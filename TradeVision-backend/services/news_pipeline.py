from services.scraper import NewsScraper
from services.scraper_mode import ScraperMode
# pyrefly: ignore [missing-import]
from services.sentiment import SentimentAnalyzer
from services.ticker_registry import Ticker

# Per-stock article budget sent to FinBERT, and how it is divided between
# sources in BOTH mode. Quotas are per-source so that RSS volume cannot crowd
# out the curated local sites; unused quota is backfilled by the other source.
MAX_PER_STOCK = 10
SOURCE_QUOTAS = {
    "google_news_rss": 7,
    "website_search": 3,
}

# Articles <= this many days old count as "recent" and carry RECENT_WEIGHT.
RECENT_AGE_DAYS = 7
RECENT_WEIGHT = 0.7
OLDER_WEIGHT = 0.3

# Score bands for the human-readable label. Matches the thresholds already used
# by test/test_news_pipeline.py so the API and the manual script agree.
BULLISH_THRESHOLD = 0.1
BEARISH_THRESHOLD = -0.1


def sentiment_label(score: float | None) -> str:
    """Bullish / Bearish / Neutral from a [-1, 1] score. None means no data."""
    if score is None:
        return "Neutral"
    if score > BULLISH_THRESHOLD:
        return "Bullish"
    if score < BEARISH_THRESHOLD:
        return "Bearish"
    return "Neutral"


class NewsSentimentPipeline:
    def __init__(
        self,
        mode: ScraperMode = ScraperMode.GOOGLE_NEWS_RSS,
        analyzer: SentimentAnalyzer | None = None,
    ):
        """
        Args:
            mode:     which scraping strategy to use.
            analyzer: optional shared SentimentAnalyzer. Loading FinBERT costs
                      ~400MB and several seconds, so the API injects one
                      long-lived instance here and lets the scraper (cheap in RSS
                      mode) be rebuilt per request. Left as None, the pipeline
                      builds its own — keeping the original standalone behaviour.

        Note on reuse: process_news_for_stocks() closes the scraper in a finally
        block, which permanently stops Playwright. A pipeline instance is
        therefore single-use in WEBSITE_SEARCH/BOTH mode. RSS mode never starts a
        browser, so close() is a no-op and the instance can be reused freely.
        """
        self.scraper = NewsScraper(mode=mode)
        self.analyzer = analyzer or SentimentAnalyzer()

    def _select_articles(self, articles: list[dict]) -> list[dict]:
        """
        Pick up to MAX_PER_STOCK articles per ticker, newest first, honouring
        the per-source quotas in SOURCE_QUOTAS.

        Selection is by publication date, not scrape order. Taking the list as
        it arrives would mean taking Google's relevance ranking (and, in BOTH
        mode, only RSS results, since those are appended first and already
        exceed the budget on their own).

        Articles with an unknown age sort last — they are used only to fill
        leftover quota, never in place of an article with a known date.
        """
        by_ticker: dict[str, list[dict]] = {}
        for article in articles:
            by_ticker.setdefault(article["ticker"], []).append(article)

        selected: list[dict] = []
        for ticker, ticker_articles in by_ticker.items():
            # Newest first; unknown age (None) sorts to the end.
            ordered = sorted(
                ticker_articles,
                key=lambda a: (a.get("age_days") is None, a.get("age_days") or 0),
            )

            chosen: list[dict] = []
            used: dict[str, int] = {}

            # Pass 1: fill each source up to its own quota.
            for article in ordered:
                source = article.get("source", "unknown")
                quota = SOURCE_QUOTAS.get(source, MAX_PER_STOCK)
                if used.get(source, 0) < quota:
                    chosen.append(article)
                    used[source] = used.get(source, 0) + 1

            # Pass 2: backfill unused budget when a source came up short
            # (e.g. website search found nothing, so RSS may exceed 7).
            if len(chosen) < MAX_PER_STOCK:
                already = {id(a) for a in chosen}
                for article in ordered:
                    if len(chosen) >= MAX_PER_STOCK:
                        break
                    if id(article) not in already:
                        chosen.append(article)

            # Re-sort: pass 2 appends out of order.
            chosen = sorted(
                chosen,
                key=lambda a: (a.get("age_days") is None, a.get("age_days") or 0),
            )[:MAX_PER_STOCK]

            if len(chosen) < len(ticker_articles):
                breakdown = ", ".join(f"{s}={n}" for s, n in sorted(used.items()))
                print(
                    f"  [{ticker}] Selected {len(chosen)} of {len(ticker_articles)} "
                    f"articles for FinBERT ({breakdown})"
                )
            selected.extend(chosen)

        return selected

    def process_news_for_stocks(
        self,
        stock_list: list[dict],
        target_urls: list[str] | None = None,
    ) -> list[dict]:
        """
        Scrapes news for requested stocks, runs each article through FinBERT,
        and returns ONE aggregated sentiment result per stock ticker.

        Args:
            stock_list:  list of {"ticker": ..., "name": ...}
            target_urls: only used by WEBSITE_SEARCH mode; ignored for GOOGLE_NEWS_RSS

        Returns:
            list of dicts, one per stock ticker, with aggregated sentiment scores.
        """
        try:
            print("Starting news scraping process...")
            scraped_articles = self.scraper.scrape_stock_news(stock_list, target_urls)
            print(f"Scraped {len(scraped_articles)} total articles.")

            scraped_articles = self._select_articles(scraped_articles)

            # Run each article through FinBERT and collect raw scores per ticker,
            # split by age: recent (<= 7 days) and older (8-30 days).
            ticker_scores_recent: dict[str, list[float]] = {}
            ticker_scores_older: dict[str, list[float]] = {}
            ticker_meta: dict[str, dict] = {}

            for article in scraped_articles:
                print(f"Analyzing: {article['headline'][:70]}...")
                sentiment_res = self.analyzer.analyze_text(article["full_text"])

                ticker = article["ticker"]
                age = article.get("age_days")

                if ticker not in ticker_meta:
                    ticker_scores_recent[ticker] = []
                    ticker_scores_older[ticker] = []
                    ticker_meta[ticker] = {
                        "ticker":     ticker,
                        "stock_name": article["stock_name"],
                        "articles":   [],
                        "failed":     0,
                    }

                record = {
                    "headline":        article["headline"],
                    "article_url":     article["article_url"],
                    "source":          article.get("source", "unknown"),
                    "age_days":        age,
                    "sentiment_score": sentiment_res["sentiment_score"],
                    "raw_scores":      sentiment_res["raw_scores"],
                    "analyzed":        sentiment_res["ok"],
                    "scraped_at":      article["scraped_at"],
                }
                if not sentiment_res["ok"]:
                    record["error"] = sentiment_res.get("error", "unknown")
                ticker_meta[ticker]["articles"].append(record)

                # Only real scores enter the averages. A failed analysis is
                # excluded outright rather than counted as 0.0/neutral.
                if not sentiment_res["ok"]:
                    ticker_meta[ticker]["failed"] += 1
                    print(f"  Skipped (analysis failed): {record.get('error')}")
                    continue

                score = sentiment_res["sentiment_score"]

                # Unknown age is treated as older, never as recent: the recent
                # bucket carries 70% weight and should require a known date.
                if age is not None and age <= RECENT_AGE_DAYS:
                    ticker_scores_recent[ticker].append(score)
                else:
                    ticker_scores_older[ticker].append(score)

            # Aggregate: recent avg, older avg, and final weighted score.
            aggregated = []
            for ticker in ticker_meta.keys():
                recent_list = ticker_scores_recent[ticker]
                older_list = ticker_scores_older[ticker]

                recent_avg = sum(recent_list) / len(recent_list) if recent_list else 0.0
                older_avg = sum(older_list) / len(older_list) if older_list else 0.0

                # Only blend when both buckets have data; otherwise the present
                # bucket stands alone rather than being diluted toward zero.
                if recent_list and older_list:
                    final_score = (recent_avg * RECENT_WEIGHT) + (older_avg * OLDER_WEIGHT)
                elif recent_list:
                    final_score = recent_avg
                elif older_list:
                    final_score = older_avg
                else:
                    final_score = None  # nothing scored — not the same as 0.0

                scored_count = len(recent_list) + len(older_list)
                aggregated.append({
                    "ticker":                ticker,
                    "stock_name":            ticker_meta[ticker]["stock_name"],
                    "recent_sentiment_7d":   round(recent_avg, 4) if recent_list else None,
                    "older_sentiment_30d":   round(older_avg, 4) if older_list else None,
                    "final_sentiment_score": round(final_score, 4) if final_score is not None else None,
                    "article_count":         scored_count,
                    "recent_count":          len(recent_list),
                    "older_count":           len(older_list),
                    "failed_count":          ticker_meta[ticker]["failed"],
                    "articles":              ticker_meta[ticker]["articles"],
                })

            return aggregated
        finally:
            # Always clean up Playwright browser (no-op in RSS mode)
            self.scraper.close()

    def get_sentiment(self, ticker: Ticker) -> dict:
        """
        One flat sentiment result for a single ticker, shaped for the API.

        NEVER RAISES. Sentiment is a supporting signal, not the point of the
        request — a scrape failure, an empty news week, or a FinBERT error must
        degrade to neutral rather than fail the whole /analyze call. The `status`
        field records which of those happened so a 0.0 score is never mistaken
        for "measured, genuinely neutral coverage".

        Returns:
            {"score": float, "label": str, "headline_count": int, "status": str}
        """
        neutral = {
            "score": 0.0,
            "label": "Neutral",
            "headline_count": 0,
            "status": "no_data",
            "articles": [],
        }

        try:
            # The scraper searches by COMPANY NAME, not ticker — Google News has
            # no idea what "HAYL.N0000" is.
            results = self.process_news_for_stocks(
                [{"ticker": ticker.symbol, "name": ticker.name}]
            )
        except Exception as e:
            print(f"[sentiment] Pipeline failed for {ticker.symbol}: {e}")
            return {**neutral, "status": f"error: {e}"}

        if not results:
            return {**neutral, "status": "no_articles_found"}

        result = results[0]
        score = result.get("final_sentiment_score")

        if score is None:
            # Articles were found but none could be scored (all analyses failed).
            return {
                **neutral,
                "headline_count": 0,
                "status": "no_articles_scored",
                "articles": result.get("articles", []),
            }

        return {
            "score": round(float(score), 4),
            "label": sentiment_label(score),
            "headline_count": int(result.get("article_count", 0)),
            "status": "ok",
            "articles": result.get("articles", []),
        }
