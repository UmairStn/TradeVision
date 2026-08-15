"""
Stock prediction engine — XGBoost inference + sentiment blend + price sizing.

The trained artifact is a binary DIRECTION classifier: it returns P(next day is
up), nothing else. The price figures in the API response therefore have to be
derived, and this module is where that happens, transparently:

    p_up        = model.predict_proba(feature_row)[0][1]
    p_adjusted  = clip(p_up + SENTIMENT_INFLUENCE * sentiment_score, 0, 1)
    trend       = "Upward" if p_adjusted > 0.55 else "Downward" if < 0.45 else "Neutral"
    exp_return  = (2 * p_adjusted - 1) * sigma      # sigma = realized vol of recent returns
    predicted   = latest_close * (1 + exp_return)

The model has no sentiment input (its feature set is fixed at 10 columns), so the
blend happens AFTER inference. The raw and adjusted probabilities are both
returned so the fusion is visible in the response rather than hidden inside a
single number.
"""

import os

# pyrefly: ignore [missing-import]
import numpy as np
# pyrefly: ignore [missing-import]
import xgboost as xgb

from services import price_data
from services.features import (
    add_indicators,
    build_feature_row,
    latest_technicals,
    realized_volatility,
)
from services.ticker_registry import Ticker

DEFAULT_MODEL_PATH = os.getenv(
    "MODEL_PATH", os.path.join(os.path.dirname(__file__), "..", "models", "srilanka_stock_classifier.json")
)

# How strongly FinBERT sentiment ([-1, 1]) nudges the model's probability.
# 0.10 * score: fully bullish news moves p by ±0.10; neutral news leaves it alone.
SENTIMENT_INFLUENCE = float(os.getenv("SENTIMENT_INFLUENCE", "0.10"))

TREND_UP_THRESHOLD = 0.55
TREND_DOWN_THRESHOLD = 0.45


class ModelNotLoadedError(RuntimeError):
    """The model artifact is missing or could not be loaded."""


def _trend_label(p_adjusted: float) -> str:
    if p_adjusted > TREND_UP_THRESHOLD:
        return "Upward"
    if p_adjusted < TREND_DOWN_THRESHOLD:
        return "Downward"
    return "Neutral"


class StockPredictionEngine:
    def __init__(self, model_path: str | None = None):
        # Resolve relative to the repo root (default path is ../models/...)
        self.model_path = os.path.abspath(model_path or DEFAULT_MODEL_PATH)
        self._model = None
        self._load_error: str | None = None
        self._load_model()

    # ──────────────────────────────────────────────
    #  Loading
    # ──────────────────────────────────────────────

    def _load_model(self) -> None:
        """
        Best-effort load. A missing or corrupt artifact must not take the whole
        API down: the engine records the problem and every later call returns a
        "model not loaded" result instead of raising.
        """
        if not os.path.exists(self.model_path):
            self._load_error = f"Model file not found: {self.model_path}"
            return

        try:
            # XGBClassifier is the sklearn wrapper the artifact was saved from.
            model = xgb.XGBClassifier()
            model.load_model(self.model_path)
            self._model = model
        except Exception as e:
            self._load_error = f"Failed to load model from {self.model_path}: {e}"
            self._model = None
            return

        self._load_error = None

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    @property
    def load_error(self) -> str | None:
        return self._load_error

    def reload(self, model_path: str | None = None) -> None:
        """Re-point and reload, so a freshly-added artifact needs no container restart."""
        if model_path is not None:
            self.model_path = os.path.abspath(model_path)
        self._model = None
        self._load_error = None
        self._load_model()

    # ──────────────────────────────────────────────
    #  Inference
    # ──────────────────────────────────────────────

    def predict_price(self, ticker: Ticker, sentiment_score: float = 0.0) -> dict:
        """
        Full prediction for one ticker. Returns the prediction block plus the
        technical summary the route needs, in a single call.
        """
        if not self.is_loaded:
            return {
                "price_prediction": None,
                "model_status": "model_not_loaded",
                "model_error": self.load_error,
                "technical_summary": None,
            }

        # 1. Prices (full history for converging indicators) -> features for the
        #    LAST row. No company identity is passed: the model is cross-sectional.
        df = price_data.get_prediction_history(ticker)
        feature_row = build_feature_row(df)
        indicators = add_indicators(df)

        # 2. Model: P(up) for tomorrow.
        proba = self._model.predict_proba(feature_row)
        p_up = float(np.asarray(proba)[0][1])

        # 3. Sentiment blend (post-hoc — the model has no sentiment feature).
        p_adjusted = float(np.clip(p_up + SENTIMENT_INFLUENCE * sentiment_score, 0.0, 1.0))

        # 4. Size the move from the stock's own recent volatility.
        sigma = realized_volatility(df)
        expected_return = (2.0 * p_adjusted - 1.0) * sigma

        latest = price_data.latest_close(df)
        predicted_close = float(latest * (1.0 + expected_return))
        change_percent = expected_return * 100.0
        trend = _trend_label(p_adjusted)

        return {
            "price_prediction": {
                "predicted_close": round(predicted_close, 4),
                "change_percent": round(change_percent, 4),
                "trend": trend,
                "probability_up": round(p_up, 4),
                "probability_up_adjusted": round(p_adjusted, 4),
                "confidence": round(p_adjusted * 100.0, 2),
                "model_status": "loaded",
            },
            "model_status": "loaded",
            "model_error": None,
            "technical_summary": latest_technicals(indicators),
        }

    def feature_row(self, ticker: Ticker) -> dict:
        """The exact feature vector the model will see, for debugging/parity checks."""
        df = price_data.get_prediction_history(ticker)
        row = build_feature_row(df)
        return row.to_dict(orient="records")[0]
