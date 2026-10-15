#!/usr/bin/env python3
"""
FlyRank Internship · Backend Track · Week 5 · Assignment A9
The Polite Scraper — Stage 1: Fetch Once, Cache Once
"""

import os
from pathlib import Path
import requests

USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/ThatoNtaopane/crud-todo-api)"
TIMEOUT_SECONDS = 10
BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / "cache"
BASE_URL = os.environ.get("SCRAPER_BASE_URL", "https://books.toscrape.com").rstrip("/")


class FetchError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def fetch_page(url: str, cache_path: Path) -> tuple[str, bool]:
    """
    Fetch an HTML page politely or return the saved copy from cache.
    Returns (html_text, was_cache_hit).
    """
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if cache_path.exists():
        raw_bytes = cache_path.read_bytes()
        print(f"CACHE HIT {url} ({len(raw_bytes)} bytes)")
        return raw_bytes.decode("utf-8"), True

    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=TIMEOUT_SECONDS)
    if response.status_code != 200:
        raise FetchError(f"Failed fetch for {url}: HTTP {response.status_code}", response.status_code)

    raw_bytes = response.content
    cache_path.write_bytes(raw_bytes)
    print(f"FETCH {url} ({len(raw_bytes)} bytes)")
    return raw_bytes.decode("utf-8"), False


if __name__ == "__main__":
    page_1_url = f"{BASE_URL}/catalogue/page-1.html"
    cache_file = CACHE_DIR / "catalogue-page-1.html"
    fetch_page(page_1_url, cache_file)
