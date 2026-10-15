#!/usr/bin/env python3
"""
FlyRank Internship · Backend Track · Week 5 · Assignment A9
The Polite Scraper — Stage 3: Extract the Raw Records
"""

import os
import re
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/ThatoNtaopane/crud-todo-api)"
TIMEOUT_SECONDS = 10
POLITE_DELAY_SECONDS = 0.5
MAX_CATALOGUE_PAGES = 3

BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / "cache"
CANONICAL_BASE_URL = "https://books.toscrape.com"
FETCH_BASE_URL = os.environ.get("SCRAPER_BASE_URL", CANONICAL_BASE_URL).rstrip("/")
RATING_WORDS = {"One", "Two", "Three", "Four", "Five"}


class FetchError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def to_fetch_url(canonical_url: str) -> str:
    if FETCH_BASE_URL != CANONICAL_BASE_URL and canonical_url.startswith(CANONICAL_BASE_URL):
        return FETCH_BASE_URL + canonical_url[len(CANONICAL_BASE_URL):]
    return canonical_url


def book_cache_path(book_url: str) -> Path:
    parts = [p for p in urlparse(book_url).path.split("/") if p and p != "index.html"]
    slug = parts[-1] if parts else "unknown-book"
    return CACHE_DIR / "books" / f"{slug}.html"


def fetch_page(canonical_url: str, cache_path: Path, is_first_network_request: list[bool]) -> tuple[str, bool]:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if cache_path.exists():
        raw_bytes = cache_path.read_bytes()
        print(f"CACHE HIT {canonical_url} ({len(raw_bytes)} bytes)")
        return raw_bytes.decode("utf-8"), True

    if not is_first_network_request[0]:
        time.sleep(POLITE_DELAY_SECONDS)
    is_first_network_request[0] = False

    headers = {"User-Agent": USER_AGENT}
    response = requests.get(to_fetch_url(canonical_url), headers=headers, timeout=TIMEOUT_SECONDS)
    if response.status_code != 200:
        raise FetchError(f"Failed fetch for {canonical_url}: HTTP {response.status_code}", response.status_code)

    raw_bytes = response.content
    cache_path.write_bytes(raw_bytes)
    print(f"FETCH {canonical_url} ({len(raw_bytes)} bytes)")
    return raw_bytes.decode("utf-8"), False


def extract_raw_record(html_text: str, product_url: str, source_page: str, fetched_at: str) -> dict:
    """
    Extract the 8 raw fields scoped strictly to article.product_page.
    Store None when description is absent.
    """
    soup = BeautifulSoup(html_text, "html.parser")
    product_article = soup.select_one("article.product_page")
    if product_article is None:
        raise ValueError(f"Missing article.product_page in {product_url}")

    product_main = product_article.select_one("div.product_main")
    if product_main is None:
        raise ValueError(f"Missing div.product_main in {product_url}")

    title_el = product_main.select_one("h1")
    price_el = product_main.select_one("p.price_color")
    avail_el = product_main.select_one("p.availability")
    rating_el = product_main.select_one("p.star-rating")

    title = re.sub(r"\s+", " ", title_el.get_text(strip=True)) if title_el else ""
    price_text = price_el.get_text(strip=True) if price_el else ""
    availability_text = re.sub(r"\s+", " ", avail_el.get_text(strip=True)) if avail_el else ""

    rating_text = ""
    if rating_el:
        classes = rating_el.get("class", [])
        for cls in classes:
            if cls in RATING_WORDS:
                rating_text = cls
                break

    desc_el = product_article.select_one("#product_description + p")
    description = None
    if desc_el is not None:
        cleaned_desc = re.sub(r"\s+", " ", desc_el.get_text(strip=True))
        if cleaned_desc:
            description = cleaned_desc

    return {
        "title": title,
        "product_url": product_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": fetched_at,
    }
