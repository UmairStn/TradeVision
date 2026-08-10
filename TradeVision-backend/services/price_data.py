"""
Historical price data provider (Yahoo Finance).

Fetches daily OHLCV for a CSE ticker and hands back a clean, date-ascending
pandas frame with exactly the columns services/features.py expects.

WHY 6 MONTHS AND NOT 20 DAYS
Only the final row is used for inference, so a short window looks sufficient —
it is not. Wilder's RSI is recursive: every value depends on the whole preceding
series. RSI computed over a 20-row window differs materially from RSI computed
over full history, which is what the training CSVs contain. Feeding the short
version to the model means out-of-distribution inputs and silently wrong
predictions. Fetching ~6 months costs one extra HTTP round trip and nothing else.
"""

import os

# pyrefly: ignore [missing-import]
import pandas as pd
# pyrefly: ignore [missing-import]
import yfinance as yf

from services.cache import TTLCache
from services.features import REQUIRED_OHLCV
from services.ticker_registry import Ticker

DEFAULT_PERIOD = "6mo"

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


def get_price_history(
    ticker: Ticker,
    period: str = DEFAULT_PERIOD,
    use_cache: bool = True,
) -> "pd.DataFrame":
    """
    Daily OHLCV for `ticker`, oldest row first, indexed by date.

    Raises PriceDataError when Yahoo has no data for the symbol — which for CSE
    tickers usually means the symbol genuinely is not carried, not a transient
    failure.
    """
    cache_key = f"{ticker.yahoo_symbol}:{period}"
    if use_cache:
        cached = _price_cache.get(cache_key)
        if cached is not None:
            return cached.copy()

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
