#!/usr/bin/env python3
"""
FlyRank Internship · Backend Track · Week 5 · Assignment A9
The Polite Scraper — Stage 2: Discover Three Catalogue Pages
"""

import os
import time
from pathlib import Path
from urllib.parse import urljoin
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


class FetchError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def to_fetch_url(canonical_url: str) -> str:
    if FETCH_BASE_URL != CANONICAL_BASE_URL and canonical_url.startswith(CANONICAL_BASE_URL):
        return FETCH_BASE_URL + canonical_url[len(CANONICAL_BASE_URL):]
    return canonical_url


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


def discover_catalogue_pages(max_pages: int = MAX_CATALOGUE_PAGES) -> tuple[int, int, list[tuple[str, str]]]:
    """
    Follow pagination up to max_pages and return:
    (catalogue_pages_count, total_discovered_count, deduplicated_list_of_(book_url, source_page))
    """
    current_url = f"{CANONICAL_BASE_URL}/catalogue/page-1.html"
    is_first_req = [True]
    pages_visited = 0
    discovered_all: list[tuple[str, str]] = []

    while current_url and pages_visited < max_pages:
        pages_visited += 1
        cache_path = CACHE_DIR / f"catalogue-page-{pages_visited}.html"
        html_text, _ = fetch_page(current_url, cache_path, is_first_req)
        soup = BeautifulSoup(html_text, "html.parser")

        for link in soup.select("article.product_pod h3 a"):
            href = link.get("href", "").strip()
            if href:
                abs_url = urljoin(current_url, href)
                discovered_all.append((abs_url, current_url))

        next_el = soup.select_one("li.next a")
        if next_el and next_el.get("href") and pages_visited < max_pages:
            current_url = urljoin(current_url, next_el["href"].strip())
        else:
            current_url = ""

    unique_pairs: list[tuple[str, str]] = []
    seen: set[str] = set()
    for book_url, source_page in discovered_all:
        if book_url not in seen:
            seen.add(book_url)
            unique_pairs.append((book_url, source_page))

    print(f"catalogue_pages={pages_visited}, discovered={len(discovered_all)}, unique_urls={len(unique_pairs)}")
    return pages_visited, len(discovered_all), unique_pairs


if __name__ == "__main__":
    discover_catalogue_pages()
