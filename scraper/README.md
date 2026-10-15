# The Polite Scraper — FlyRank Backend Track (Week 5 · Assignment A9)

A polite, deterministic web-scraping pipeline built in the **Python lane** (`Python 3.10+`, `requests`, `BeautifulSoup`, and `Pydantic`).

## Target Classification (Stage 0)

- **Target Site**: [Books to Scrape](https://books.toscrape.com) (verified via the [ToScrape Sandbox Directory](https://toscrape.com))
- **Why This Site**: Books to Scrape explicitly states on [toscrape.com](https://toscrape.com) that it is *"a safe place for beginners learning web scraping and for developers validating their scraping technologies as well"*, and its banner reads *"Books to Scrape — We love being scraped!"*.
- **Scope**: Strictly the **first 3 catalogue pages only** (`page-1.html`, `page-2.html`, and `page-3.html`), comprising **60 book detail pages** out of the 1,000 books in the sandbox.
- **Data Collected**: Public bibliographic catalogue fields only (`title`, `product_url`, `price_text`, `price_gbp`, `availability_text`, `rating_text`, `description`, `source_page`, and `fetched_at`). No personal data, user accounts, or private endpoints exist or are accessed.
- **Why This Scope Is Appropriate**: Collecting 60 static catalogue records with local HTML caching and a 500 ms delay between requests proves multi-page discovery, extraction, normalisation, schema validation, and failure recovery without placing load on the sandbox server.
- **`robots.txt` Check Result**: Requesting `https://books.toscrape.com/robots.txt` returns `HTTP 404 Not Found` (**no robots file found** — a missing file is not permission, it is just a missing file; explicit permission comes from the sandbox notice on [toscrape.com](https://toscrape.com)).

> **Commitment**: I will not reuse this code on another site without checking its rules and terms first.
