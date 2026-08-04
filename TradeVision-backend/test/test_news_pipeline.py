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
        def fmt(score) -> str:
            """Scores are None when nothing could be scored — not 0.0."""
            return "   n/a  " if score is None else f"{score:+.4f}"

        for item in processed_news:
            final = item['final_sentiment_score']
            if final is None:
                direction = "No data"
            elif final > 0.1:
                direction = "Bullish"
            elif final < -0.1:
                direction = "Bearish"
            else:
                direction = "Neutral"

            print(f"  [{item['ticker']}]  {item['stock_name']}")
            print(f"     <= 7 Days Sentiment (Weight 70%)  : {fmt(item['recent_sentiment_7d'])}  (Based on {item['recent_count']} articles)")
            print(f"     8-30 Days Sentiment (Weight 30%)  : {fmt(item['older_sentiment_30d'])}  (Based on {item['older_count']} articles)")
            if item['failed_count']:
                print(f"     Excluded (analysis failed)        : {item['failed_count']} articles")
            print(f"     ---------------------------------------------")
            print(f"     FINAL WEIGHTED SENTIMENT SCORE    : {fmt(final)}  ({direction})\n")