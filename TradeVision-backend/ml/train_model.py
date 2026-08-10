"""
XGBoost training — CSE next-day direction classifier (cross-sectional).

Train on every CSV in ml/data/ and save the artifact the API loads. All features
come from services/features.py — the SAME module the serving code uses — so a
model built here is guaranteed to receive identical inputs in production.

Cross-sectional: there is no Asset_ID in the feature set, so the model learns
"this pattern of returns/RSI/relative volume implies X about tomorrow" without
caring which company produced it. That is what lets it predict ANY CSE ticker,
including ones never seen in training. The number of files in ml/data/ therefore
has no effect on which symbols the API can predict — it only changes the volume
of training data.

Run from the backend root (PYTHONPATH=/app in Docker):
    python -m ml.train_model

Expects CSVs in ml/data/ (see ml/fetch_data.py) with at least Date, Open, High,
Low, Close, Volume. Writes models/srilanka_stock_classifier.json.
"""

import glob
import os

# pyrefly: ignore [missing-import]
import pandas as pd
# pyrefly: ignore [missing-import]
import xgboost as xgb
# pyrefly: ignore [missing-import]
from sklearn.metrics import accuracy_score, auc, log_loss, roc_curve

from services.features import FEATURE_COLUMNS, add_indicators, add_model_features

_HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.getenv("DATA_DIR", os.path.join(_HERE, "data"))
MODEL_OUT = os.getenv(
    "MODEL_OUT", os.path.join(_HERE, "..", "models", "srilanka_stock_classifier.json")
)
PLOT_OUT = os.getenv("PLOT_OUT", os.path.join(_HERE, "roc_curve.png"))

TRAIN_SPLIT = 0.8

# Stale-close filter. Thin CSE counters print unchanged closes for days at a
# time (often with zero volume); those rows manufacture artificial zero-return
# observations that corrupt both features and labels. Dropping them is
# legitimate — they carry no information about the next day.
STALE_ZERO_VOLUME = True


def load_and_prepare(path: str) -> "pd.DataFrame":
    """One CSV -> a frame carrying the model features and the direction target."""
    df = pd.read_csv(path)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date").reset_index(drop=True)

    if STALE_ZERO_VOLUME:
        before = len(df)
        df = df[~((df["Close"] == df["Close"].shift(1)) & (df["Volume"] == 0))]
        df = df.reset_index(drop=True)
        if len(df) < before:
            print(f"    (dropped {before - len(df)} stale zero-volume rows)")

    # Recompute indicators with the shared code — the same path the API uses.
    df = add_indicators(df)
    df = add_model_features(df)

    # Target: did the NEXT day close higher? Flat days count as "down", matching
    # the original script.
    next_day_return = df["Close"].pct_change().shift(-1)
    df["Target_Direction"] = (next_day_return > 0).astype(int)

    # The final row has no next day, so its target is meaningless.
    df = df.iloc[:-1]

    return df.dropna(subset=FEATURE_COLUMNS + ["Target_Direction"])


def main() -> None:
    print("Step 1: Building features with services/features.py (shared with the API)...")

    csv_paths = sorted(glob.glob(os.path.join(DATA_DIR, "*.csv")))
    if not csv_paths:
        raise SystemExit(
            f"No training CSVs found in {DATA_DIR}. Run `python -m ml.fetch_data` "
            f"first, or point DATA_DIR at a folder containing them."
        )
    print(f"Found {len(csv_paths)} CSVs\n")

    train_dfs, test_dfs, skipped = [], [], []

    for path in csv_paths:
        name = os.path.basename(path)
        try:
            df = load_and_prepare(path)
        except Exception as e:
            print(f"  {name:<28} FAILED  {e}")
            skipped.append(name)
            continue

        if len(df) < 50:
            print(f"  {name:<28} SKIPPED (only {len(df)} usable rows)")
            skipped.append(name)
            continue

        # Split each asset on its own timeline before concatenating, so no
        # stock's future leaks into another's training window.
        split_row = int(len(df) * TRAIN_SPLIT)
        train_dfs.append(df.iloc[:split_row])
        test_dfs.append(df.iloc[split_row:])
        print(f"  {name:<28} OK      {len(df):>6} rows")

    if not train_dfs:
        raise SystemExit(f"No usable training data in {DATA_DIR}.")

    master_train = pd.concat(train_dfs, ignore_index=True).sort_values("Date")
    master_test = pd.concat(test_dfs, ignore_index=True).sort_values("Date")

    X_train, y_train = master_train[FEATURE_COLUMNS], master_train["Target_Direction"]
    X_test, y_test = master_test[FEATURE_COLUMNS], master_test["Target_Direction"]

    print(
        f"\nStep 2: Training XGBoost on {len(X_train):,} rows from "
        f"{len(csv_paths) - len(skipped)} assets, {len(FEATURE_COLUMNS)} features..."
    )
    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.02,
        subsample=0.7,
        colsample_bytree=0.7,
        random_state=42,
        eval_metric="logloss",
    )
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    probabilities = model.predict_proba(X_test)[:, 1]

    accuracy = accuracy_score(y_test, predictions) * 100
    logloss = log_loss(y_test, probabilities)
    fpr, tpr, _ = roc_curve(y_test, probabilities)
    roc_auc = auc(fpr, tpr)

    # Markets drift upward, so "always predict up" is a real competitor. A model
    # that cannot beat it has learned nothing, and accuracy alone would hide that.
    majority_rate = max(y_test.mean(), 1 - y_test.mean()) * 100

    print("\n=================== PIPELINE RESULTS ===================")
    print(f"Directional Accuracy (Hit Ratio): {accuracy:.2f}%")
    print(f"Majority-class baseline:          {majority_rate:.2f}%  <- must beat this")
    print(f"Log Loss:                         {logloss:.5f}")
    print(f"ROC AUC:                          {roc_auc:.4f}")
    print("=========================================================")

    if accuracy <= majority_rate:
        print(
            "\nWARNING: the model did NOT beat the majority-class baseline.\n"
            "The features contain no exploitable signal for next-day direction.\n"
            "This is a legitimate result to report — do not hide it, and do not\n"
            "tune hyperparameters until it is beaten."
        )

    os.makedirs(os.path.dirname(os.path.abspath(MODEL_OUT)), exist_ok=True)
    model.save_model(MODEL_OUT)
    print(f"\n-> Model saved to {os.path.abspath(MODEL_OUT)}")

    saved_features = model.get_booster().feature_names
    print(f"-> Artifact feature names: {saved_features}")
    if saved_features != FEATURE_COLUMNS:
        print("!! MISMATCH: artifact features differ from services/features.py")

    _save_roc_plot(fpr, tpr, roc_auc)


def _save_roc_plot(fpr, tpr, roc_auc: float) -> None:
    """
    Write the ROC curve to disk, if matplotlib is available.

    Imported lazily and optionally: matplotlib is a training-only convenience and
    is deliberately kept out of requirements.txt so it never ships in the serving
    image. The Agg backend is selected because containers have no display, and
    plt.show() would block a headless run forever.
    """
    try:
        # pyrefly: ignore [missing-import]
        import matplotlib
        matplotlib.use("Agg")
        # pyrefly: ignore [missing-import]
        import matplotlib.pyplot as plt
    except ImportError:
        print("-> matplotlib not installed; skipping ROC plot (`pip install matplotlib`).")
        return

    plt.figure(figsize=(8, 6))
    plt.plot(fpr, tpr, color="blue", lw=2, label=f"ROC Curve (AUC = {roc_auc:.2f})")
    plt.plot([0, 1], [0, 1], color="red", linestyle="--", lw=2, label="Random Guess (AUC = 0.50)")
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.title("Model Evaluation: ROC Curve for Market Direction")
    plt.xlabel("False Positive Rate (Type I Error)")
    plt.ylabel("True Positive Rate (Sensitivity)")
    plt.legend(loc="lower right")
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.savefig(PLOT_OUT, dpi=120, bbox_inches="tight")
    print(f"-> ROC curve saved to {os.path.abspath(PLOT_OUT)}")


if __name__ == "__main__":
    main()
