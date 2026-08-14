"""
Historical price data provider (Yahoo Finance).

Fetches daily OHLCV for a CSE ticker and hands back a clean, date-ascending
pandas frame with exactly the columns services/features.py expects.

WHY 2 YEARS AND NOT 20 DAYS
Only the final row is used for inference, so a short window looks sufficient —
it is not, for two independent reasons:

  1. Wilder's RSI is recursive: every value depends on the whole preceding
     series. RSI over a 20-row window differs materially from RSI over full
     history, which is what training saw. A short window means
     out-of-distribution inputs and silently wrong predictions.
  2. Yahoo's CSE feed goes stale (see _trim_stale_tail below) and the dead
     region can be months long. The fetch window has to be wide enough that
     trimming it away still leaves a usable series.

Two years costs one HTTP round trip and nothing else.
"""

import datetime as _dt
import os

# pyrefly: ignore [missing-import]
import pandas as pd
# pyrefly: ignore [missing-import]
import yfinance as yf

from services.cache import TTLCache
from services.features import MIN_ROWS, REQUIRED_OHLCV, drop_non_trading_rows
from services.ticker_registry import Ticker

DEFAULT_PERIOD = "2y"

# Beyond this many calendar days behind today, the newest bar is not "the market
# was closed", it is a data outage worth surfacing to the caller.
STALE_AFTER_DAYS = 7

# Intraday prices move, but this endpoint predicts the NEXT daily close from
# completed daily bars, so a 15-minute window costs no accuracy and keeps
# repeated Postman calls instant.
_PRICE_TTL_SECONDS = float(os.getenv("PRICE_CACHE_TTL", "900"))
_price_cache = TTLCache(_PRICE_TTL_SECONDS)


class PriceDataError(RuntimeError):
    """Price history could not be retrieved for a symbol."""


def _flatten_columns(df: "pd.DataFrame") -> "pd.DataFrame":
    """
    yfinance returns a MultiIndex ('Close', 'JKH-N0000.CM') on newer versions and
    flat columns on older ones. Normalize to flat so downstream code sees one
    shape regardless of the installed version.
    """
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = df.columns.get_level_values(0)
    return df


def _trim_stale_tail(df: "pd.DataFrame", symbol: str) -> "pd.DataFrame":
    """
    Cut the series back to the newest bar that both traded and moved the price.

    Complements features.drop_non_trading_rows(), which removes forward-filled
    zero-volume rows everywhere. This handles the residue that survives it: the
    handful of bars inside a dead region that carry non-zero volume but still
    print the frozen close. Measured on JKH-N0000.CM, 7 of the last 129 days
    traded while the window held only 5 distinct closes.

    Inference is what makes this worth a separate pass. Training averages over
    tens of thousands of rows, so a few bad bars wash out; a prediction is built
    from the LAST row alone, so one bad bar at the end is the entire answer.

    WHY NOT A DENSITY TEST
    The obvious rule — "require N traded days in the trailing 20-day window" —
    fails exactly where it matters. At the boundary the window is still full of
    healthy history, so the first bars of the outage pass it. Measured: it left
    9 dead rows in place and Return_Lag1 was still 0.0.

    Walking back while a bar is untraded OR unchanged has no boundary blind spot,
    because a forward-filled bar cannot satisfy both tests at once. The cost is
    dropping a genuine final bar that traded but happened to close flat — one
    bar, and its return was 0 anyway.
    """
    close = df["Close"].astype(float).to_numpy()
    volume = df["Volume"].astype(float).fillna(0.0).to_numpy()
    n = len(close)

    i = n - 1
    while i > 0 and (volume[i] <= 0 or close[i] == close[i - 1]):
        i -= 1

    if i == 0:
        # The whole window is dead. Return it untouched rather than a one-row
        # frame: the caller's MIN_ROWS check gives a far better error message
        # than a downstream NaN would.
        print(f"[price_data] {symbol}: no live bar in the fetched window.")
        return df

    if i < n - 1:
        print(
            f"[price_data] {symbol}: trimmed {n - 1 - i} stale forward-filled "
            f"row(s); newest live bar is {pd.Timestamp(df.index[i]).date()}"
        )
    return df.iloc[:i + 1]


def _staleness_days(df: "pd.DataFrame") -> int | None:
    """Calendar days between the newest bar and today, or None if undeterminable."""
    try:
        last = pd.Timestamp(df.index[-1]).date()
    except Exception:
        return None
    return (_dt.date.today() - last).days


def get_price_history(
    ticker: Ticker,
    period: str = DEFAULT_PERIOD,
    use_cache: bool = True,
) -> "pd.DataFrame":
    """
    Daily OHLCV for `ticker`, oldest row first, indexed by date.

    The forward-filled stale tail is trimmed, so the last row is the last bar
    that genuinely traded. `df.attrs["stale_days"]` carries how far behind today
    that is; the route turns anything over STALE_AFTER_DAYS into a warning.

    Raises PriceDataError when Yahoo has no data for the symbol — which for CSE
    tickers usually means the symbol genuinely is not carried, not a transient
    failure.
    """
    cache_key = f"{ticker.yahoo_symbol}:{period}"
    if use_cache:
        cached = _price_cache.get(cache_key)
        if cached is not None:
            out = cached.copy()
            # Recomputed, not copied: a frame cached yesterday is a day staler
            # today, and .attrs survives .copy() so the old value would persist.
            out.attrs["stale_days"] = _staleness_days(out)
            return out

    try:
        raw = yf.download(
            ticker.yahoo_symbol,
            period=period,
            interval="1d",
            # Match the training CSVs, which were exported with raw (unadjusted)
            # prices. auto_adjust=True would back-adjust the whole series for
            # dividends and splits, shifting every feature.
            auto_adjust=False,
            progress=False,
            threads=False,
        )
    except Exception as e:
        raise PriceDataError(
            f"Failed to fetch price history for {ticker.symbol} "
            f"(Yahoo symbol {ticker.yahoo_symbol}): {e}"
        ) from e

    if raw is None or raw.empty:
        raise PriceDataError(
            f"No price data returned for {ticker.symbol} "
            f"(Yahoo symbol {ticker.yahoo_symbol}). The symbol may not be carried "
            f"by Yahoo Finance, or the market may have no recent trading history."
        )

    df = _flatten_columns(raw)

    missing = [c for c in REQUIRED_OHLCV if c not in df.columns]
    if missing:
        raise PriceDataError(
            f"Price data for {ticker.symbol} is missing columns {missing}. "
            f"Got: {list(df.columns)}"
        )

    df = df[REQUIRED_OHLCV].copy()
    df = df.dropna(subset=["Close"]).sort_index()

    if df.empty:
        raise PriceDataError(f"Price data for {ticker.symbol} has no usable rows.")

    df = _trim_stale_tail(df, ticker.symbol)
    df = drop_non_trading_rows(df)

    # Checked here rather than only in build_feature_row: after trimming, "not
    # enough history" is the most likely failure, and the message should name
    # the symbol and the window instead of just a row count.
    if len(df) < MIN_ROWS:
        raise PriceDataError(
            f"Only {len(df)} usable trading day(s) for {ticker.symbol} after "
            f"discarding non-trading rows (need {MIN_ROWS}). Try a longer period "
            f"than {period}, or the counter may be too illiquid to model."
        )

    df.attrs["stale_days"] = _staleness_days(df)

    if use_cache:
        _price_cache.set(cache_key, df.copy())

    return df


def latest_close(df: "pd.DataFrame") -> float:
    return float(df["Close"].iloc[-1])


def latest_date(df: "pd.DataFrame") -> str | None:
    """Newest bar's date as YYYY-MM-DD, for the API's `as_of` field."""
    try:
        return pd.Timestamp(df.index[-1]).strftime("%Y-%m-%d")
    except Exception:
        return None


def get_prediction_history(ticker: Ticker) -> "pd.DataFrame":
    """
    Fetches the 5-day historical data from the live CSE API for predictions.
    This avoids the stale Yahoo Finance data feed.
    """
    from services import cse_api
    
    try:
        raw = cse_api.historical_5day(ticker.symbol)
    except Exception as e:
        raise PriceDataError(f"Failed to fetch CSE 5-day history for {ticker.symbol}: {e}") from e

    if not raw:
        raise PriceDataError(f"No recent CSE historical data for {ticker.symbol}.")

    df = pd.DataFrame(raw)
    
    # Map to standard OHLCV
    df["Date"] = pd.to_datetime(df["time"], unit="ms")
    df.set_index("Date", inplace=True)
    df["Close"] = pd.to_numeric(df["price"], errors="coerce")
    df["High"] = pd.to_numeric(df["high"], errors="coerce").fillna(df["Close"])
    df["Low"] = pd.to_numeric(df["low"], errors="coerce").fillna(df["Close"])
    df["Volume"] = pd.to_numeric(df["quantity"], errors="coerce")
    
    # CSE chart data doesn't include Open, approximate from previous Close
    df["Open"] = df["Close"].shift(1).fillna(df["Close"])

    df = df[REQUIRED_OHLCV].copy()
    df = df.dropna(subset=["Close"]).sort_index()

    if df.empty:
        raise PriceDataError(f"Price data for {ticker.symbol} has no usable rows.")

    df = drop_non_trading_rows(df)

    if len(df) < MIN_ROWS:
        raise PriceDataError(
            f"Only {len(df)} usable trading day(s) for {ticker.symbol} after "
            f"discarding non-trading rows (need {MIN_ROWS}). The counter may be too illiquid to model."
        )

    df.attrs["stale_days"] = _staleness_days(df)
    return df
