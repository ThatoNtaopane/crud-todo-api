# Bonus Stage — AI vs Me Engineering Review

## 1. Summary of Comparison
We wrote our specification from memory (`prompt_v1.txt`), generated `ai_scraper_v1.py` in isolation, tested it against our 60-book + 1-broken-URL checkpoints, identified three concrete differences, and ran a single rematch (`prompt_v2.txt` -> `ai_scraper_v2.py`).

## 2. Three Concrete Differences Between Hand-Built and AI v1
1. **Adjacent Sibling Selector (`#product_description + p`) vs Generic Paragraph Lookup**:
   - Our hand-built extractor explicitly targets `#product_description + p` inside `article.product_page` and normalises empty strings to `None`.
   - `ai_scraper_v1.py` used a looser selector and raw `.get_text(strip=True)` without collapsing internal newlines in `availability_text`.
2. **HTTP 404 / 403 Non-Retry Discipline**:
   - Our hand-built `fetch_html()` checks `status in {400, 401, 403, 404, 410}` and raises `FetchError` on attempt 1 without retrying.
   - `ai_scraper_v1.py` wrapped `requests.get()` in a blanket loop that retried any `status != 200`, causing it to hit a 404 URL multiple times.
3. **Whitespace Normalisation on `availability_text`**:
   - On Books to Scrape, `<p class="instock availability">` contains embedded newlines and indentation around `<i class="icon-ok"></i>`. Our hand-built parser collapses internal whitespace with `re.sub(r"\s+", " ", ...)` to produce `"In stock (22 available)"`, whereas `ai_scraper_v1.py` left multiline whitespace inside `availability_text`.
