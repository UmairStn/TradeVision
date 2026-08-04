# AGENTS.md — TradeVision Backend

Guidance for AI agents working in `TradeVision-backend/`. This is the Python backend
for **TradeVision** (aka SmartInvestor-Lanka), a stock-prediction system focused on the
Colombo Stock Exchange (CSE). The backend's current, working feature is a **news
sentiment pipeline** that scrapes Sri Lankan stock news and scores it with FinBERT.

## What this backend does

For a list of stocks it:
1. Scrapes recent news articles (Google News RSS and/or Sri Lankan news sites).
2. Runs each article through FinBERT financial sentiment analysis.
3. Aggregates one weighted sentiment score per ticker (recent news weighted higher).

## Tech stack

- **API**: FastAPI + Uvicorn ([api/main.py](api/main.py)) — currently just a health-check root route.
- **ML/NLP**: `transformers` + `torch` (CPU), model `ProsusAI/finbert`.
- **Scraping**: `urllib` + `beautifulsoup4` (RSS mode); `playwright` headless Chromium (website mode).
- **Planned/declared but not yet used**: `sqlalchemy`, `psycopg2-binary`, `alembic` (Postgres), `xgboost` (price model).
- **Python 3.11**. `PYTHONPATH=/app` — imports are rooted at the backend dir (e.g. `from services.scraper import ...`).

## Directory map

| Path | Purpose | Status |
|------|---------|--------|
| [api/](api/) | FastAPI app entrypoint (`api.main:app`) | minimal — only `/` health route |
| [services/](services/) | News scraping + sentiment pipeline | **active, working** |
| [docker/](docker/) | Multi-stage Dockerfile + docker-compose (dev/prod) | active |
| [test/](test/) | Manual run scripts | see note below |
| `db/`, `ml/`, `models/`, `scheduler/` | Reserved for DB models, ML training, saved models, scheduled jobs | **empty placeholders** |

## Key files in `services/`

- [services/scraper_mode.py](services/scraper_mode.py) — `ScraperMode` enum: `GOOGLE_NEWS_RSS`, `WEBSITE_SEARCH`, `BOTH`.
- [services/scraper.py](services/scraper.py) — `NewsScraper`. Fetches articles. RSS mode uses urllib (fast, no browser); website mode uses Playwright. **Always call `.close()`** to free Playwright resources (the pipeline does this in a `finally`).
- [services/sentiment.py](services/sentiment.py) — `SentimentAnalyzer`. Wraps FinBERT; `analyze_text()` returns `sentiment_score` in `[-1.0, 1.0]` (`positive - negative`) plus `raw_scores`.
- [services/news_pipeline.py](services/news_pipeline.py) — `NewsSentimentPipeline`. Orchestrates scrape → analyze → aggregate. Caps 10 articles/stock; weights recent (≤7d) 70% and older (8–30d) 30%.

## Running

**Docker (recommended — handles Playwright + HF model cache):**
```bash
# Dev (hot-reload) — from the backend dir
docker compose -f docker/docker-compose.yml up -d backend-dev
# Prod
docker compose -f docker/docker-compose.yml --profile prod up -d backend-prod
```
API serves on `http://localhost:8000`. Note: build context is `..` (repo root), Dockerfile expects `requirements.txt` at that context root.

**Local (manual pipeline run):**
```bash
pip install -r requirements.txt
playwright install chromium          # only needed for WEBSITE_SEARCH / BOTH modes
export PYTHONPATH=$(pwd)             # PowerShell: $env:PYTHONPATH = (Get-Location).Path
python -m test.test_news_pipeline
```

## Conventions & gotchas

- **Imports are absolute from the backend root** (`services.*`, `api.*`). Keep `PYTHONPATH` pointed at this dir; don't add relative-import hacks.
- `# pyrefly: ignore [missing-import]` comments suppress the type checker for ML libs — keep them on those import lines.
- [test/test_news_pipeline.py](test/test_news_pipeline.py) is a **manual `__main__` script**, not a pytest suite. There is no automated test framework configured yet; if you add real tests, wire up pytest and put them here.
- First FinBERT run downloads the model from Hugging Face (~400MB). The `hf_cache` docker volume persists it across rebuilds — don't remove that volume mapping.
- Scraping is network- and layout-dependent. RSS mode is the reliable default; website mode breaks when target sites change markup. Prefer `GOOGLE_NEWS_RSS` for tests.
- FinBERT truncates input (~1500 chars / 512 tokens). Don't pass full article bodies expecting full coverage.
- No secrets/env config is required today. If you add DB or external APIs, load via env vars (see the empty `db/` dir as the intended home for models).

## Where to add things

- New scraping source → add a template to `WEBSITE_SEARCH_TEMPLATES` in [services/scraper.py](services/scraper.py).
- New API endpoint → extend [api/main.py](api/main.py) (consider splitting into routers as it grows).
- Persistence / price prediction (xgboost) → the reserved `db/`, `models/`, `ml/` dirs are the intended homes; they're empty scaffolding today.
