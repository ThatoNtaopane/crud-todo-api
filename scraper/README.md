# The Polite Scraper — FlyRank Backend Track · Week 5 · Assignment A9

A deterministic, fault-tolerant, and polite web-scraping pipeline built in the **Python lane** (`Python 3.10+`, `requests`, `BeautifulSoup`, and `Pydantic`). It downloads the first three catalogue pages of [Books to Scrape](https://books.toscrape.com), visits all 60 book detail pages, normalises and validates every record against a strict schema, survives broken pages without crashing, and writes a transparent run report at the end of every execution.

---

## 1. Target Classification & `robots.txt` Check (Stage 0)

- **Target Site**: [Books to Scrape](https://books.toscrape.com) (verified via the [ToScrape Web Scraping Sandbox](https://toscrape.com))
- **Why This Site Is Permitted**: The [ToScrape Sandbox Directory](https://toscrape.com) explicitly states that Books to Scrape is *"a fictional bookstore that desperately wants to be scraped. It's a safe place for beginners learning web scraping and for developers validating their scraping technologies as well"*, and the site header declares *"Books to Scrape — We love being scraped!"*.
- **Scope**: Strictly the **first 3 catalogue pages only** (`page-1.html`, `page-2.html`, and `page-3.html`), discovering and visiting **60 unique book detail pages** out of the 1,000 books hosted on the sandbox.
- **Data Collected**: Public catalogue metadata only (`title`, `product_url`, `price_text`, `price_gbp`, `availability_text`, `rating_text`, `description`, `source_page`, and `fetched_at`).
- **Why This Scope Is Appropriate**: Limiting collection to 60 static book pages with local disk caching and a 500 ms delay between requests validates pagination, extraction, normalisation, schema validation, and error recovery without placing unnecessary load on the practice server.
- **`robots.txt` Check Result**: Requesting `https://books.toscrape.com/robots.txt` returns `HTTP 404 Not Found` (**no robots file found** — a missing file is not permission, it is just a missing file; explicit permission is granted by the sandbox notice on [toscrape.com](https://toscrape.com)).

> **Commitment**: I will not reuse this code on another site without checking its rules and terms first.

---

## 2. Quickstart — Clone & Run in Under 5 Minutes

### Lane & Prerequisites

- **Lane**: Python lane (`Python 3.10+`)
- **HTTP Client**: `requests`
- **HTML Parser**: `beautifulsoup4` (`BeautifulSoup`)
- **Schema Validator**: `pydantic` (`BaseModel`)
- **Output Serialiser**: Python built-in `json` and `csv` modules

### One Copy-Pasteable Command to Run

```bash
git clone https://github.com/ThatoNtaopane/crud-todo-api.git && cd crud-todo-api/scraper && pip install -r requirements.txt && python3 src/main.py
```

### Additional Commands

```bash
# Run a second time to verify CACHE HIT behaviour and idempotent 60-record output
python3 src/main.py

# Run without the deliberate Stage 5 broken URL injection (0 failed pages)
python3 src/main.py --no-broken-url

# Run Stage 0 robots.txt check
python3 src/main.py --check-robots

# Run the automated unit test suite (7 parser, schema, URL, and fixture tests)
python3 tests/test_scraper.py
```

---

## 3. Politeness Rules Followed

1. **Honest Identifying `User-Agent`**: Every HTTP request sends `User-Agent: FlyRankInternship-A9/1.0 (+https://github.com/ThatoNtaopane/crud-todo-api)` so server administrators can identify the bot and repository immediately.
2. **Explicit Request Timeout**: Every request sets `timeout=10` seconds so a stalled connection never hangs the pipeline indefinitely.
3. **Strict Status Code Check**: Every response verifies `status_code == 200` before parsing HTML. Non-200 responses are treated as failed fetches, never as HTML to parse.
4. **Polite Rate Limiting (`>= 500 ms`)**: The scraper waits at least `0.5` seconds (`time.sleep(0.5)`) between consecutive network requests. Cached pages require zero delay because they never leave the local machine.
5. **Read-Through Local HTML Cache (`cache/`)**: Every fetched catalogue page (`cache/catalogue-page-1.html` .. `3.html`) and book detail page (`cache/books/<slug>.html`) is saved locally on the first fetch and read from disk on subsequent runs. The `cache/` directory is listed in `.gitignore` so cached HTML is never committed to Git.
6. **Smart Retry & Backoff Rules**: Transient failures (`requests.Timeout`, `requests.ConnectionError`, `429 Too Many Requests`, and `5xx` server errors) are retried with exponential backoff, random jitter, and `Retry-After` header support. Permanent client errors (`404 Not Found` and `403 Forbidden`) are **never** retried.

---

## 4. Record Schema (`BookRecord`)

Every extracted book record is normalised (`price_text` `"£51.77"` -> `price_gbp` `51.77`) and validated through our Pydantic `BookRecord` schema before storage. Any record that fails validation is written to `output/errors.json` with its failure reason and excluded from `output/books.json`.

| Field | Type | Required | Validation Rule & Description |
| :--- | :--- | :--- | :--- |
| `title` | `str` | Yes | Non-empty book title extracted from `article.product_page div.product_main h1` |
| `product_url` | `str` | Yes | Canonical absolute URL starting with `https://`; serves as the deduplication key |
| `price_text` | `str` | Yes | Raw price string preserved verbatim from the page (e.g., `"£51.77"`) |
| `price_gbp` | `float` | Yes | Numeric GBP value (`> 0`, e.g., `51.77`) for sorting and comparison |
| `availability_text` | `str` | Yes | Cleaned stock status text (e.g., `"In stock (22 available)"`) |
| `rating_text` | `Literal["One", "Two", "Three", "Four", "Five"]` | Yes | Star rating word extracted from `p.star-rating` CSS class |
| `description` | `Optional[str]` | No (`null` allowed) | Product description text, or `null` when absent (e.g., *The Torch Is Passed*) |
| `source_page` | `str` | Yes | Provenance URL of the catalogue page where the book link was discovered (`https://...`) |
| `fetched_at` | `str` | Yes | Provenance ISO-8601 UTC timestamp (`YYYY-MM-DDTHH:MM:SSZ`) |

---

## 5. Run Report Evidence (`output/run-report.json`)

### First Run (Fresh Network Fetch + 1 Deliberate Broken URL)

```json
{
  "start_time": "2026-10-15T12:45:18Z",
  "end_time": "2026-10-15T12:45:54Z",
  "duration_seconds": 35.91,
  "user_agent": "FlyRankInternship-A9/1.0 (+https://github.com/ThatoNtaopane/crud-todo-api)",
  "catalogue_pages": 3,
  "discovered_urls": 60,
  "unique_urls": 60,
  "pages_fetched": 63,
  "cache_hits": 0,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 1,
  "failed_urls": [
    {
      "url": "https://books.toscrape.com/catalogue/broken-book-page-404_000/index.html",
      "status_code": 404,
      "attempts": 1,
      "reason": "HTTP 404 for https://books.toscrape.com/catalogue/broken-book-page-404_000/index.html (non-retryable client status)"
    }
  ],
  "change_detection": {
    "new": 60,
    "changed": 0,
    "unchanged": 0,
    "gone": 0
  }
}
```

### Second Run (From Local Cache — Proving Idempotency & Change Detection)

```json
{
  "start_time": "2026-10-15T12:45:55Z",
  "end_time": "2026-10-15T12:45:55Z",
  "duration_seconds": 0.554,
  "user_agent": "FlyRankInternship-A9/1.0 (+https://github.com/ThatoNtaopane/crud-todo-api)",
  "catalogue_pages": 3,
  "discovered_urls": 60,
  "unique_urls": 60,
  "pages_fetched": 0,
  "cache_hits": 63,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 1,
  "failed_urls": [
    {
      "url": "https://books.toscrape.com/catalogue/broken-book-page-404_000/index.html",
      "status_code": 404,
      "attempts": 1,
      "reason": "HTTP 404 for https://books.toscrape.com/catalogue/broken-book-page-404_000/index.html (non-retryable client status)"
    }
  ],
  "change_detection": {
    "new": 0,
    "changed": 0,
    "unchanged": 60,
    "gone": 0
  }
}
```

---

## 6. Why This Assignment Needed No Browser (+ Stretch Browser Cost Comparison)

**Why no browser was needed**: The data is already in the HTML the server sends, so a browser would only add cost.

### Stretch Goal: Browser Cost Comparison (`quotes.toscrape.com/js`)

To quantify the exact engineering cost of running a headless browser versus a plain HTTP client, `src/browser_comparison.py` compares fetching `https://quotes.toscrape.com/js/` using `requests` versus Headless Chromium (`Playwright`):

| Metric | Plain HTTP (`requests` + `BeautifulSoup`) | Headless Browser (`Playwright` Chromium) | Cost Multiplier |
| :--- | :--- | :--- | :--- |
| **Wall-Clock Time (1 Page)** | `142.4 ms` | `1,848.7 ms` | **13.0x slower** |
| **Peak Memory (RSS)** | `18.2 MB` | `196.5 MB` | **10.8x more RAM** |
| **Quotes Found on `/js/`** | `0` (quotes live inside a `<script>` JS variable) | `10` (JS executed & DOM populated) | Browser required only for client-rendered JS |
| **Books Found on `books.toscrape.com`** | `20 per page` (all HTML is server-rendered) | `20 per page` | **Zero data gain from browser** |

---

## 7. Honest Limitation

One honest limitation of this pipeline is that the file-based HTML cache (`cache/`) has no automatic time-to-live (TTL) expiry or `ETag` / `If-Modified-Since` conditional revalidation header check: once a page is cached on disk, subsequent runs always read the cached file until the user deletes `cache/` or passes `--no-cache`.

---

## 8. Scraping Ethics Note

Responsible data collection treats every remote server as someone else's property and infrastructure:
- **Use an official API first**: Whenever a service provides a documented public API or data export, use that API instead of scraping HTML.
- **Never bypass access controls**: Never circumvent logins, paywalls, rate-limit blocks, or CAPTCHAs; a `403 Forbidden` means stop immediately.
- **Minimise footprint and scope**: Identify your scraper honestly via `User-Agent`, obey `robots.txt` and `Retry-After` headers, pace requests politely, cache aggressively during development, and collect only the minimum public fields required for your task.

---

## 9. Optional Extras Included

1. **CSV Export (`output/books.csv`)**: Produces a clean 60-row CSV alongside `output/books.json`.
   - *Flattening note*: Optional `description` values that are `null` (`None`) in JSON are flattened to empty strings `""` in CSV, and any embedded whitespace/newlines are collapsed to single spaces so every book record occupies exactly one CSV line.
2. **Changed Since Last Run (`output/record-hashes.json`)**: Computes a deterministic SHA-256 hash of each record's canonical content fields (excluding `fetched_at`) and reports `new`, `changed`, `unchanged`, and `gone` counts in `output/run-report.json`.
3. **Tiny Observability Dashboard (`output/dashboard.html`)**: Generates a local static HTML dashboard displaying validated record count (`60`), GBP price range (`£12.84 – £57.31`, mean `£35.00`), cache hit ratio, failed pages, and a sample table of scraped books.
4. **Selector Fixtures & Unit Tests (`fixtures/` & `tests/test_scraper.py`)**: Includes three offline HTML fixtures (`missing_description.html`, `extra_whitespace.html`, and `malformed_price.html`) and 7 unit tests verifying price normalisation, `urljoin` resolution, missing descriptions (`null`), extra whitespace cleanup, duplicate URL removal, schema rejection of malformed records, and `Retry-After` parsing.
5. **Retry Like a Pro**: Implements exponential backoff with random jitter, respects the HTTP `Retry-After` header, and records structured log events (`url`, `status`, `attempt`, `event`).

---

## 10. Bonus Stage — The AI Rematch (`AI vs me`)

All AI-generated artefacts are isolated inside `scraper/ai-version/` so the hand-built pipeline in `scraper/src/` remains untouched.

### Prompt v1 (`ai-version/prompt_v1.txt`)

> Build a polite Python 3.10+ web scraper using `requests`, `BeautifulSoup`, and `Pydantic` targeting `https://books.toscrape.com`. Crawl the first 3 catalogue pages (`page-1.html` to `page-3.html`), resolve relative book links to absolute URLs, and visit all 60 book detail pages. Send User-Agent `FlyRankInternship-A9/1.0 (+https://github.com/ThatoNtaopane/crud-todo-api)`, use a 10-second timeout, wait 500 ms between network requests, and cache HTML files under `cache/`. Extract 8 raw fields (`title`, `product_url`, `price_text`, `availability_text`, `rating_text`, `description`, `source_page`, `fetched_at`), normalise `price_text` into float `price_gbp`, validate with Pydantic (`description` optional), deduplicate by `product_url`, write valid records to `output/books.json`, invalid records to `output/errors.json`, and a run summary to `output/run-report.json`. Ensure one broken book URL does not crash the run.

### Checkpoint Comparison: Hand-Built vs AI v1 vs AI v2 (Rematch)

| Checkpoint | Hand-Built (`src/main.py`) | AI Version 1 (`ai-version/ai_scraper_v1.py`) | AI Version 2 (`ai-version/ai_scraper_v2.py`) |
| :--- | :--- | :--- | :--- |
| Discovers 3 pages & 60 unique URLs | Pass (`60`) | Pass (`60`) | Pass (`60`) |
| Scopes selectors to `article.product_page` | Pass | **Fail** (used global `soup.find("p")` which grabbed stock text when description was missing) | Pass (fixed to `#product_description + p`) |
| Stores `null` on missing description | Pass (`None` -> `null`) | **Fail** (stored `"In stock (16 available)"` as description on book #945) | Pass (`None` -> `null`) |
| Idempotent rerun (`books.json` stays 60) | Pass (`60`) | Pass (`60`) | Pass (`60`) |
| Skips retry on `404` / `403` | Pass (1 attempt on 404) | **Fail** (retried 404 three times before skipping) | Pass (skips 404/403 immediately) |

### Engineering Diff Review (Three Questions)

1. **What did the AI do better — and do you understand that code?**
   - The AI used `urllib.parse.urlsplit` and ` pathlib.Path` concisely and wrapped run metrics in a `@dataclass`. Yes — the dataclass pattern is clean and easy to read because it groups counters (`pages_fetched`, `cache_hits`, `failed_pages`) with default values and serialises via `dataclasses.asdict()`.
2. **What did it get wrong or silently skip?**
   - In Version 1 (`ai_scraper_v1.py`), the AI wrote `soup.select_one("article.product_page > p")` to extract the book description. On book #945 (*The Torch Is Passed: A Harding Family Story*), which has no `#product_description` header, that selector silently matched the wrong `<p>` tag instead of returning `None`. Additionally, AI v1 retried `HTTP 404` responses instead of distinguishing permanent client errors (`404`/`403`) from transient server errors (`5xx`).
3. **What did your prompt forget to say (and what changed in the rematch)?**
   - My initial prompt (`prompt_v1.txt`) said *"extract `description` (optional)"* without specifying the exact DOM anchor (`#product_description + p`) or explicitly stating *"do not retry HTTP 404 or 403 responses"*. In the rematch prompt (`prompt_v2.txt`), I specified both constraints explicitly, and `ai_scraper_v2.py` passed all checkpoints cleanly.
