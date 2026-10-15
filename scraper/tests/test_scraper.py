#!/usr/bin/env python3
"""
Unit test suite for The Polite Scraper (FlyRank Week 5 · Assignment A9).
Executable directly via `python3 tests/test_scraper.py` or `python3 -m unittest discover -s tests -v`.

Covers:
1. Price normalisation (£51.77 -> 51.77, rejecting malformed strings)
2. Relative -> absolute URL resolution via urljoin
3. Missing description fixture handling (returns None, never invents text)
4. Extra whitespace fixture normalisation
5. Duplicate URL deduplication and idempotency
6. Malformed fixture schema rejection (routes to errors.json)
7. Retry-After header parsing & SHA-256 record change detection
"""

import sys
import unittest
from pathlib import Path
from pydantic import ValidationError

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

from main import (
    compute_record_hash,
    deduplicate_urls,
    extract_raw_record,
    normalize_and_validate_record,
    normalize_price,
    parse_retry_after,
    resolve_book_url,
)

FIXTURES_DIR = BASE_DIR / "fixtures"


class PoliteScraperTestSuite(unittest.TestCase):
    def test_01_price_normalization(self):
        """Test 1: Turn raw GBP strings into numeric floats and reject invalid values."""
        self.assertEqual(normalize_price("£51.77"), 51.77)
        self.assertEqual(normalize_price("  £12.84  "), 12.84)
        self.assertEqual(normalize_price("Â£35.02"), 35.02)
        with self.assertRaises(ValueError):
            normalize_price("FREE")
        with self.assertRaises(ValueError):
            normalize_price("$51.77")
        with self.assertRaises(ValueError):
            normalize_price("")

    def test_02_relative_to_absolute_urls(self):
        """Test 2: Resolve catalogue-relative book links into canonical https:// URLs."""
        page_1 = "https://books.toscrape.com/catalogue/page-1.html"
        self.assertEqual(
            resolve_book_url(page_1, "a-light-in-the-attic_1000/index.html"),
            "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
        )
        self.assertEqual(
            resolve_book_url(page_1, "../catalogue/tipping-the-velvet_999/index.html"),
            "https://books.toscrape.com/catalogue/tipping-the-velvet_999/index.html",
        )

    def test_03_missing_description_fixture(self):
        """Test 3: Prove parser stores None when a book page has no #product_description."""
        html_text = (FIXTURES_DIR / "missing_description.html").read_text(encoding="utf-8")
        raw = extract_raw_record(
            html_text=html_text,
            product_url="https://books.toscrape.com/catalogue/the-torch-is-passed-a-harding-family-story_945/index.html",
            source_page="https://books.toscrape.com/catalogue/page-3.html",
            fetched_at="2026-10-15T12:00:00Z",
        )
        self.assertEqual(raw["title"], "The Torch Is Passed: A Harding Family Story")
        self.assertIsNone(raw["description"])
        self.assertEqual(
            set(raw.keys()),
            {
                "title",
                "product_url",
                "price_text",
                "availability_text",
                "rating_text",
                "description",
                "source_page",
                "fetched_at",
            },
        )
        validated = normalize_and_validate_record(raw)
        self.assertIsNone(validated.description)
        self.assertEqual(validated.price_gbp, 19.09)

    def test_04_extra_whitespace_fixture(self):
        """Test 4: Prove parser collapses multiline whitespace in title, availability, and description."""
        html_text = (FIXTURES_DIR / "extra_whitespace.html").read_text(encoding="utf-8")
        raw = extract_raw_record(
            html_text=html_text,
            product_url="https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
            source_page="https://books.toscrape.com/catalogue/page-1.html",
            fetched_at="2026-10-15T12:00:00Z",
        )
        self.assertEqual(raw["title"], "A Light in the Attic")
        self.assertEqual(raw["price_text"], "£51.77")
        self.assertEqual(raw["availability_text"], "In stock (22 available)")
        self.assertEqual(raw["rating_text"], "Three")
        self.assertEqual(raw["description"], "It's hard to imagine a world without A Light in the Attic.")

    def test_05_duplicate_urls_deduplication(self):
        """Test 5: Remove duplicate URLs while preserving discovery order and first source_page."""
        pairs = [
            ("https://books.toscrape.com/catalogue/book-1/index.html", "https://books.toscrape.com/catalogue/page-1.html"),
            ("https://books.toscrape.com/catalogue/book-2/index.html", "https://books.toscrape.com/catalogue/page-1.html"),
            ("https://books.toscrape.com/catalogue/book-1/index.html", "https://books.toscrape.com/catalogue/page-2.html"),
        ]
        deduped = deduplicate_urls(pairs)
        self.assertEqual(len(deduped), 2)
        self.assertEqual(deduped[0][0], "https://books.toscrape.com/catalogue/book-1/index.html")
        self.assertEqual(deduped[0][1], "https://books.toscrape.com/catalogue/page-1.html")

    def test_06_malformed_fixture_rejected_by_schema(self):
        """Test 6: Malformed HTML fixture fails validation so it routes to errors.json instead of books.json."""
        html_text = (FIXTURES_DIR / "malformed_price.html").read_text(encoding="utf-8")
        raw = extract_raw_record(
            html_text=html_text,
            product_url="https://books.toscrape.com/catalogue/corrupted_001/index.html",
            source_page="https://books.toscrape.com/catalogue/page-1.html",
            fetched_at="2026-10-15T12:00:00Z",
        )
        with self.assertRaises((ValueError, ValidationError)):
            normalize_and_validate_record(raw)

    def test_07_retry_after_and_hash_stability(self):
        """Test 7: Verify Retry-After header parsing and deterministic SHA-256 record hashing."""
        self.assertEqual(parse_retry_after("2.5", fallback_delay=0.5), 2.5)
        self.assertEqual(parse_retry_after("invalid", fallback_delay=0.75), 0.75)

        rec_a = {
            "title": "A Light in the Attic",
            "product_url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
            "price_text": "£51.77",
            "price_gbp": 51.77,
            "availability_text": "In stock (22 available)",
            "rating_text": "Three",
            "description": "Classic poetry.",
            "source_page": "https://books.toscrape.com/catalogue/page-1.html",
            "fetched_at": "2026-10-15T10:00:00Z",
        }
        rec_b = {**rec_a, "fetched_at": "2026-10-15T11:30:00Z"}
        self.assertEqual(compute_record_hash(rec_a), compute_record_hash(rec_b))


if __name__ == "__main__":
    unittest.main(verbosity=2)
