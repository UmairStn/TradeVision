"""
Pydantic response models for the live market endpoints.

Same rationale as schemas/prediction.py: these exist for the generated OpenAPI
docs as much as for validation, so http://localhost:8000/docs renders the exact
payload the frontend consumes.

Fields are snake_case, matching the rest of this API. The frontend maps them to
its camelCase interfaces in src/services/api.ts, which is already the mapping
layer for the prediction payload.
"""

# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field


class MarketQuote(BaseModel):
    symbol: str
    name: str = Field(..., description="Company name, or the ticker when the CSE omits it.")
    price: float
    change: float
    change_percent: float
    volume: float = Field(..., description="Shares traded in the session.")
    turnover: float = Field(0.0, description="Rupee value traded in the session.")
    trades: float = Field(0.0, description="Number of individual trades.")

    # Present for full quotes (tradeSummary), absent for rows that came only from
    # a thin movers endpoint and could not be matched during enrichment.
    previous_close: float | None = None
    day_high: float | None = None
    day_low: float | None = None
    day_open: float | None = None
    market_cap: str | None = Field(None, description="Human-readable, e.g. '352.9B'.")
    market_cap_value: float | None = Field(None, description="Raw market cap in rupees.")
    last_traded_time: int | None = Field(None, description="Epoch milliseconds.")


class MarketIndices(BaseModel):
    aspi: float | None = Field(None, description="All Share Price Index level.")
    aspi_change: float | None = None
    aspi_change_percent: float | None = None
    turnover: float | None = Field(None, description="Total market turnover for the session.")
    share_volume: float | None = None
    trades: int | None = None
    listed_companies: int | None = Field(None, description="Companies in the CSE trade summary.")


class MarketSummaryResponse(BaseModel):
    status: str = Field(..., description="'Market Open', 'Market Closed', etc., per the CSE.")
    # The CSE caps each list at 10 rows; that is upstream behaviour, not a limit
    # applied here.
    gainers: list[MarketQuote]
    losers: list[MarketQuote]
    most_active: list[MarketQuote]
    indices: MarketIndices
    warnings: list[str] = Field(default_factory=list)


class SymbolListResponse(BaseModel):
    count: int
    symbols: list[MarketQuote]


class PricePoint(BaseModel):
    timestamp: str = Field(..., description="Bar date, YYYY-MM-DD.")
    open: float
    high: float
    low: float
    close: float
    volume: float


class PriceHistoryResponse(BaseModel):
    symbol: str
    source: str = Field(
        ...,
        description=(
            "Always 'yahoo'. The CSE chart endpoint returns only 5 daily bars for "
            "any period, so it cannot draw a multi-week chart."
        ),
    )
    points: list[PricePoint]
    as_of: str | None = Field(None, description="Date of the newest bar (YYYY-MM-DD).")
    stale_days: int | None = Field(
        None,
        description="Calendar days between the newest bar and today.",
    )
    warnings: list[str] = Field(default_factory=list)
