from services.scraper import NewsScraper
from services.scraper_mode import ScraperMode
# pyrefly: ignore [missing-import]
from services.sentiment import SentimentAnalyzer

class NewsSentimentPipeline:
    def __init__(self, mode: ScraperMode = ScraperMode.GOOGLE_NEWS_RSS):
        self.scraper = NewsScraper(mode=mode)
        self.analyzer = SentimentAnalyzer()

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

            # Keep only the latest 10 articles per stock ticker.
            # (Accommodates 7 from RSS + 3 from Website Search in BOTH mode)
            MAX_PER_STOCK = 10
            ticker_counts: dict[str, int] = {}
            trimmed_articles = []
            for article in scraped_articles:
                ticker = article["ticker"]
                count = ticker_counts.get(ticker, 0)
                if count < MAX_PER_STOCK:
                    trimmed_articles.append(article)
                    ticker_counts[ticker] = count + 1

            if len(trimmed_articles) < len(scraped_articles):
                print(f"Trimmed to {len(trimmed_articles)} articles ({MAX_PER_STOCK} per stock) for FinBERT...")
            scraped_articles = trimmed_articles

            # Run each article through FinBERT and collect raw scores per ticker
            # We separate them by age: recent (<= 7 days) and older (8-30 days)
            ticker_scores_recent: dict[str, list[float]] = {}
            ticker_scores_older: dict[str, list[float]] = {}
            ticker_meta: dict[str, dict] = {}

            for article in scraped_articles:
                print(f"Analyzing: {article['headline'][:70]}...")
                sentiment_res = self.analyzer.analyze_text(article["full_text"])
                score = sentiment_res["sentiment_score"]

                ticker = article["ticker"]
                age = article.get("age_days", 0)

                if ticker not in ticker_meta:
                    ticker_scores_recent[ticker] = []
                    ticker_scores_older[ticker] = []
                    ticker_meta[ticker] = {
                        "ticker":     ticker,
                        "stock_name": article["stock_name"],
                        "articles":   [],
                    }

                if age <= 7:
                    ticker_scores_recent[ticker].append(score)
                else:
                    ticker_scores_older[ticker].append(score)

                ticker_meta[ticker]["articles"].append({
                    "headline":        article["headline"],
                    "article_url":     article["article_url"],
                    "source":          article.get("source", "unknown"),
                    "sentiment_score": score,
                    "raw_scores":      sentiment_res["raw_scores"],
                    "scraped_at":      article["scraped_at"],
                })

            # Aggregate: calculate recent avg, older avg, and final weighted score
            aggregated = []
            for ticker in ticker_meta.keys():
                recent_list = ticker_scores_recent[ticker]
                older_list = ticker_scores_older[ticker]
                
                recent_avg = sum(recent_list) / len(recent_list) if recent_list else 0.0
                older_avg = sum(older_list) / len(older_list) if older_list else 0.0
                
                # Weighted Final Sentiment (70% weight to <=7 days, 30% to 8-30 days)
                if recent_list and older_list:
                    final_score = (recent_avg * 0.7) + (older_avg * 0.3)
                elif recent_list:
                    final_score = recent_avg
                elif older_list:
                    final_score = older_avg
                else:
                    final_score = 0.0

                aggregated.append({
                    "ticker":               ticker,
                    "stock_name":           ticker_meta[ticker]["stock_name"],
                    "recent_sentiment_7d":  round(recent_avg, 4),
                    "older_sentiment_30d":  round(older_avg, 4),
                    "final_sentiment_score": round(final_score, 4),
                    "article_count":        len(recent_list) + len(older_list),
                    "recent_count":         len(recent_list),
                    "older_count":          len(older_list),
                    "articles":             ticker_meta[ticker]["articles"],
                })

            return aggregated
        finally:
            # Always clean up Playwright browser (no-op in RSS mode)
            self.scraper.close()