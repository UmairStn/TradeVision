from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime
from uuid import UUID

# Watchlist Schemas
class WatchlistCreate(BaseModel):
    symbol: str

class WatchlistResponse(BaseModel):
    id: UUID
    symbol: str
    added_at: datetime

    class Config:
        from_attributes = True

# Portfolio Schemas
class PortfolioCreate(BaseModel):
    symbol: str
    price: float
    quantity: float
    date_acquired: date

class PortfolioResponse(BaseModel):
    id: UUID
    symbol: str
    price: float
    quantity: float
    date_acquired: date
    added_at: datetime

    class Config:
        from_attributes = True
