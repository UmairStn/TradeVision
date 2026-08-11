"""
Stock analysis endpoint.

    GET /api/v1/stocks/analyze?symbol=HAYL.N0000[&include_news=true]

Combines, for whatever symbol is passed:
  1. FinBERT news sentiment  (services/news_pipeline.py)
  2. XGBoost price direction (services/prediction_engine.py)

WHY EVERY BLOCKING CALL GOES THROUGH run_in_threadpool
The route is async, but the work underneath is entirely synchronous, and one
piece of it is actively hostile to asyncio: sync_playwright() raises if started
inside a running event loop. yfinance and FinBERT are merely blocking — they
would stall the loop and freeze every other request. run_in_threadpool hands the
work to a worker thread with no running loop, which fixes both problems at once.
"""

import os

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, HTTPException, Query
# pyrefly: ignore [missing-import]
from starlette.concurrency import run_in_threadpool

from api.dependencies import build_news_pipeline, get_engine
from api.schemas.prediction import (
    StockAnalysisResponse,
    SymbolInfo,
    SymbolListResponse,
)
from services import price_data
from services.cache import TTLCache
from services.features import InsufficientHistoryError
from services.price_data import PriceDataError
from services.ticker_registry import (
    UnknownTickerError,
    all_tickers,
    resolve_open,
    supported_symbols,
)

router = APIRouter(prefix="/api/v1/stocks", tags=["stocks"])

# A full scrape + FinBERT pass costs 30-90s per symbol. News moves on a scale of
# hours, so an hour-long cache makes repeat Postman calls instant at no real cost
# to freshness.
_SENTIMENT_TTL = float(os.getenv("SENTIMENT_CACHE_TTL", "3600"))
_sentiment_cache = TTLCache(_SENTIMENT_TTL)

_NEUTRAL_SENTIMENT = {
    "score": 0.0,
    "label": "Neutral",
    "headline_count": 0,
    "status": "skipped",
}


def _fetch_sentiment_sync(ticker) -> dict:
    """Blocking: scrape + FinBERT. Runs in a worker thread. Never raises."""
    cached = _sentiment_cache.get(ticker.symbol)
    if cached is not None:
        return {**cached, "status": f"{cached.get('status', 'ok')} (cached)"}

    pipeline = build_news_pipeline()
    result = pipeline.get_sentiment(ticker)

    # Only cache real measurements. Caching a failure would pin a symbol to
    # neutral for the whole TTL because of one transient network blip.
    if result.get("status") == "ok":
        _sentiment_cache.set(ticker.symbol, result)

    return result


@router.get(
    "/analyze",
    response_model=StockAnalysisResponse,
    summary="Analyze a CSE stock: news sentiment + XGBoost price prediction",
)
async def analyze_stock(
    symbol: str = Query(
        ...,
        description="CSE ticker, e.g. HAYL.N0000 (short form 'HAYL' also accepted).",
        examples=["HAYL.N0000"],
    ),
    include_news: bool = Query(
        True,
        description=(
            "Set false to skip news scraping entirely. Sentiment returns a neutral "
            "0.0 and the response arrives in seconds instead of 30-90s — useful "
            "when iterating on the price model."
        ),
    ),
):
    # 1. Resolve the symbol. The model is cross-sectional (no company identity in
    #    its features), so ANY well-formed CSE ticker is predictable — not just
    #    the curated ones. Only malformed input is rejected.
    try:
        ticker = resolve_open(symbol)
    except UnknownTickerError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    warnings: list[str] = []

    # Unregistered symbols have no curated company name, so the news query falls
    # back to the ticker root and sentiment quality drops. Say so rather than
    # presenting a weak signal as a strong one. Prediction is unaffected.
    if not ticker.is_known and include_news:
        warnings.append(
            f"{ticker.symbol} is not in the company-name registry, so news is "
            f"searched by ticker root ('{ticker.name}') and sentiment may be "
            f"unreliable. Price prediction is unaffected."
        )

    # 2. Sentiment. Failures degrade to neutral rather than failing the request.
    if include_news:
        sentiment = await run_in_threadpool(_fetch_sentiment_sync, ticker)
        if not sentiment.get("status", "").startswith("ok"):
            warnings.append(f"Sentiment unavailable ({sentiment.get('status')}); using 0.0.")
    else:
        sentiment = dict(_NEUTRAL_SENTIMENT)

    # 3. Price prediction, nudged by the sentiment score.
    engine = get_engine()
    try:
        prediction = await run_in_threadpool(
            engine.predict_price, ticker, float(sentiment["score"])
        )
    except PriceDataError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except InsufficientHistoryError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Prediction failed for {ticker.symbol}: {e}"
        ) from e

    if prediction.get("model_status") != "loaded":
        warnings.append(
            prediction.get("model_error")
            or "Prediction model is not loaded; price_prediction is null."
        )

    # 4. Latest price. Cached from the prediction call, so this is not a refetch.
    #    When the model is missing there was no prediction call, so fetch here to
    #    keep the rest of the payload useful.
    latest_price = None
    as_of = None
    technical_summary = prediction.get("technical_summary")
    try:
        df = await run_in_threadpool(price_data.get_price_history, ticker)
        latest_price = round(price_data.latest_close(df), 4)
        as_of = price_data.latest_date(df)

        # Yahoo forward-fills CSE symbols after its feed goes stale; price_data
        # trims those ghost rows, so `as_of` can legitimately be months behind.
        # The prediction is still valid FOR THAT DATE — say so rather than let it
        # read as a forecast for tomorrow.
        stale_days = df.attrs.get("stale_days")
        if stale_days is not None and stale_days > price_data.STALE_AFTER_DAYS:
            warnings.append(
                f"Newest real trading bar for {ticker.symbol} is {as_of} "
                f"({stale_days} days old). Yahoo Finance has stopped updating this "
                f"symbol and its recent rows were forward-filled placeholders, which "
                f"have been discarded. The prediction is for the day after {as_of}, "
                f"not for tomorrow."
            )

        if technical_summary is None:
            from services.features import add_indicators, latest_technicals
            technical_summary = latest_technicals(add_indicators(df))
    except PriceDataError as e:
        if prediction.get("model_status") == "loaded":
            raise HTTPException(status_code=502, detail=str(e)) from e
        warnings.append(f"Price data unavailable: {e}")

    return StockAnalysisResponse(
        symbol=ticker.symbol,
        company_name=ticker.name,
        as_of=as_of,
        latest_price=latest_price,
        sentiment_analysis=sentiment,
        price_prediction=prediction.get("price_prediction"),
        technical_summary=technical_summary,
        model_status=prediction.get("model_status", "unknown"),
        warnings=warnings,
    )


@router.get(
    "/symbols",
    response_model=SymbolListResponse,
    summary="List CSE symbols with curated company names",
)
async def list_symbols():
    """
    Symbols that have a curated company name, which gives the best news quality.

    NOT a limit on prediction: the model is cross-sectional, so /analyze accepts
    any well-formed CSE ticker. Symbols outside this list still get a full price
    prediction — only their news lookup is weaker.
    """
    return SymbolListResponse(
        count=len(supported_symbols()),
        symbols=[
            SymbolInfo(
                symbol=t.symbol,
                name=t.name,
                asset_id=t.asset_id,
                yahoo_symbol=t.yahoo_symbol,
            )
            for t in all_tickers()
        ],
    )
