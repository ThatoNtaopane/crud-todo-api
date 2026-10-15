#!/usr/bin/env python3
"""
FlyRank Internship · Backend Track · Week 5 · Assignment A9
The Polite Scraper — Complete Pipeline (Stages 0–6 + Extras)

Features:
- Stage 0: Target classification & robots.txt verification (--check-robots)
- Stage 1: Polite HTTP fetching with honest User-Agent, timeout, status check, and HTML caching
- Stage 2: Catalogue crawler discovering 3 pages and 60 unique book URLs via urljoin
- Stage 3: Scoped BeautifulSoup extraction (article.product_page) preserving provenance
- Stage 4: Price normalization (£ -> float price_gbp), Pydantic schema validation, idempotent books.json & errors.json
- Stage 5: Fault isolation per book page, smart retry with exponential backoff + jitter + Retry-After,
           deliberate broken URL test support, and honest output/run-report.json
- Extras: CSV export (output/books.csv), SHA-256 record change detection, and local HTML observability dashboard (output/dashboard.html)
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field, ValidationError, validator

# ---------------------------------------------------------------------------
# Politeness & Pipeline Constants
# ---------------------------------------------------------------------------
USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/ThatoNtaopane/crud-todo-api)"
TIMEOUT_SECONDS = 10
POLITE_DELAY_SECONDS = 0.5
MAX_CATALOGUE_PAGES = 3
MAX_RETRIES = 2

BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / "cache"
OUTPUT_DIR = BASE_DIR / "output"

CANONICAL_BASE_URL = "https://books.toscrape.com"
FETCH_BASE_URL = os.environ.get("SCRAPER_BASE_URL", CANONICAL_BASE_URL).rstrip("/")
BROKEN_BOOK_URL = f"{CANONICAL_BASE_URL}/catalogue/broken-book-page-404_000/index.html"

RATING_WORDS = {"One", "Two", "Three", "Four", "Five"}
NON_RETRYABLE_STATUSES = {400, 401, 403, 404, 410}
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


# ---------------------------------------------------------------------------
# Schema Definition (Stage 4 — Pydantic)
# ---------------------------------------------------------------------------
class BookRecord(BaseModel):
    """Validated, normalized schema for a scraped book record."""
    title: str = Field(..., min_length=1)
    product_url: str = Field(..., min_length=1)
    price_text: str = Field(..., min_length=2)
    price_gbp: float = Field(..., gt=0)
    availability_text: str = Field(..., min_length=1)
    rating_text: Literal["One", "Two", "Three", "Four", "Five"]
    description: Optional[str] = None
    source_page: str = Field(..., min_length=1)
    fetched_at: str = Field(..., min_length=10)

    @validator("product_url", "source_page")
    def must_start_with_https(cls, v: str) -> str:
        if not v.startswith("https://"):
            raise ValueError(f"URL must start with https://, got '{v}'")
        return v


class FetchError(Exception):
    """Raised when an HTTP fetch fails after applying polite retry rules."""
    def __init__(self, message: str, status_code: Optional[int] = None, attempts: int = 1):
        super().__init__(message)
        self.status_code = status_code
        self.attempts = attempts


# ---------------------------------------------------------------------------
# Structured Logging & URL Helpers
# ---------------------------------------------------------------------------
def log_structured(event: str, **fields: Any) -> dict[str, Any]:
    entry = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "event": event,
        **fields,
    }
    return entry


def to_fetch_url(canonical_url: str) -> str:
    """Translate canonical URL to local test server URL when SCRAPER_BASE_URL is set."""
    if FETCH_BASE_URL != CANONICAL_BASE_URL and canonical_url.startswith(CANONICAL_BASE_URL):
        return FETCH_BASE_URL + canonical_url[len(CANONICAL_BASE_URL):]
    return canonical_url


def resolve_book_url(page_url: str, relative_href: str) -> str:
    """Turn a relative book href into an absolute canonical URL using urljoin."""
    return urljoin(page_url, relative_href.strip())


def deduplicate_urls(pairs: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Remove duplicate book URLs while preserving discovery order."""
    seen: set[str] = set()
    unique: list[tuple[str, str]] = []
    for book_url, source_page in pairs:
        if book_url not in seen:
            seen.add(book_url)
            unique.append((book_url, source_page))
    return unique


def normalize_price(price_text: str) -> float:
    """Convert raw price string such as '£51.77' into a float 51.77."""
    if not price_text or not isinstance(price_text, str):
        raise ValueError(f"Invalid price_text: {price_text!r}")
    cleaned = price_text.strip().replace("Â", "")
    match = re.match(r"^£\s*(\d+(?:\.\d{1,2})?)$", cleaned)
    if not match:
        raise ValueError(f"Price string {price_text!r} does not match expected GBP format '£XX.XX'")
    val = round(float(match.group(1)), 2)
    if val <= 0:
        raise ValueError(f"Price must be positive, got {val}")
    return val


def parse_retry_after(header_value: Optional[str], fallback_delay: float) -> float:
    """Respect the Retry-After HTTP header when provided by a server."""
    if not header_value:
        return fallback_delay
    try:
        seconds = float(header_value.strip())
        return max(0.0, min(seconds, 30.0))
    except ValueError:
        return fallback_delay


def book_cache_path(book_url: str, cache_dir: Path = CACHE_DIR) -> Path:
    parts = [p for p in urlparse(book_url).path.split("/") if p and p != "index.html"]
    slug = parts[-1] if parts else "unknown-book"
    return cache_dir / "books" / f"{slug}.html"


# ---------------------------------------------------------------------------
# Stage 0: robots.txt Verification
# ---------------------------------------------------------------------------
def check_robots_txt(session: Optional[requests.Session] = None) -> dict[str, Any]:
    robots_url = f"{CANONICAL_BASE_URL}/robots.txt"
    req_client = session or requests
    headers = {"User-Agent": USER_AGENT}
    try:
        resp = req_client.get(to_fetch_url(robots_url), headers=headers, timeout=TIMEOUT_SECONDS)
        if resp.status_code == 404:
            note = "no robots file found"
        elif resp.status_code == 200:
            note = resp.text.strip()
        else:
            note = f"HTTP {resp.status_code}"
        return {"url": robots_url, "status_code": resp.status_code, "note": note}
    except requests.RequestException as exc:
        return {"url": robots_url, "status_code": None, "note": f"request failed: {exc}"}


# ---------------------------------------------------------------------------
# Stage 1 & Stage 5: Polite Fetch + Disk Cache + Smart Retry
# ---------------------------------------------------------------------------
def fetch_html(
    canonical_url: str,
    cache_path: Path,
    stats: dict[str, Any],
    session: Optional[requests.Session] = None,
    use_cache: bool = True,
    polite_delay: float = POLITE_DELAY_SECONDS,
    max_retries: int = MAX_RETRIES,
) -> tuple[str, str, bool]:
    """
    Fetch a page politely or read from cache.
    Returns (html_text, fetched_at_iso, was_cache_hit).
    - Never retries 404 or 403.
    - Retries timeouts and 5xx/429 with exponential backoff + jitter and Retry-After support.
    """
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if use_cache and cache_path.exists():
        raw_bytes = cache_path.read_bytes()
        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        stats["cache_hits"] += 1
        print(f"CACHE HIT {canonical_url} ({len(raw_bytes)} bytes)")
        stats["structured_logs"].append(
            log_structured("cache_hit", url=canonical_url, status=200, attempt=0, size_bytes=len(raw_bytes))
        )
        return raw_bytes.decode("utf-8"), mtime, True

    req_client = session or requests
    headers = {"User-Agent": USER_AGENT}
    target_url = to_fetch_url(canonical_url)

    for attempt in range(1, max_retries + 2):
        if stats["network_requests_sent"] > 0 and polite_delay > 0:
            time.sleep(polite_delay)
        stats["network_requests_sent"] += 1

        try:
            response = req_client.get(target_url, headers=headers, timeout=TIMEOUT_SECONDS)
            status = response.status_code
            stats["structured_logs"].append(
                log_structured("http_response", url=canonical_url, status=status, attempt=attempt)
            )

            if status == 200:
                raw_bytes = response.content
                cache_path.write_bytes(raw_bytes)
                fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                stats["pages_fetched"] += 1
                print(f"FETCH {canonical_url} ({len(raw_bytes)} bytes)")
                return raw_bytes.decode("utf-8"), fetched_at, False

            # Do NOT retry 404 or 403 (Stage 5 rule 2)
            if status in NON_RETRYABLE_STATUSES:
                raise FetchError(
                    f"HTTP {status} for {canonical_url} (non-retryable client status)",
                    status_code=status,
                    attempts=attempt,
                )

            # Retry on 5xx or 429
            if status in RETRYABLE_STATUSES and attempt <= max_retries:
                base_backoff = polite_delay * (2 ** (attempt - 1)) + random.uniform(0.05, 0.15)
                wait_seconds = parse_retry_after(response.headers.get("Retry-After"), base_backoff)
                stats["structured_logs"].append(
                    log_structured("retry_scheduled", url=canonical_url, status=status, attempt=attempt, wait_s=round(wait_seconds, 3))
                )
                if wait_seconds > 0:
                    time.sleep(wait_seconds)
                continue

            raise FetchError(f"HTTP {status} for {canonical_url}", status_code=status, attempts=attempt)

        except (requests.Timeout, requests.ConnectionError) as exc:
            stats["structured_logs"].append(
                log_structured("network_error", url=canonical_url, status=None, attempt=attempt, error=str(exc))
            )
            if attempt <= max_retries:
                wait_seconds = polite_delay * (2 ** (attempt - 1)) + random.uniform(0.05, 0.15)
                if wait_seconds > 0:
                    time.sleep(wait_seconds)
                continue
            raise FetchError(f"Timeout/connection failure for {canonical_url}: {exc}", status_code=None, attempts=attempt) from exc

    raise FetchError(f"Exhausted retries for {canonical_url}", status_code=None, attempts=max_retries + 1)


# ---------------------------------------------------------------------------
# Stage 2: Discover Three Catalogue Pages
# ---------------------------------------------------------------------------
def discover_catalogue(
    stats: dict[str, Any],
    cache_dir: Path = CACHE_DIR,
    max_pages: int = MAX_CATALOGUE_PAGES,
    session: Optional[requests.Session] = None,
    use_cache: bool = True,
    polite_delay: float = POLITE_DELAY_SECONDS,
) -> list[tuple[str, str]]:
    current_url = f"{CANONICAL_BASE_URL}/catalogue/page-1.html"
    pages_count = 0
    discovered_pairs: list[tuple[str, str]] = []

    while current_url and pages_count < max_pages:
        pages_count += 1
        c_path = cache_dir / f"catalogue-page-{pages_count}.html"
        html_text, _, _ = fetch_html(
            current_url,
            c_path,
            stats=stats,
            session=session,
            use_cache=use_cache,
            polite_delay=polite_delay,
        )
        soup = BeautifulSoup(html_text, "html.parser")

        for a_tag in soup.select("article.product_pod h3 a"):
            href = a_tag.get("href", "")
            if href:
                abs_book_url = resolve_book_url(current_url, href)
                discovered_pairs.append((abs_book_url, current_url))

        next_tag = soup.select_one("li.next a")
        if next_tag and next_tag.get("href") and pages_count < max_pages:
            current_url = resolve_book_url(current_url, next_tag["href"])
        else:
            current_url = ""

    unique_pairs = deduplicate_urls(discovered_pairs)
    stats["catalogue_pages"] = pages_count
    stats["discovered_urls"] = len(discovered_pairs)
    stats["unique_urls"] = len(unique_pairs)
    print(f"catalogue_pages={pages_count}, discovered={len(discovered_pairs)}, unique_urls={len(unique_pairs)}")
    return unique_pairs


# ---------------------------------------------------------------------------
# Stage 3: Extract Raw Record from Book Detail HTML
# ---------------------------------------------------------------------------
def extract_raw_record(
    html_text: str,
    product_url: str,
    source_page: str,
    fetched_at: str,
) -> dict[str, Any]:
    """
    Parse book detail HTML aiming selectors strictly at article.product_page.
    Store None when description is missing — never invent text.
    """
    soup = BeautifulSoup(html_text, "html.parser")
    product_area = soup.select_one("article.product_page")
    if product_area is None:
        raise ValueError(f"Missing article.product_page container in {product_url}")

    product_main = product_area.select_one("div.product_main")
    if product_main is None:
        raise ValueError(f"Missing div.product_main container in {product_url}")

    title_el = product_main.select_one("h1")
    price_el = product_main.select_one("p.price_color")
    avail_el = product_main.select_one("p.availability")
    rating_el = product_main.select_one("p.star-rating")

    title = re.sub(r"\s+", " ", title_el.get_text(strip=True)) if title_el else ""
    price_text = re.sub(r"\s+", "", price_el.get_text(strip=True)) if price_el else ""
    availability_text = re.sub(r"\s+", " ", avail_el.get_text(strip=True)) if avail_el else ""

    rating_text = ""
    if rating_el:
        for cls in rating_el.get("class", []):
            if cls in RATING_WORDS:
                rating_text = cls
                break

    desc_el = product_area.select_one("#product_description + p")
    description: Optional[str] = None
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


# ---------------------------------------------------------------------------
# Stage 4: Normalize, Validate, and Deduplicate
# ---------------------------------------------------------------------------
def normalize_and_validate_record(raw_record: dict[str, Any]) -> BookRecord:
    """Normalize price_text -> price_gbp and validate with Pydantic."""
    price_gbp = normalize_price(raw_record.get("price_text", ""))
    candidate = {
        **raw_record,
        "price_gbp": price_gbp,
    }
    return BookRecord(**candidate)


# ---------------------------------------------------------------------------
# Extras: Change Detection, CSV Export, and Local HTML Dashboard
# ---------------------------------------------------------------------------
def compute_record_hash(record: dict[str, Any]) -> str:
    """Hash canonical content fields (excluding volatile fetched_at) to detect changes."""
    stable_payload = {
        "title": record["title"],
        "product_url": record["product_url"],
        "price_text": record["price_text"],
        "price_gbp": record["price_gbp"],
        "availability_text": record["availability_text"],
        "rating_text": record["rating_text"],
        "description": record["description"],
        "source_page": record["source_page"],
    }
    canonical_json = json.dumps(stable_payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def update_change_detection(records: list[dict[str, Any]], output_dir: Path) -> dict[str, int]:
    """Compare current validated records against previous run hashes."""
    hash_file = output_dir / "record-hashes.json"
    previous_hashes: dict[str, str] = {}
    if hash_file.exists():
        try:
            previous_hashes = json.loads(hash_file.read_text(encoding="utf-8"))
        except Exception:
            previous_hashes = {}

    current_hashes: dict[str, str] = {
        r["product_url"]: compute_record_hash(r) for r in records
    }

    new_count = 0
    changed_count = 0
    unchanged_count = 0
    for url, digest in current_hashes.items():
        if url not in previous_hashes:
            new_count += 1
        elif previous_hashes[url] != digest:
            changed_count += 1
        else:
            unchanged_count += 1

    gone_count = sum(1 for url in previous_hashes if url not in current_hashes)
    hash_file.write_text(json.dumps(current_hashes, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "new": new_count,
        "changed": changed_count,
        "unchanged": unchanged_count,
        "gone": gone_count,
    }


def export_books_csv(records: list[dict[str, Any]], csv_path: Path) -> None:
    """
    Export validated book records to CSV.
    Flattening notes:
    - Optional `description` (None in Python / null in JSON) is flattened to an empty string "".
    - Embedded newlines or tabs in `description` and `title` are collapsed to single spaces.
    """
    fieldnames = [
        "title",
        "product_url",
        "price_text",
        "price_gbp",
        "availability_text",
        "rating_text",
        "description",
        "source_page",
        "fetched_at",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            flat_row = {
                **r,
                "description": "" if r.get("description") is None else re.sub(r"\s+", " ", str(r["description"])),
            }
            writer.writerow(flat_row)


def generate_dashboard_html(records: list[dict[str, Any]], report: dict[str, Any], html_path: Path) -> None:
    """Generate a local observability HTML dashboard summarizing the run."""
    prices = [r["price_gbp"] for r in records] if records else [0.0]
    min_price = min(prices)
    max_price = max(prices)
    avg_price = round(sum(prices) / len(prices), 2)

    rows_html = []
    for idx, r in enumerate(records[:15], start=1):
        desc_preview = r["description"][:80] + "..." if r.get("description") else "<em>null (missing description)</em>"
        rows_html.append(
            f"<tr>"
            f"<td>{idx}</td>"
            f"<td><a href='{html.escape(r['product_url'])}'>{html.escape(r['title'])}</a></td>"
            f"<td>£{r['price_gbp']:.2f}</td>"
            f"<td>{html.escape(r['rating_text'])}</td>"
            f"<td>{html.escape(r['availability_text'])}</td>"
            f"<td>{desc_preview}</td>"
            f"</tr>"
        )

    dashboard = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>The Polite Scraper — Observability Dashboard</title>
  <style>
    body {{ font-family: system-ui, -apple-system, sans-serif; margin: 2rem auto; max-width: 1100px; color: #1e293b; background: #f8fafc; padding: 0 1rem; }}
    h1 {{ color: #0f172a; margin-bottom: 0.25rem; }}
    .subtitle {{ color: #475569; margin-bottom: 1.5rem; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem; }}
    .card {{ background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1rem 1.25rem; box-shadow: 0 1px 2px rgba(0,0,0,0.04); }}
    .card-label {{ font-size: 0.85rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.04em; }}
    .card-value {{ font-size: 1.6rem; font-weight: 700; color: #0f172a; margin-top: 0.25rem; }}
    table {{ width: 100%; border-collapse: collapse; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; }}
    th, td {{ padding: 0.65rem 0.85rem; text-align: left; border-bottom: 1px solid #f1f5f9; font-size: 0.9rem; }}
    th {{ background: #f1f5f9; font-weight: 600; color: #334155; }}
  </style>
</head>
<body>
  <h1>The Polite Scraper — Run Observability Dashboard</h1>
  <p class="subtitle">Last fresh run: <strong>{html.escape(report['end_time'])}</strong> · Duration: <strong>{report['duration_seconds']}s</strong> · User-Agent: <code>{html.escape(USER_AGENT)}</code></p>
  <div class="cards">
    <div class="card">
      <div class="card-label">Validated Records</div>
      <div class="card-value">{report['valid_records']}</div>
    </div>
    <div class="card">
      <div class="card-label">Price Range (GBP)</div>
      <div class="card-value">£{min_price:.2f} – £{max_price:.2f}</div>
    </div>
    <div class="card">
      <div class="card-label">Mean Price (GBP)</div>
      <div class="card-value">£{avg_price:.2f}</div>
    </div>
    <div class="card">
      <div class="card-label">Cache Hits / Fetched</div>
      <div class="card-value">{report['cache_hits']} / {report['pages_fetched']}</div>
    </div>
    <div class="card">
      <div class="card-label">Failed Pages / Errors</div>
      <div class="card-value">{report['failed_pages']} / {report['invalid_records']}</div>
    </div>
  </div>
  <h2>Sample Validated Records (First 15 of {len(records)})</h2>
  <table>
    <thead>
      <tr><th>#</th><th>Title</th><th>Price (GBP)</th><th>Rating</th><th>Availability</th><th>Description Preview</th></tr>
    </thead>
    <tbody>
      {''.join(rows_html)}
    </tbody>
  </table>
</body>
</html>
"""
    html_path.write_text(dashboard, encoding="utf-8")


# ---------------------------------------------------------------------------
# Full Pipeline Runner (Stages 1–5 + Extras)
# ---------------------------------------------------------------------------
def run_pipeline(
    cache_dir: Path = CACHE_DIR,
    output_dir: Path = OUTPUT_DIR,
    inject_broken_url: bool = True,
    use_cache: bool = True,
    polite_delay: float = POLITE_DELAY_SECONDS,
    session: Optional[requests.Session] = None,
) -> dict[str, Any]:
    start_dt = datetime.now(timezone.utc)
    start_perf = time.perf_counter()

    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    stats: dict[str, Any] = {
        "catalogue_pages": 0,
        "discovered_urls": 0,
        "unique_urls": 0,
        "pages_fetched": 0,
        "cache_hits": 0,
        "valid_records": 0,
        "invalid_records": 0,
        "failed_pages": 0,
        "failed_urls": [],
        "network_requests_sent": 0,
        "structured_logs": [],
    }

    # Stage 2: Discover the first 3 catalogue pages (60 unique book URLs)
    unique_book_pairs = discover_catalogue(
        stats=stats,
        cache_dir=cache_dir,
        max_pages=MAX_CATALOGUE_PAGES,
        session=session,
        use_cache=use_cache,
        polite_delay=polite_delay,
    )

    # Stage 5 Checkpoint: Add one deliberate fake book URL to prove one bad page never kills the run
    work_list = list(unique_book_pairs)
    if inject_broken_url:
        work_list.append((BROKEN_BOOK_URL, f"{CANONICAL_BASE_URL}/catalogue/page-3.html"))

    raw_records: list[dict[str, Any]] = []
    for book_url, source_page in work_list:
        c_path = book_cache_path(book_url, cache_dir=cache_dir)
        try:
            html_text, fetched_at, _ = fetch_html(
                book_url,
                c_path,
                stats=stats,
                session=session,
                use_cache=use_cache,
                polite_delay=polite_delay,
            )
            raw_rec = extract_raw_record(
                html_text=html_text,
                product_url=book_url,
                source_page=source_page,
                fetched_at=fetched_at,
            )
            raw_records.append(raw_rec)
        except FetchError as exc:
            stats["failed_pages"] += 1
            stats["failed_urls"].append({
                "url": book_url,
                "status_code": exc.status_code,
                "attempts": exc.attempts,
                "reason": str(exc),
            })
            print(f"SKIP BROKEN PAGE {book_url} -> {exc}")
        except Exception as exc:
            stats["failed_pages"] += 1
            stats["failed_urls"].append({
                "url": book_url,
                "status_code": None,
                "attempts": 1,
                "reason": str(exc),
            })
            print(f"SKIP PARSE ERROR {book_url} -> {exc}")

    # Stage 3 Checkpoint: Print one complete raw record and summary detail_pages=60
    if raw_records:
        print("Sample raw record:", json.dumps(raw_records[0], ensure_ascii=False))
    print(f"detail_pages={len(raw_records)}")

    # Stage 4: Normalize, validate against Pydantic schema, deduplicate by canonical product_url (idempotency)
    validated_by_url: dict[str, dict[str, Any]] = {}
    validation_errors: list[dict[str, Any]] = []

    for raw_rec in raw_records:
        try:
            valid_model = normalize_and_validate_record(raw_rec)
            clean_dict = valid_model.model_dump() if hasattr(valid_model, "model_dump") else valid_model.dict()
            # Canonical URL identity ensures idempotency (duplicates count once)
            validated_by_url[clean_dict["product_url"]] = clean_dict
        except (ValidationError, ValueError) as exc:
            stats["invalid_records"] += 1
            validation_errors.append({
                "product_url": raw_rec.get("product_url"),
                "raw_record": raw_rec,
                "reason": str(exc),
            })

    final_books = list(validated_by_url.values())
    stats["valid_records"] = len(final_books)

    books_path = output_dir / "books.json"
    errors_path = output_dir / "errors.json"
    report_path = output_dir / "run-report.json"
    csv_path = output_dir / "books.csv"
    dashboard_path = output_dir / "dashboard.html"

    books_path.write_text(json.dumps(final_books, indent=2, ensure_ascii=False), encoding="utf-8")
    errors_path.write_text(json.dumps(validation_errors, indent=2, ensure_ascii=False), encoding="utf-8")

    # Extras: change detection, CSV export, HTML dashboard
    change_summary = update_change_detection(final_books, output_dir=output_dir)
    export_books_csv(final_books, csv_path=csv_path)

    end_dt = datetime.now(timezone.utc)
    duration_seconds = round(time.perf_counter() - start_perf, 3)

    run_report = {
        "start_time": start_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end_time": end_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "duration_seconds": duration_seconds,
        "user_agent": USER_AGENT,
        "catalogue_pages": stats["catalogue_pages"],
        "discovered_urls": stats["discovered_urls"],
        "unique_urls": stats["unique_urls"],
        "pages_fetched": stats["pages_fetched"],
        "cache_hits": stats["cache_hits"],
        "valid_records": stats["valid_records"],
        "invalid_records": stats["invalid_records"],
        "failed_pages": stats["failed_pages"],
        "failed_urls": stats["failed_urls"],
        "change_detection": change_summary,
    }
    report_path.write_text(json.dumps(run_report, indent=2, ensure_ascii=False), encoding="utf-8")
    generate_dashboard_html(final_books, run_report, html_path=dashboard_path)

    print(
        f"Run complete: valid_records={run_report['valid_records']}, "
        f"invalid_records={run_report['invalid_records']}, "
        f"failed_pages={run_report['failed_pages']}, "
        f"pages_fetched={run_report['pages_fetched']}, "
        f"cache_hits={run_report['cache_hits']}"
    )
    return run_report


def main() -> None:
    parser = argparse.ArgumentParser(description="The Polite Scraper (FlyRank W5 · A9)")
    parser.add_argument(
        "--no-broken-url",
        action="store_true",
        help="Disable the deliberate Stage 5 broken book URL test injection.",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Bypass reading from cache/ and force fresh network fetches.",
    )
    parser.add_argument(
        "--check-robots",
        action="store_true",
        help="Run Stage 0 robots.txt check and print result.",
    )
    args = parser.parse_args()

    if args.check_robots:
        res = check_robots_txt()
        print(json.dumps(res, indent=2))
        return

    run_pipeline(
        inject_broken_url=not args.no_broken_url,
        use_cache=not args.no_cache,
    )


if __name__ == "__main__":
    main()
