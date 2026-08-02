import re
from datetime import datetime
from bs4 import BeautifulSoup
# pyrefly: ignore [missing-import]
from playwright.sync_api import sync_playwright

class NewsScraper:
    def __init__(self):
        self.playwright = sync_playwright().start()
        # Launch Chromium headlessly
        self.browser = self.playwright.chromium.launch(headless=True)
        # Use a single context to present a consistent, real browser fingerprint
        self.context = self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )

    def close(self):
        """Must be called to clean up Playwright resources."""
        if hasattr(self, 'context'):
            self.context.close()
        if hasattr(self, 'browser'):
            self.browser.close()
        if hasattr(self, 'playwright'):
            self.playwright.stop()

    def fetch_page(self, url: str) -> str:
        try:
            page = self.context.new_page()
            # wait_until="networkidle" waits until network requests stop (perfect for React/Angular SPAs)
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            content = page.content()
            page.close()
            return content
        except Exception as e:
            print(f"Exception fetching {url} with Playwright: {e}")
            return ""

    def clean_text(self, text: str) -> str:
        return re.sub(r'\s+', ' ', text).strip()

    def fetch_article_body(self, article_url: str) -> str:
        """Fetches paragraph text from inside the article page."""
        html_content = self.fetch_page(article_url)
        if not html_content:
            return ""

        soup = BeautifulSoup(html_content, 'html.parser')
        paragraphs = soup.find_all('p')
        
        # Combine the first 3 paragraphs into a single text block
        body_text = " ".join([self.clean_text(p.get_text()) for p in paragraphs[:3]])
        return body_text

    def scrape_stock_news(self, stock_list: list[dict], target_urls: list[str]) -> list[dict]:
        found_articles = []

        for url in target_urls:
            print(f"Fetching news from {url}...")
            html_content = self.fetch_page(url)
            if not html_content:
                print(f"Warning: No content returned for {url}")
                continue

            soup = BeautifulSoup(html_content, 'html.parser')
            links = soup.find_all('a', href=True)
            print(f"Found {len(links)} links on {url}")

            for link in links:
                headline = self.clean_text(link.get_text())
                article_url = link.get('href', '')
                
                if not article_url:
                    continue

                if article_url.startswith('/'):
                    base_url = "/".join(url.split("/")[:3])
                    article_url = base_url + article_url

                if len(headline) < 15 or not article_url.startswith('http'):
                    continue

                # Temporary debug: Print all valid headlines so we can see what's actually on the page
                print(f"  -> Found Headline: '{headline}'")

                headline_lower = headline.lower()

                for stock in stock_list:
                    ticker_clean = stock["ticker"].split(".")[0].lower()
                    name_lower = stock["name"].lower()

                    if ticker_clean in headline_lower or name_lower in headline_lower:
                        if any(a['article_url'] == article_url and a['ticker'] == stock["ticker"] for a in found_articles):
                            continue

                        # Fetch article body text for better FinBERT accuracy
                        body_text = self.fetch_article_body(article_url)
                        
                        # Use body text if available, otherwise fallback to headline
                        combined_text = f"{headline}. {body_text}" if body_text else headline

                        found_articles.append({
                            "ticker": stock["ticker"],
                            "stock_name": stock["name"],
                            "headline": headline,
                            "full_text": combined_text,
                            "article_url": article_url,
                            "scraped_at": datetime.now().isoformat()
                        })
                        
        return found_articles