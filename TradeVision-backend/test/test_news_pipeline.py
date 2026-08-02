from services.news_pipeline import NewsSentimentPipeline
from services.scraper_mode import ScraperMode

if __name__ == "__main__":

    # ──────────────────────────────────────────────────────────────────
    #  SWITCH MODE HERE:
    #    ScraperMode.GOOGLE_NEWS_RSS  → fast, reliable, uses Google News
    #    ScraperMode.BOTH             → runs both methods simultaneously!
    # ──────────────────────────────────────────────────────────────────
    MODE = ScraperMode.BOTH

    pipeline = NewsSentimentPipeline(mode=MODE)

    # Target stocks
    target_stocks = [
        {"ticker": "JKH.N0000",  "name": "John Keells"},
        {"ticker": "SAMP.N0000", "name": "Sampath Bank"},
        {"ticker": "COMB.N0000", "name": "Commercial Bank"},
    ]

    print(f"\n--- Running News Scraper + FinBERT Pipeline (Mode: {MODE.value}) ---\n")
    processed_news = pipeline.process_news_for_stocks(target_stocks)

    print("\n" + "=" * 60)
    print("  FINAL SCRAPED NEWS SENTIMENT SCORES  ")
    print("=" * 60 + "\n")

    if not processed_news:
        print("No articles found. Try switching the MODE above.")
    else:
        for item in processed_news:
            direction = "Bullish" if item['final_sentiment_score'] > 0.1 else ("Bearish" if item['final_sentiment_score'] < -0.1 else "Neutral")
            print(f"  [{item['ticker']}]  {item['stock_name']}")
            print(f"     <= 7 Days Sentiment (Weight 70%)  : {item['recent_sentiment_7d']:+.4f}  (Based on {item['recent_count']} articles)")
            print(f"     8-30 Days Sentiment (Weight 30%)  : {item['older_sentiment_30d']:+.4f}  (Based on {item['older_count']} articles)")
            print(f"     ---------------------------------------------")
            print(f"     FINAL WEIGHTED SENTIMENT SCORE    : {item['final_sentiment_score']:+.4f}  ({direction})\n")