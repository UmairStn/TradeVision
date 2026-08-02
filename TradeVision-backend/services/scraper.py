import re
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
import email.utils
from bs4 import BeautifulSoup
# pyrefly: ignore [missing-import]
from playwright.sync_api import sync_playwright

from services.scraper_mode import ScraperMode


# ─────────────────────────────────────────────────────────────
#  Search URL templates for WEBSITE_SEARCH mode
#  Add new sites here — {query} will be replaced with the
#  URL-encoded company name automatically.
# ─────────────────────────────────────────────────────────────
WEBSITE_SEARCH_TEMPLATES = [
    "https://www.ft.lk/?s={query}",
    "https://economynext.com/?s={query}",
    "https://lbo.lk/?s={query}",
]


class NewsScraper:
    def __init__(self, mode: ScraperMode = ScraperMode.GOOGLE_NEWS_RSS):
        """
        Args:
            mode: ScraperMode.GOOGLE_NEWS_RSS  → fast, reliable, no browser needed
                  ScraperMode.WEBSITE_SEARCH   → scrapes specific Sri Lankan news sites
        """
        self.mode = mode

        # Only launch Playwright browser when scraping websites directly or in BOTH mode
        if self.mode in (ScraperMode.WEBSITE_SEARCH, ScraperMode.BOTH):
            self._init_browser()

    # ──────────────────────────────────────────────
    #  Browser lifecycle (WEBSITE_SEARCH mode only)
    # ──────────────────────────────────────────────

    def _init_browser(self):
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=True)
        self._context = self._browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
        )

    def close(self):
        """Must be called after scraping to free Playwright resources."""
        if self.mode in (ScraperMode.WEBSITE_SEARCH, ScraperMode.BOTH):
            if hasattr(self, '_context'):
                self._context.close()
            if hasattr(self, '_browser'):
                self._browser.close()
            if hasattr(self, '_playwright'):
                self._playwright.stop()

    # ──────────────────────────────────────────────
    #  Shared utilities
    # ──────────────────────────────────────────────

    def clean_text(self, text: str) -> str:
        return re.sub(r'\s+', ' ', text).strip()

    def _get_age_days(self, pub_date_str: str) -> int:
        """Calculate how many days old an article is based on RSS pubDate."""
        if not pub_date_str:
            return 0  # Default to 0 (fresh) if no date found
        try:
            dt = email.utils.parsedate_to_datetime(pub_date_str)
            now = datetime.now(timezone.utc)
            delta = now - dt
            return max(0, delta.days)
        except Exception:
            return 0  # Default to 0 if parsing fails

    def _fetch_page_playwright(self, url: str) -> str:
        """Fetch a page HTML using headless Chromium (WEBSITE_SEARCH mode)."""
        try:
            page = self._context.new_page()
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            content = page.content()
            page.close()
            return content
        except Exception as e:
            print(f"  [Playwright] Exception fetching {url}: {e}")
            return ""

    def _fetch_article_body(self, article_url: str, use_playwright: bool = False) -> str:
        """Fetch the first 3 paragraphs of an article for FinBERT input."""
        if use_playwright:
            html = self._fetch_page_playwright(article_url)
        else:
            # For RSS mode we use plain urllib (fast, no browser needed)
            try:
                req = urllib.request.Request(
                    article_url,
                    headers={"User-Agent": "Mozilla/5.0"}
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    html = resp.read().decode("utf-8", errors="ignore")
            except Exception as e:
                print(f"  [urllib] Exception fetching article body {article_url}: {e}")
                return ""

        soup = BeautifulSoup(html, "html.parser")
        paragraphs = soup.find_all("p")
        return " ".join([self.clean_text(p.get_text()) for p in paragraphs[:3]])

    # ──────────────────────────────────────────────
    #  Public entry point (mode router)
    # ──────────────────────────────────────────────

    def scrape_stock_news(
        self,
        stock_list: list[dict],
        target_urls: list[str] | None = None,
    ) -> list[dict]:
        """
        Scrape news for every stock in stock_list.

        Args:
            stock_list:  list of {"ticker": "JKH.N0000", "name": "John Keells"}
            target_urls: only used by WEBSITE_SEARCH mode (ignored for RSS mode)
        """
        if self.mode == ScraperMode.GOOGLE_NEWS_RSS:
            return self._scrape_via_rss(stock_list)
        elif self.mode == ScraperMode.WEBSITE_SEARCH:
            return self._scrape_via_website_search(stock_list)
        elif self.mode == ScraperMode.BOTH:
            print("\n--- Running BOTH Modes: RSS + Website Search ---")
            rss_results = self._scrape_via_rss(stock_list)
            web_results = self._scrape_via_website_search(stock_list)
            
            # Combine and deduplicate
            combined = rss_results.copy()
            existing_signatures = set((r["article_url"], r["ticker"]) for r in combined)
            
            for res in web_results:
                if (res["article_url"], res["ticker"]) not in existing_signatures:
                    combined.append(res)
                    
            print(f"--- BOTH Modes Complete: {len(combined)} Total Unique Articles Found ---\n")
            return combined
        return []

    # ──────────────────────────────────────────────
    #  Mode 1: Google News RSS
    # ──────────────────────────────────────────────

    def _scrape_via_rss(self, stock_list: list[dict]) -> list[dict]:
        """
        For each company, query Google News RSS and extract matching articles.
        No browser needed — Google News returns clean XML.
        """
        found_articles = []

        for stock in stock_list:
            company_name = stock["name"]
            query = urllib.parse.quote_plus(f"{company_name} Sri Lanka stock")
            rss_url = f"https://news.google.com/rss/search?q={query}&hl=en&gl=LK&ceid=LK:en"

            print(f"[RSS] Searching Google News for: '{company_name}'")
            try:
                req = urllib.request.Request(rss_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    xml_content = resp.read()
            except Exception as e:
                print(f"  [RSS] Failed to fetch feed for '{company_name}': {e}")
                continue

            try:
                root = ET.fromstring(xml_content)
            except ET.ParseError as e:
                print(f"  [RSS] XML parse error for '{company_name}': {e}")
                continue

            items = root.findall(".//item")
            
            # Filter to articles from the last 30 days
            fresh_items = []
            for item in items:
                pub_date = item.findtext("pubDate", "")
                age = self._get_age_days(pub_date)
                
                if age <= 30:
                    # Tag the item with its calculated age so we can use it later
                    item.set("calculated_age", str(age))
                    fresh_items.append(item)
                    if len(fresh_items) >= 15:  # Pull up to 15 RSS articles per stock to balance fresh/old
                        break
            
            print(f"  Processing latest {len(fresh_items)} fresh articles (<= 30 days old) for '{company_name}'")

            for item in fresh_items:
                headline = self.clean_text(item.findtext("title", ""))
                article_url = self.clean_text(item.findtext("link", ""))
                age_days = int(item.get("calculated_age", 0))

                if not headline or not article_url:
                    continue

                # Fetch article body for better FinBERT accuracy
                body_text = self._fetch_article_body(article_url, use_playwright=False)
                combined_text = f"{headline}. {body_text}" if body_text else headline

                found_articles.append({
                    "ticker": stock["ticker"],
                    "stock_name": company_name,
                    "headline": headline,
                    "full_text": combined_text,
                    "article_url": article_url,
                    "age_days": age_days,
                    "scraped_at": datetime.now().isoformat(),
                    "source": "google_news_rss",
                })

        return found_articles

    # ──────────────────────────────────────────────
    #  Mode 2: Website Search (Playwright)
    # ──────────────────────────────────────────────

    def _scrape_via_website_search(self, stock_list: list[dict]) -> list[dict]:
        """
        For each company + search URL template combination, build a search URL,
        scrape the results with Playwright, and extract matching articles.
        """
        found_articles = []

        for stock in stock_list:
            company_name = stock["name"]
            query = urllib.parse.quote_plus(company_name)
            stock_article_count = 0

            for template in WEBSITE_SEARCH_TEMPLATES:
                # Limit to 3 articles per stock from Website Search to reach the total 10 limit
                if stock_article_count >= 3:
                    break
                    
                search_url = template.format(query=query)
                print(f"[WebSearch] Searching '{company_name}' on {search_url}")

                html = self._fetch_page_playwright(search_url)
                if not html:
                    continue

                soup = BeautifulSoup(html, "html.parser")
                links = soup.find_all("a", href=True)
                print(f"  Found {len(links)} links on search results page")

                for link in links:
                    if stock_article_count >= 3:
                        break
                        
                    headline = self.clean_text(link.get_text())
                    article_url = link.get("href", "")

                    if not article_url:
                        continue
                    if article_url.startswith("/"):
                        base = "/".join(search_url.split("/")[:3])
                        article_url = base + article_url
                    if len(headline) < 20 or not article_url.startswith("http"):
                        continue

                    # Deduplicate
                    if any(
                        a["article_url"] == article_url and a["ticker"] == stock["ticker"]
                        for a in found_articles
                    ):
                        continue

                    body_text = self._fetch_article_body(article_url, use_playwright=True)
                    combined_text = f"{headline}. {body_text}" if body_text else headline

                    found_articles.append({
                        "ticker": stock["ticker"],
                        "stock_name": company_name,
                        "headline": headline,
                        "full_text": combined_text,
                        "article_url": article_url,
                        "age_days": 0,  # Website search results are assumed to be today's news
                        "scraped_at": datetime.now().isoformat(),
                        "source": "website_search",
                    })
                    stock_article_count += 1

        return found_articles
