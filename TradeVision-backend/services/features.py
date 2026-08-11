"""
Feature engineering — the single source of truth shared by training and serving.

`ml/train_model.py` and `services/prediction_engine.py` both import FEATURE_COLUMNS
and the builders here. That is the whole point of this module: if training and
inference computed features independently they would drift, and a drifted feature
produces a confident, plausible, wrong prediction with nothing in the stack to
flag it.

THE MODEL CONTRACT (do not reorder — XGBoost matches on position):

    Open_Pct, High_Pct, Low_Pct, Rel_Volume,
    RSI_14, RSI_7, Return_Lag1, Return_Lag2, Return_Lag3

CROSS-SECTIONAL BY DESIGN. Every feature above is scale-free, so the model
learns "what does this pattern imply about tomorrow" rather than "what does
company #3 usually do". That is what lets it predict ANY CSE ticker, including
ones absent from training.

Two features were deliberately removed to get here:

  * Asset_ID — an integer company index. Its tree splits only covered the 9
    training companies, so a 10th had no valid value to pass. This was the sole
    reason the old model was locked to 9 stocks.
  * Log_Volume — log1p(raw share count), roughly 15 for a large cap and 9 for a
    thin counter. Less obvious than Asset_ID but the same leak: it encoded
    company size. Replaced by Rel_Volume, which compares a stock's volume to its
    OWN recent average and therefore means the same thing everywhere.

One quirk is replicated deliberately from the original training script:

  * Return_Lag1 is `pct_change().shift(1)` — the return over t-2 -> t-1, NOT
    yesterday's return. The current day's own return is computed but never used
    as a feature. Almost certainly unintended upstream; kept so this retrain
    changes one thing at a time. Revisit separately.

RSI is still divided by 100, matching the original training script, which read
pre-computed 0-100 RSI columns out of the CSVs and rescaled them.
"""

# pyrefly: ignore [missing-import]
import numpy as np
# pyrefly: ignore [missing-import]
import pandas as pd

# Column order the model is trained on. Positional — never reorder.
FEATURE_COLUMNS = [
    "Open_Pct",
    "High_Pct",
    "Low_Pct",
    "Rel_Volume",
    "RSI_14",
    "RSI_7",
    "Return_Lag1",
    "Return_Lag2",
    "Return_Lag3",
]

# Raw OHLCV columns every input frame must carry.
REQUIRED_OHLCV = ["Open", "High", "Low", "Close", "Volume"]

# Lookback for the relative-volume baseline.
VOLUME_WINDOW = 20

# Ceiling on Rel_Volume. A near-dormant counter that suddenly trades once can
# produce a ratio in the hundreds; unclipped, that single outlier dominates the
# split search and the model learns from an artefact.
REL_VOLUME_CAP = 10.0

# RSI_14 needs 15 rows to emit a first value and Wilder smoothing is recursive,
# so RSI computed over a short window differs from RSI over full history.
# Rel_Volume needs VOLUME_WINDOW rows. 30 is the floor for a usable answer;
# callers should feed ~6 months.
MIN_ROWS = 30


class InsufficientHistoryError(ValueError):
    """Not enough price rows to compute the feature vector."""


def _wilder_smooth(values: "pd.Series", period: int) -> "pd.Series":
    """
    Wilder's smoothing, seeded with a simple average (TA-Lib / pandas_ta style).

    pandas' `ewm(alpha=1/period, adjust=False)` seeds from the first observation
    instead, which gives different early values. Both converge, but seeding this
    way matches the mainstream TA libraries most likely to have produced the RSI
    columns in the training CSVs. See rsi_ewm() for the other convention and
    test/verify_features.py for the check that decides which one your data used.
    """
    arr = values.to_numpy(dtype=float)
    out = np.full(len(arr), np.nan)

    if len(arr) < period + 1:
        return pd.Series(out, index=values.index)

    # arr[0] is NaN (it comes from .diff()); seed at index `period`.
    out[period] = np.nanmean(arr[1:period + 1])
    for i in range(period + 1, len(arr)):
        out[i] = (out[i - 1] * (period - 1) + arr[i]) / period

    return pd.Series(out, index=values.index)


def _rsi_from_averages(avg_gain: "pd.Series", avg_loss: "pd.Series") -> "pd.Series":
    """
    Convert Wilder averages into RSI, handling both degenerate cases.

    Guarding only `avg_loss == 0` (the common shortcut) maps a completely flat
    series to RSI 100 — identical to a stock that rose every single day. That is
    wrong and it matters here: illiquid CSE counters print stale, unchanged closes
    for days at a time, and a false 100 would tell the model "extremely
    overbought" when nothing traded.

      no losses, some gains -> 100  (genuinely overbought)
      no gains,  some losses->   0  (genuinely oversold)
      neither  (flat)       ->  50  (no information, neutral)
    """
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    out = 100.0 - (100.0 / (1.0 + rs))

    flat = (avg_gain == 0.0) & (avg_loss == 0.0)
    no_loss = (avg_loss == 0.0) & (avg_gain > 0.0)

    out = out.where(~no_loss, 100.0)
    out = out.where(~flat, 50.0)

    # Preserve the warm-up NaNs; a missing average must not become a number.
    return out.where(avg_gain.notna() & avg_loss.notna())


def rsi(close: "pd.Series", period: int) -> "pd.Series":
    """Relative Strength Index on the classic 0-100 scale, Wilder smoothing."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)

    return _rsi_from_averages(
        _wilder_smooth(gain, period),
        _wilder_smooth(loss, period),
    )


def rsi_ewm(close: "pd.Series", period: int) -> "pd.Series":
    """
    RSI using pandas' ewm seeding instead of an SMA seed.

    Alternative convention, kept so test/verify_features.py can compare both
    against your training CSVs and tell us which one they used.
    """
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)

    return _rsi_from_averages(
        gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean(),
        loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean(),
    )


def add_indicators(df: "pd.DataFrame") -> "pd.DataFrame":
    """
    Attach every indicator this system reports, on a copy of `df`.

    Two distinct groups:
      * Model features — RSI_14/RSI_7 (0-100 here; rescaled in build_feature_row).
      * Display only — SMA/EMA/MACD, surfaced in the API's technical_summary.
        These are NOT model inputs; the artifact was trained without them.
    """
    missing = [c for c in REQUIRED_OHLCV if c not in df.columns]
    if missing:
        raise ValueError(f"Price frame is missing required columns: {missing}")

    out = df.copy()
    close = out["Close"].astype(float)

    # --- Model features ---
    out["RSI_14"] = rsi(close, 14)
    out["RSI_7"] = rsi(close, 7)

    # --- Display only ---
    out["SMA_10"] = close.rolling(window=10).mean()
    out["SMA_20"] = close.rolling(window=20).mean()
    out["EMA_12"] = close.ewm(span=12, adjust=False).mean()
    out["EMA_26"] = close.ewm(span=26, adjust=False).mean()
    out["MACD"] = out["EMA_12"] - out["EMA_26"]
    out["MACD_Signal"] = out["MACD"].ewm(span=9, adjust=False).mean()
    out["MACD_Hist"] = out["MACD"] - out["MACD_Signal"]

    return out


def add_model_features(df: "pd.DataFrame") -> "pd.DataFrame":
    """
    Attach the model features. Expects add_indicators() to have run already
    (or RSI_14/RSI_7 to be present on the 0-100 scale, as in the training CSVs).

    No company identity is taken or added — see the module docstring.
    """
    out = df.copy()
    close = out["Close"].astype(float)

    # Intraday shape relative to the same day's close. Close_Pct is omitted
    # because it is identically 1.0.
    out["Open_Pct"] = out["Open"].astype(float) / close
    out["High_Pct"] = out["High"].astype(float) / close
    out["Low_Pct"] = out["Low"].astype(float) / close

    # Volume relative to this stock's OWN recent average: 1.0 is a normal day,
    # 2.0 is twice usual activity. Scale-free, so it carries the same meaning for
    # a large cap and a thin counter alike.
    volume = out["Volume"].astype(float)
    avg_volume = volume.rolling(VOLUME_WINDOW, min_periods=VOLUME_WINDOW).mean()
    # replace(0 -> NaN) before dividing: a fully dormant 20-day window would
    # otherwise yield inf, which XGBoost accepts silently as a huge value.
    out["Rel_Volume"] = (volume / avg_volume.replace(0.0, np.nan)).clip(upper=REL_VOLUME_CAP)

    # Training rescaled the CSV's 0-100 RSI columns to 0-1.
    out["RSI_14"] = out["RSI_14"].astype(float) / 100.0
    out["RSI_7"] = out["RSI_7"].astype(float) / 100.0

    out["Current_Return"] = close.pct_change()
    out["Return_Lag1"] = out["Current_Return"].shift(1)
    out["Return_Lag2"] = out["Current_Return"].shift(2)
    out["Return_Lag3"] = out["Current_Return"].shift(3)

    return out


def build_feature_row(df: "pd.DataFrame") -> "pd.DataFrame":
    """
    Build the single feature row for the most recent trading day.

    `df` must be date-ascending OHLCV with enough history for RSI and the volume
    baseline to converge — pass the full ~6 months, not a trimmed tail.

    Returns a DataFrame (not a numpy array) so XGBoost can match on feature name
    and raise on a mismatch rather than silently predicting from misaligned
    columns.
    """
    if len(df) < MIN_ROWS:
        raise InsufficientHistoryError(
            f"Need at least {MIN_ROWS} trading days to build features, got {len(df)}."
        )

    enriched = add_model_features(add_indicators(df))
    row = enriched.iloc[[-1]][FEATURE_COLUMNS].astype(float)

    if row.isna().any().any():
        bad = row.columns[row.isna().iloc[0]].tolist()
        raise InsufficientHistoryError(
            f"Feature(s) {bad} are NaN on the latest row. This usually means too "
            f"little price history, or gaps in the series."
        )

    return row


def latest_technicals(df_with_indicators: "pd.DataFrame") -> dict:
    """Display indicators for the newest row, as plain floats for JSON."""
    last = df_with_indicators.iloc[-1]
    fields = [
        "RSI_14", "RSI_7", "SMA_10", "SMA_20",
        "EMA_12", "EMA_26", "MACD", "MACD_Signal", "MACD_Hist",
    ]
    out = {}
    for name in fields:
        value = last.get(name)
        out[name.lower()] = (
            None if value is None or pd.isna(value) else round(float(value), 4)
        )
    return out


def realized_volatility(df: "pd.DataFrame", window: int = 20) -> float:
    """
    Std-dev of recent daily returns, used to size the predicted move.

    The classifier only emits a probability, so magnitude comes from the stock's
    own recent behaviour rather than from the model.
    """
    returns = df["Close"].astype(float).pct_change().dropna()
    if len(returns) < 2:
        return 0.0
    sigma = returns.tail(window).std()
    return 0.0 if pd.isna(sigma) else float(sigma)
