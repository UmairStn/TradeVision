"""
Shared, lazily-initialised singletons for the API layer.

Two objects are expensive and must not be rebuilt per request:

  * SentimentAnalyzer — loads FinBERT (~400MB). Several seconds and a large
    memory hit each time.
  * StockPredictionEngine — loads the XGBoost artifact from disk.

Both are created on FIRST USE, not at import. That keeps `uvicorn --reload` fast
and, more importantly, means the app still starts when the model artifact or the
Hugging Face cache is missing — the endpoint then degrades gracefully instead of
the container failing to boot.

Note what is deliberately NOT a singleton: NewsSentimentPipeline. Its
process_news_for_stocks() closes the scraper in a finally block, permanently
stopping Playwright, so a shared instance would work exactly once in
WEBSITE_SEARCH/BOTH mode. Instead a fresh pipeline is built per request around
the SHARED analyzer — the scraper is cheap, FinBERT is not.
"""

import os
import threading
# pyrefly: ignore [missing-import]
import jwt
# pyrefly: ignore [missing-import]
from fastapi import Depends, HTTPException, status
# pyrefly: ignore [missing-import]
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from services.news_pipeline import NewsSentimentPipeline
from services.prediction_engine import StockPredictionEngine
from services.scraper_mode import ScraperMode
# pyrefly: ignore [missing-import]
from services.sentiment import SentimentAnalyzer

# RSS is the default: it needs no browser, is far more reliable than scraping
# site markup, and is the only mode safe to run repeatedly behind an API.
SCRAPER_MODE = ScraperMode(os.getenv("SCRAPER_MODE", ScraperMode.GOOGLE_NEWS_RSS.value))

_analyzer: SentimentAnalyzer | None = None
_engine: StockPredictionEngine | None = None

# Requests are served from a threadpool, so two concurrent cold requests could
# otherwise each start loading FinBERT.
_analyzer_lock = threading.Lock()
_engine_lock = threading.Lock()


def get_analyzer() -> SentimentAnalyzer:
    """Shared FinBERT analyzer. First call downloads/loads the model."""
    global _analyzer
    if _analyzer is None:
        with _analyzer_lock:
            if _analyzer is None:
                print("[startup] Loading FinBERT sentiment model (first use)...")
                _analyzer = SentimentAnalyzer()
                print("[startup] FinBERT ready.")
    return _analyzer


def get_engine() -> StockPredictionEngine:
    """Shared prediction engine. Never raises if the artifact is missing."""
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = StockPredictionEngine()
                if _engine.is_loaded:
                    print(f"[startup] XGBoost model loaded from {_engine.model_path}")
                else:
                    print(f"[startup] Prediction model NOT loaded: {_engine.load_error}")
    return _engine


def build_news_pipeline() -> NewsSentimentPipeline:
    """
    A fresh single-use pipeline wrapping the shared analyzer.

    Single-use by design — see the module docstring.
    """
    return NewsSentimentPipeline(mode=SCRAPER_MODE, analyzer=get_analyzer())

security = HTTPBearer(auto_error=False)
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verifies the Supabase JWT token and returns the user payload."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    try:
        # Supabase uses HS256 for signing its JWTs
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False}
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
