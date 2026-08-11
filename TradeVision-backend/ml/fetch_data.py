"""
Download CSE price history from Yahoo Finance into ml/data/ for training.

Run from the backend root (PYTHONPATH=/app in Docker):
    python -m ml.fetch_data                 # fetch everything missing
    python -m ml.fetch_data --force         # re-download even if present
    python -m ml.fetch_data --period 10y    # longer history
    python -m ml.fetch_data JKH.N0000 HNB.N0000   # just these

Writes one CSV per ticker: ml/data/<YAHOO_SYMBOL>.csv with Date + OHLCV.

Deliberately NOT written to fail fast. Yahoo's CSE coverage is uneven, so some
symbols return nothing and some return a handful of rows. Those are skipped and
reported in a summary rather than aborting a 50-ticker run on the first miss.

RSI is not stored here. The original CSVs carried pre-computed RSI columns, but
training now recomputes indicators through services/features.py so that training
and serving are guaranteed to agree. Raw OHLCV is all that is needed.
"""

import argparse
import os
import sys
import time

# pyrefly: ignore [missing-import]
import pandas as pd
# pyrefly: ignore [missing-import]
import yfinance as yf

from ml.cse_universe import CSE_UNIVERSE, to_yahoo_symbol

_HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.getenv("DATA_DIR", os.path.join(_HERE, "data"))

DEFAULT_PERIOD = "5y"

# A ticker with fewer usable rows than this contributes noise rather than signal:
# ~200 trading days is under a year, too short for stable indicator warm-up plus
# a meaningful train/test split.
MIN_USABLE_ROWS = 200

OHLCV = ["Open", "High", "Low", "Close", "Volume"]


def _flatten_columns(df: "pd.DataFrame") -> "pd.DataFrame":
    """yfinance returns a MultiIndex on newer versions; normalize to flat."""
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = df.columns.get_level_values(0)
    return df


def fetch_one(symbol: str, period: str) -> "pd.DataFrame | None":
    """Download one ticker. Returns None when unusable (missing or too short)."""
    yahoo = to_yahoo_symbol(symbol)

    try:
        raw = yf.download(
            yahoo,
            period=period,
            interval="1d",
            # Must match services/price_data.py. auto_adjust=True would
            # back-adjust for splits/dividends, so training would see a
            # different price series than serving does.
            auto_adjust=False,
            progress=False,
            threads=False,
        )
    except Exception as e:
        print(f"  {symbol:<14} ERROR    {e}")
        return None

    if raw is None or raw.empty:
        print(f"  {symbol:<14} MISSING  Yahoo has no data for {yahoo}")
        return None

    df = _flatten_columns(raw)

    missing = [c for c in OHLCV if c not in df.columns]
    if missing:
        print(f"  {symbol:<14} BAD      missing columns {missing}")
        return None

    df = df[OHLCV].dropna(subset=["Close"]).sort_index()

    if len(df) < MIN_USABLE_ROWS:
        print(f"  {symbol:<14} SHORT    only {len(df)} rows (need {MIN_USABLE_ROWS})")
        return None

    print(f"  {symbol:<14} OK       {len(df)} rows  {df.index[0].date()} -> {df.index[-1].date()}")
    return df


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch CSE price history for training.")
    parser.add_argument("symbols", nargs="*", help="Specific symbols (default: whole universe)")
    parser.add_argument("--period", default=DEFAULT_PERIOD, help="yfinance period, e.g. 5y, 10y, max")
    parser.add_argument("--force", action="store_true", help="Re-download even if the CSV exists")
    args = parser.parse_args()

    if args.symbols:
        targets = [(s.strip().upper(), "") for s in args.symbols]
    else:
        targets = CSE_UNIVERSE

    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"Fetching {len(targets)} tickers (period={args.period}) into {DATA_DIR}\n")

    fetched, skipped_existing, failed = [], [], []

    for symbol, _name in targets:
        out_path = os.path.join(DATA_DIR, f"{to_yahoo_symbol(symbol)}.csv")

        if os.path.exists(out_path) and not args.force:
            print(f"  {symbol:<14} SKIP     already present (use --force to refresh)")
            skipped_existing.append(symbol)
            continue

        df = fetch_one(symbol, args.period)
        if df is None:
            failed.append(symbol)
            continue

        df.to_csv(out_path, index_label="Date")
        fetched.append(symbol)

        # Yahoo throttles aggressive sequential requests; a short pause keeps a
        # 50-ticker run from tripping rate limits partway through.
        time.sleep(0.4)

    total_available = len(fetched) + len(skipped_existing)

    print("\n" + "=" * 58)
    print(f"  Fetched now      : {len(fetched)}")
    print(f"  Already present  : {len(skipped_existing)}")
    print(f"  Failed / skipped : {len(failed)}")
    print(f"  Usable CSVs      : {total_available}")
    print("=" * 58)

    if failed:
        print(f"\nNot available on Yahoo: {', '.join(failed)}")
        print("Normal — CSE coverage is patchy. Training uses whatever succeeded.")

    if total_available == 0:
        print(
            "\nNo data fetched. Check the Yahoo symbol format: this script expects "
            f"'{to_yahoo_symbol('JKH.N0000')}'. If that is wrong, fix to_yahoo_symbol() "
            "in ml/cse_universe.py."
        )
        return 1

    if total_available < 30:
        print(
            f"\nOnly {total_available} tickers available — fewer than hoped. Training "
            "will still work, but the cross-sectional dataset is thinner than planned."
        )

    print(f"\nNext: python -m ml.train_model")
    return 0


if __name__ == "__main__":
    sys.exit(main())
