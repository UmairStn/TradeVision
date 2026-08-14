"""
Check the stale-feed defences in services/price_data.py + services/features.py.

    python -m test.test_stale_data            # synthetic checks (offline, fast)
    python -m test.test_stale_data JKH.N0000  # also probe a live Yahoo symbol

WHY THIS EXISTS
Yahoo's CSE feed does not fail cleanly. When it loses the exchange it keeps
emitting daily rows carrying the last known close with Volume 0, forever.
Measured on JKH-N0000.CM in Aug 2026: ~85% of days traded across 5 years, but
only 7 of the most recent 129, with the final 8 closes byte-identical.

That is the dangerous kind of bad data — it has the right shape, the right dates
and no NaNs, so nothing downstream objects. Inference reads the LAST row, so
those are exactly the rows a prediction gets built from: every return 0, RSI
pinned at 50, and a 20-day volume mean tending to 0.

The synthetic cases below assert the two-part defence works and, just as
importantly, that it does NOT mistake a thin-but-genuinely-trading CSE counter
for a dead one. Re-run this whenever Yahoo's coverage changes.
"""

import sys

# pyrefly: ignore [missing-import]
import numpy as np
# pyrefly: ignore [missing-import]
import pandas as pd

from services import price_data
from services.features import (
    FEATURE_COLUMNS,
    InsufficientHistoryError,
    add_indicators,
    build_feature_row,
    drop_non_trading_rows,
)

N_LIVE = 400
N_DEAD = 129          # matches the observed JKH 6-month window
N_DEAD_TRADES = 7     # ...of which this many actually traded


def _frame(close, volume, start="2024-01-01"):
    """OHLCV frame shaped like what yfinance hands back."""
    return pd.DataFrame(
        {
            "Open": close * 0.995,
            "High": close * 1.010,
            "Low": close * 0.990,
            "Close": close,
            "Volume": volume,
        },
        index=pd.bdate_range(start, periods=len(close)),
    )


def _healthy_then_dead(rng):
    """A real series with a forward-filled dead tail glued on — the JKH shape."""
    close = 100 * np.cumprod(1 + rng.normal(0, 0.015, N_LIVE))
    volume = rng.integers(50_000, 200_000, N_LIVE).astype(float)
    volume[rng.random(N_LIVE) < 0.15] = 0.0   # thin-but-alive: 15% no-trade days

    dead_close = np.full(N_DEAD, close[-1])   # forward-filled, byte-identical
    dead_volume = np.zeros(N_DEAD)
    dead_volume[rng.choice(N_DEAD, N_DEAD_TRADES, replace=False)] = 1000.0

    return _frame(
        np.concatenate([close, dead_close]),
        np.concatenate([volume, dead_volume]),
    )


def _clean(df, symbol):
    """The exact two-step get_price_history() applies, in the same order."""
    return drop_non_trading_rows(price_data._trim_stale_tail(df, symbol))


def check_dead_tail_is_removed(rng) -> None:
    print("\n[1] Healthy series + dead forward-filled tail")
    df = _healthy_then_dead(rng)

    # What the old code served: a feature row built from the ghost region.
    before = build_feature_row(df)
    lag1_before = float(before["Return_Lag1"].iloc[0])
    rsi_before = float(before["RSI_14"].iloc[0])
    print(f"    untreated : Return_Lag1={lag1_before:.4f}  RSI_14={rsi_before:.4f}")
    assert lag1_before == 0.0, "expected the ghost tail to flatten returns"

    # NOTE: RSI does NOT come back as the neutral 0.5 that _rsi_from_averages
    # returns for a flat series. Wilder smoothing is recursive and decays toward
    # zero only asymptotically, so after 129 identical closes avg_gain and
    # avg_loss are tiny but still non-zero — the `flat` guard never fires and
    # RSI simply FREEZES at whatever it read when the feed died.
    #
    # That is worse than the degenerate case it was written to catch: a frozen
    # 47.8 looks like a perfectly ordinary reading. Nothing downstream can tell
    # it apart from a live one. Removing the rows is the only defence.
    frozen = add_indicators(df)["RSI_14"]
    assert abs(float(frozen.iloc[-1]) - float(frozen.iloc[-20])) < 1e-9, (
        "expected RSI to be frozen across the dead tail"
    )
    print(f"    ...and RSI is FROZEN: identical at t-20 and t-1 "
          f"({float(frozen.iloc[-1]):.4f}), not the 50.0 the flat-series guard "
          f"would give")

    clean = _clean(df, "TEST.N0000")
    print(f"    cleaned   : {len(df)} -> {len(clean)} rows, "
          f"last bar {clean.index[-1].date()}")
    assert len(clean) <= N_LIVE, "did not cut back into the live region"
    assert (clean["Volume"] > 0).all(), "a zero-volume row survived"

    after = build_feature_row(clean)
    assert after.notna().all().all(), "NaN in the cleaned feature row"
    lag1 = float(after["Return_Lag1"].iloc[0])
    rsi = float(after["RSI_14"].iloc[0])
    print(f"    features  : Return_Lag1={lag1:.4f}  RSI_14={rsi:.4f}")
    assert lag1 != 0.0, "returns still flat after cleaning"
    assert 0.0 < rsi < 1.0, f"RSI still degenerate: {rsi}"
    assert abs(rsi - rsi_before) > 1e-6, "cleaning did not change the RSI reading"


def check_fully_dead_symbol_fails_loudly(rng) -> None:
    print("\n[2] Fully dead symbol — must fail, not guess")
    df = _healthy_then_dead(rng).iloc[N_LIVE:]
    clean = _clean(df, "DEAD.N0000")
    print(f"    {len(df)} -> {len(clean)} usable rows")

    try:
        build_feature_row(clean)
    except InsufficientHistoryError as e:
        print(f"    raised InsufficientHistoryError: {str(e)[:64]}...")
    else:
        raise AssertionError("built a feature row out of a dead series")


def check_thin_counter_survives(rng) -> None:
    print("\n[3] Thin-but-alive counter — must NOT be treated as dead")
    n = 300
    close = 40 * np.cumprod(1 + rng.normal(0, 0.02, n))
    volume = rng.integers(1_000, 9_000, n).astype(float)
    volume[rng.random(n) < 0.60] = 0.0        # 60% of days never trade
    df = _frame(close, volume, start="2025-01-01")

    clean = _clean(df, "THIN.N0000")
    print(f"    {len(df)} -> {len(clean)} usable rows")
    assert len(clean) >= 30, "a genuinely trading counter was killed as dead"
    assert build_feature_row(clean).notna().all().all()
    print("    features built OK")


def probe_live(symbol: str) -> None:
    """Hit Yahoo for real. Reports rather than asserts — coverage moves."""
    from services.ticker_registry import resolve_open

    print(f"\n[live] {symbol}")
    ticker = resolve_open(symbol)
    try:
        df = price_data.get_price_history(ticker, use_cache=False)
    except Exception as e:
        print(f"    {type(e).__name__}: {e}")
        return

    stale = df.attrs.get("stale_days")
    print(f"    {len(df)} usable bars, newest {price_data.latest_date(df)} "
          f"({stale} days old), close {price_data.latest_close(df):.2f}")
    if stale is not None and stale > price_data.STALE_AFTER_DAYS:
        print(f"    -> STALE: Yahoo has stopped updating {ticker.yahoo_symbol}.")

    row = build_feature_row(df)
    print("    features:")
    for name in FEATURE_COLUMNS:
        print(f"      {name:<14} {float(row[name].iloc[0]):>10.4f}")


def main() -> int:
    rng = np.random.default_rng(0)
    print("=" * 62)
    print("  Stale-feed defence checks")
    print("=" * 62)

    check_dead_tail_is_removed(rng)
    check_fully_dead_symbol_fails_loudly(rng)
    check_thin_counter_survives(rng)

    print("\n" + "=" * 62)
    print("  Synthetic checks PASSED")
    print("=" * 62)

    for symbol in sys.argv[1:]:
        probe_live(symbol)

    return 0


if __name__ == "__main__":
    sys.exit(main())
