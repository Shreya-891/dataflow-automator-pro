"""
DataFlow Automator Pro - Web Scraping Module
Provides multi-source web scrapers with retry backoff, User-Agent rotation,
structured data extraction (news, products, quotes, custom URLs), and pipeline exports.
"""

import time
import random
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
import pandas as pd

from core.logger import logger
from core.exceptions import ScrapingError

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
]


class WebScraper:
    """
    Robust Web Scraping engine with request headers rotation and structured parsers.
    """
    def __init__(self, timeout: int = 15, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()

    def _get_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "DNT": "1",
            "Connection": "keep-alive"
        }

    def fetch_page(self, url: str) -> str:
        """Fetch raw HTML with retry backoff."""
        for attempt in range(1, self.max_retries + 1):
            try:
                headers = self._get_headers()
                logger.info(f"Fetching URL: {url} (Attempt {attempt}/{self.max_retries})")
                response = self.session.get(url, headers=headers, timeout=self.timeout)
                response.raise_for_status()
                return response.text
            except Exception as e:
                logger.warning(f"Fetch attempt {attempt} failed for {url}: {e}")
                if attempt == self.max_retries:
                    logger.error(f"Exhausted all retries for URL: {url}")
                    raise ScrapingError(f"Failed to fetch webpage: {url}", {"error": str(e)})
                time.sleep(attempt * 1.5)
        return ""

    def scrape_books_catalog(self, max_pages: int = 2) -> pd.DataFrame:
        """
        Scrape books catalog from books.toscrape.com (safe public scraping sandbox).
        Extracts title, price, rating, stock status, and detail URL.
        """
        base_url = "http://books.toscrape.com/catalogue/page-{}.html"
        records = []
        rating_map = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}

        for page in range(1, max_pages + 1):
            url = base_url.format(page)
            try:
                html = self.fetch_page(url)
                soup = BeautifulSoup(html, "html.parser")
                products = soup.select("article.product_pod")

                for p in products:
                    title_elem = p.select_one("h3 a")
                    title = title_elem["title"] if title_elem and "title" in title_elem.attrs else (title_elem.text if title_elem else "Unknown")
                    price_elem = p.select_one("p.price_color")
                    price_str = price_elem.text if price_elem else "£0.00"
                    # clean price
                    price_num = float(price_str.replace("£", "").replace("Â", "").strip()) if price_str else 0.0

                    rating_elem = p.select_one("p.star-rating")
                    rating_val = 0
                    if rating_elem:
                        classes = rating_elem.get("class", [])
                        for c in classes:
                            if c in rating_map:
                                rating_val = rating_map[c]

                    avail_elem = p.select_one("p.instock.availability")
                    in_stock = "In stock" in (avail_elem.text if avail_elem else "")

                    records.append({
                        "title": title,
                        "price_gbp": price_num,
                        "rating_stars": rating_val,
                        "in_stock": in_stock,
                        "category": "Books"
                    })
            except Exception as e:
                logger.error(f"Error scraping books page {page}: {e}")
                break

        df = pd.DataFrame(records)
        logger.info(f"Scraped {len(df)} books across {max_pages} pages.")
        return df

    def scrape_quotes_feed(self, max_pages: int = 2) -> pd.DataFrame:
        """
        Scrape quotes from quotes.toscrape.com (public sandbox).
        Extracts quote text, author, and tags.
        """
        base_url = "http://quotes.toscrape.com/page/{}/"
        records = []

        for page in range(1, max_pages + 1):
            url = base_url.format(page)
            try:
                html = self.fetch_page(url)
                soup = BeautifulSoup(html, "html.parser")
                quotes = soup.select("div.quote")

                for q in quotes:
                    text_elem = q.select_one("span.text")
                    author_elem = q.select_one("small.author")
                    tag_elems = q.select("div.tags a.tag")

                    text = text_elem.text.strip("“”") if text_elem else ""
                    author = author_elem.text.strip() if author_elem else "Anonymous"
                    tags = ", ".join([t.text.strip() for t in tag_elems])

                    records.append({
                        "quote": text,
                        "author": author,
                        "tags": tags,
                        "length": len(text)
                    })
            except Exception as e:
                logger.error(f"Error scraping quotes page {page}: {e}")
                break

        df = pd.DataFrame(records)
        logger.info(f"Scraped {len(df)} quotes across {max_pages} pages.")
        return df

    def scrape_hacker_news(self, limit: int = 20) -> pd.DataFrame:
        """
        Scrape top tech headlines from Hacker News (news.ycombinator.com).
        """
        url = "https://news.ycombinator.com/"
        records = []

        try:
            html = self.fetch_page(url)
            soup = BeautifulSoup(html, "html.parser")
            items = soup.select("tr.athing")

            for item in items[:limit]:
                title_elem = item.select_one("span.titleline > a")
                if not title_elem:
                    continue

                title = title_elem.text.strip()
                link = title_elem.get("href", "")

                # Subtext row contains score and author
                subtext = item.find_next_sibling("tr")
                score = 0
                author = "Unknown"
                comments = 0

                if subtext:
                    score_elem = subtext.select_one("span.score")
                    if score_elem:
                        score_text = score_elem.text.replace(" points", "").replace(" point", "")
                        score = int(score_text) if score_text.isdigit() else 0

                    by_elem = subtext.select_one("a.hnuser")
                    if by_elem:
                        author = by_elem.text.strip()

                records.append({
                    "headline": title,
                    "url": link,
                    "points": score,
                    "author": author,
                    "source": "Hacker News"
                })
        except Exception as e:
            logger.error(f"Error scraping Hacker News: {e}")
            raise ScrapingError("Hacker News scraping failed", {"error": str(e)})

        df = pd.DataFrame(records)
        logger.info(f"Scraped {len(df)} tech news headlines.")
        return df

    def scrape_custom_url(self, url: str) -> Dict[str, Any]:
        """
        Extract generic structured content (meta title, description, headings, tables, links) from any URL.
        """
        try:
            html = self.fetch_page(url)
            soup = BeautifulSoup(html, "html.parser")

            # Title & Meta
            page_title = soup.title.string.strip() if soup.title and soup.title.string else "Untitled"
            meta_desc = ""
            desc_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
            if desc_tag and "content" in desc_tag.attrs:
                meta_desc = desc_tag["content"].strip()

            # Headings
            h1s = [h.text.strip() for h in soup.find_all("h1") if h.text.strip()]
            h2s = [h.text.strip() for h in soup.find_all("h2") if h.text.strip()][:10]

            # Links
            links = []
            for a in soup.find_all("a", href=True)[:25]:
                text = a.text.strip()
                if text and len(text) < 80:
                    links.append({"text": text, "href": a["href"]})

            # Tables to DataFrame preview
            tables_data = []
            for t in soup.find_all("table")[:3]:
                try:
                    df_table = pd.read_html(str(t))[0]
                    tables_data.append(df_table.head(10).to_dict(orient="records"))
                except Exception:
                    pass

            return {
                "url": url,
                "title": page_title,
                "meta_description": meta_desc,
                "h1_headings": h1s,
                "h2_headings": h2s,
                "links": links,
                "tables_count": len(soup.find_all("table")),
                "tables_preview": tables_data
            }
        except Exception as e:
            logger.error(f"Custom URL scraping error: {e}")
            raise ScrapingError(f"Failed to scrape {url}", {"error": str(e)})
