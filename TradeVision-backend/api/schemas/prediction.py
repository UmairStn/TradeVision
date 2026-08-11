"""
Pydantic response models for the analysis endpoint.

These exist for the generated OpenAPI docs as much as for validation: with them,
http://localhost:8000/docs renders the exact payload shape, which makes the
endpoint testable in the browser as well as in Postman.
"""

# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field


class SentimentBlock(BaseModel):
    score: float = Field(..., description="FinBERT sentiment, -1.0 (bearish) to 1.0 (bullish).")
    label: str = Field(..., description="Bullish, Bearish or Neutral.")
    headline_count: int = Field(..., description="Articles that were successfully scored.")
    status: str = Field(
        ...,
        description=(
            "'ok', or why the score fell back to neutral "
            "('no_articles_found', 'skipped', 'error: ...')."
        ),
    )


class PricePredictionBlock(BaseModel):
    predicted_close: float
    change_percent: float
    trend: str = Field(..., description="Upward, Downward or Neutral.")

    # The underlying model is a direction classifier, so these expose what it
    # actually produced and how sentiment shifted it. predicted_close is derived
    # from probability_up_adjusted and recent volatility, not emitted by the model.
    probability_up: float = Field(..., description="Raw P(up) from XGBoost, before sentiment.")
    probability_up_adjusted: float = Field(..., description="P(up) after the sentiment blend.")
    confidence: float = Field(..., description="probability_up_adjusted as a percentage.")
    model_status: str


class TechnicalSummary(BaseModel):
    rsi_14: float | None = None
    rsi_7: float | None = None
    sma_10: float | None = None
    sma_20: float | None = None
    ema_12: float | None = None
    ema_26: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    macd_hist: float | None = None


class StockAnalysisResponse(BaseModel):
    symbol: str
    company_name: str
    as_of: str | None = Field(None, description="Date of the latest price bar (YYYY-MM-DD).")
    latest_price: float | None = None
    sentiment_analysis: SentimentBlock
    # Null when the model artifact is absent — the rest of the payload still
    # populates so the endpoint stays testable before the model is dropped in.
    price_prediction: PricePredictionBlock | None = None
    technical_summary: TechnicalSummary | None = None
    model_status: str = Field(..., description="'loaded' or 'model_not_loaded'.")
    warnings: list[str] = Field(default_factory=list)


class SymbolInfo(BaseModel):
    symbol: str
    name: str
    # None for symbols outside the curated list. Historical metadata only — the
    # cross-sectional model does not consume it.
    asset_id: int | None = None
    yahoo_symbol: str


class SymbolListResponse(BaseModel):
    count: int
    symbols: list[SymbolInfo]
