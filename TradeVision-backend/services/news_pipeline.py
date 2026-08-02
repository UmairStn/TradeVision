from services.scraper import NewsScraper
# pyrefly: ignore [missing-import]
from services.sentiment import SentimentAnalyzer

class NewsSentimentPipeline:
    def __init__(self):
        self.scraper = NewsScraper()
        self.analyzer = SentimentAnalyzer()

    def process_news_for_stocks(self, stock_list: list[dict], target_urls: list[str]) -> list[dict]:
        """
        Scrapes news for requested stocks and processes each article through FinBERT.
        """
        try:
            print("Starting news scraping process...")
            scraped_articles = self.scraper.scrape_stock_news(stock_list, target_urls)
            print(f"Scraped {len(scraped_articles)} relevant articles.")

            results = []
            for article in scraped_articles:
                print(f"Analyzing sentiment for: {article['headline'][:50]}...")
                
                # Pass article text into FinBERT
                sentiment_res = self.analyzer.analyze_text(article["full_text"])

                results.append({
                    "ticker": article["ticker"],
                    "stock_name": article["stock_name"],
                    "headline": article["headline"],
                    "article_url": article["article_url"],
                    "sentiment_score": sentiment_res["sentiment_score"], # Range: -1.0 to +1.0
                    "raw_scores": sentiment_res["raw_scores"],
                    "scraped_at": article["scraped_at"]
                })

            return results
        finally:
            # Ensure Playwright browser is properly closed
            self.scraper.close()