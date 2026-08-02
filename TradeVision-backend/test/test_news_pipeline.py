from services.news_pipeline import NewsSentimentPipeline

if __name__ == "__main__":
    pipeline = NewsSentimentPipeline()

    # Target stocks
    target_stocks = [
        {"ticker": "DIV", "name": "Dividend"},
        {"ticker": "REP", "name": "Report"}
    ]



    # Live CSE news sources
    news_urls = [
        "https://www.cse.lk/news-events/press-releases",
        "https://economynext.com/",
        "https://www.ft.lk/financial-services/42"
    ]

    print("\n--- Running News Scraper + FinBERT Pipeline ---\n")
    processed_news = pipeline.process_news_for_stocks(target_stocks, news_urls)

    print("\n" + "="*60)
    print("  FINAL SCRAPED NEWS SENTIMENT SCORES  ")
    print("="*60 + "\n")

    for idx, item in enumerate(processed_news, start=1):
        print(f"[{idx}] Ticker  : {item['ticker']} ({item['stock_name']})")
        print(f"    Headline: {item['headline']}")
        print(f"    Link    : {item['article_url']}")
        print(f"    Scores  : {item['raw_scores']}")
        print(f"    Score   : {item['sentiment_score']}  (-1.0 = Very Bearish, +1.0 = Very Bullish)\n")