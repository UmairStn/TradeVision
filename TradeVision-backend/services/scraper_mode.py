from enum import Enum

class ScraperMode(Enum):
    """
    Controls which news-fetching strategy NewsScraper uses.

    GOOGLE_NEWS_RSS:
        Queries the Google News RSS feed per company.
        Fast, reliable, no Playwright needed, covers hundreds of Sri Lankan news sites.
        Best for: production use and quick testing.

    WEBSITE_SEARCH:
        Builds search URLs directly on target Sri Lankan news sites (ft.lk, lbo.lk, etc.)
        and scrapes the results using Playwright.
        Best for: pulling specifically from curated local Sri Lankan sources.

    BOTH:
        Runs GOOGLE_NEWS_RSS first, then WEBSITE_SEARCH, and combines all results.
        Best for: maximum coverage.
    """
    GOOGLE_NEWS_RSS  = "google_news_rss"
    WEBSITE_SEARCH   = "website_search"
    BOTH             = "both"
