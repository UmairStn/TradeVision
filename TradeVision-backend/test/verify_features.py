"""
Feature parity check — RUN THIS FIRST.

The trained model expects RSI values produced by whatever tool wrote the RSI
columns in the training CSVs. services/features.py recomputes RSI from scratch.
If the two disagree, the model receives out-of-distribution inputs and returns
confident nonsense — and nothing else in the stack can detect that. Every number
in the API would look perfectly reasonable and be wrong.

This script settles it by computing both common RSI conventions against a real
training CSV and reporting which matches:

  * Wilder / SMA-seeded  (features.rsi)     - TA-Lib, pandas_ta default
  * pandas ewm-seeded    (features.rsi_ewm) - the `ta` package and hand-rolled code

Usage (from the backend root, PYTHONPATH=/app in Docker):
    python -m test.verify_features ml/data/HAYL-N0000.CM.csv
    python -m test.verify_features            # auto-discovers a CSV under ml/data/

Reads only. Writes nothing.
"""

import glob
import os
import sys

# pyrefly: ignore [missing-import]
import pandas as pd

from services.features import rsi, rsi_ewm

# Mean absolute difference (on the 0-100 scale) below which we call it a match.
# 0.5 tolerates float noise and rounding in the CSV export; a genuine convention
# mismatch lands far above it, typically 2-10.
MATCH_TOLERANCE = 0.5


def find_default_csv() -> str | None:
    for pattern in ("ml/data/*.csv", "data/*.csv", "*.csv"):
        matches = sorted(glob.glob(pattern))
        if matches:
            return matches[0]
    return None


def compare(csv_path: str) -> int:
    df = pd.read_csv(csv_path)

    if "Close" not in df.columns:
        print(f"FAIL: {csv_path} has no 'Close' column. Found: {list(df.columns)}")
        return 1

    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date").reset_index(drop=True)

    close = df["Close"].astype(float)
    print(f"Loaded {csv_path}: {len(df)} rows")
    print(f"Columns: {list(df.columns)}\n")

    csv_rsi_cols = [c for c in ("RSI_14", "RSI_7") if c in df.columns]
    if not csv_rsi_cols:
        print("NOTE: This CSV carries no RSI columns, so parity cannot be checked.")
        print("      Showing our computed values for eyeballing instead.\n")
        for period in (14, 7):
            wilder = rsi(close, period)
            print(f"  RSI_{period} (Wilder, last 3): {wilder.tail(3).round(3).tolist()}")
        print("\nInconclusive — supply a CSV that includes its RSI columns.")
        return 0

    exit_code = 0

    for col in csv_rsi_cols:
        period = int(col.split("_")[1])
        expected = df[col].astype(float)

        candidates = {
            "Wilder / SMA-seeded (features.rsi)": rsi(close, period),
            "pandas ewm-seeded (features.rsi_ewm)": rsi_ewm(close, period),
        }

        print(f"--- {col} ---")
        best_name, best_diff = None, float("inf")

        for name, computed in candidates.items():
            # Compare only rows where both are present; RSI warm-up is NaN and
            # the CSV may have been trimmed differently.
            both = pd.concat([expected, computed], axis=1).dropna()
            if both.empty:
                print(f"  {name}: no overlapping rows to compare")
                continue

            diff = (both.iloc[:, 0] - both.iloc[:, 1]).abs()
            mean_diff, max_diff = diff.mean(), diff.max()
            verdict = "MATCH" if mean_diff <= MATCH_TOLERANCE else "mismatch"
            print(
                f"  {name}: mean |diff| = {mean_diff:.4f}, "
                f"max = {max_diff:.4f}  [{verdict}]  ({len(both)} rows)"
            )
            if mean_diff < best_diff:
                best_name, best_diff = name, mean_diff

        if best_diff <= MATCH_TOLERANCE:
            print(f"  => Best match: {best_name}\n")
        else:
            print(
                f"  => NO CONVENTION MATCHED (best was {best_name} at {best_diff:.4f}).\n"
                f"     The model will see out-of-distribution RSI. Identify the tool\n"
                f"     that generated {col} before trusting any prediction.\n"
            )
            exit_code = 1

    if exit_code == 0:
        print("PASS: computed RSI matches the training data.")
        print("      If the winner above is the ewm-seeded variant, switch")
        print("      services/features.py:add_indicators() to use rsi_ewm().")
    else:
        print("FAIL: RSI parity could not be established.")

    return exit_code


def main() -> int:
    csv_path = sys.argv[1] if len(sys.argv) > 1 else find_default_csv()

    if not csv_path:
        print(
            "No CSV found. Pass one explicitly:\n"
            "    python -m test.verify_features ml/data/HAYL-N0000.CM.csv\n\n"
            "Drop at least one training CSV into ml/data/ to run this check."
        )
        return 1

    if not os.path.exists(csv_path):
        print(f"File not found: {csv_path}")
        return 1

    return compare(csv_path)


if __name__ == "__main__":
    raise SystemExit(main())
