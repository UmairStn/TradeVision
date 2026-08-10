"""
Prediction engine smoke test — no HTTP, no scraping.

Isolates the price + feature + model path so a failure points at one layer
instead of the whole stack. Run this before touching Postman.

Usage (from the backend root, PYTHONPATH=/app in Docker):
    python -m test.test_prediction_engine
    python -m test.test_prediction_engine JKH.N0000
"""

import sys

from services import price_data
from services.features import FEATURE_COLUMNS, build_feature_row
from services.prediction_engine import StockPredictionEngine
from services.ticker_registry import UnknownTickerError, resolve_open

DEFAULT_SYMBOL = "HAYL.N0000"

# A real CSE ticker deliberately absent from the curated registry. Since the
# model is cross-sectional, it should predict just like a registered one — this
# is the whole point of removing Asset_ID.
UNREGISTERED_SYMBOL = "LOLC.N0000"


def run_one(symbol: str) -> int:
    try:
        ticker = resolve_open(symbol)
    except UnknownTickerError as e:
        print(f"FAIL: {e}")
        return 1

    print(f"\n--- Prediction Engine Smoke Test: {ticker.symbol} ---")
    print(f"Company:  {ticker.name}")
    print(f"Known:    {ticker.is_known}   Yahoo: {ticker.yahoo_symbol}\n")

    # 1. Prices
    print("[1/5] Fetching price history...")
    try:
        df = price_data.get_price_history(ticker)
    except Exception as e:
        print(f"  FAIL: {e}")
        print("\n  Yahoo may not carry this symbol. Verify the yahoo_symbol format")
        print("  in services/ticker_registry.py against a working ticker.")
        return 1

    print(f"  OK: {len(df)} rows, {df.index[0].date()} -> {df.index[-1].date()}")
    print(f"  Latest close: {price_data.latest_close(df):.2f}\n")

    # 2. Features — the exact vector the model will see.
    print("[2/5] Building feature row...")
    try:
        row = build_feature_row(df)
    except Exception as e:
        print(f"  FAIL: {e}")
        return 1

    values = row.iloc[0]
    for col in FEATURE_COLUMNS:
        print(f"    {col:<14} {values[col]:>12.6f}")
    print()

    # 3. Model
    print("[3/5] Loading model...")
    engine = StockPredictionEngine()
    if not engine.is_loaded:
        print(f"  NOT LOADED: {engine.load_error}")
        print("\n  Steps 1-2 passed, so prices and features are fine.")
        print(f"  Run `python -m ml.train_model` to generate the artifact at:")
        print(f"    {engine.model_path}")
        print("  The API will still respond, with price_prediction: null.")
        return 0
    print(f"  OK: {engine.model_path}")

    artifact_features = engine._model.get_booster().feature_names
    print(f"  Artifact features: {artifact_features}")
    if artifact_features != FEATURE_COLUMNS:
        print(f"  !! MISMATCH: artifact has {len(artifact_features)} features, "
              f"serving expects {len(FEATURE_COLUMNS)}. Retrain.")
        return 1
    print()

    # 4. Inference, with and without a sentiment nudge.
    print("[4/5] Running inference...")
    for label, sentiment in (("neutral (0.0)", 0.0), ("bullish (+0.65)", 0.65)):
        result = engine.predict_price(ticker, sentiment)
        pred = result["price_prediction"]
        if pred is None:
            print(f"  {label}: no prediction ({result.get('model_error')})")
            continue
        print(
            f"  sentiment {label:<16} -> p_up {pred['probability_up']:.4f} "
            f"-> adj {pred['probability_up_adjusted']:.4f} "
            f"| {pred['trend']:<8} {pred['predicted_close']:.2f} "
            f"({pred['change_percent']:+.2f}%)"
        )

    # 5. Verify the cross-sectional claim: an unregistered ticker predicts too.
    print(f"\n[5/5] Cross-sectional check: {UNREGISTERED_SYMBOL} is NOT in the registry...")
    other = resolve_open(UNREGISTERED_SYMBOL)
    if other.is_known:
        print(f"  (Actually registered — pick a different UNREGISTERED_SYMBOL)")
    else:
        try:
            result = engine.predict_price(other, 0.0)
            pred = result["price_prediction"]
            if pred is None:
                print(f"  FAIL: no prediction for {UNREGISTERED_SYMBOL}")
                return 1
            print(
                f"  OK: {UNREGISTERED_SYMBOL} -> {pred['trend']} "
                f"{pred['predicted_close']:.2f} ({pred['change_percent']:+.2f}%)"
            )
        except Exception as e:
            print(f"  FAIL: {e}")
            return 1

    print("\nPASS: engine is working end to end, including unregistered tickers.")
    return 0


def main() -> int:
    symbol = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SYMBOL
    return run_one(symbol)


if __name__ == "__main__":
    raise SystemExit(main())
