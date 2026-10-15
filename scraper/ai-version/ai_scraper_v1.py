#!/usr/bin/env python3
"""
AI Version 1 (Quarantined in ai-version/ai_scraper_v1.py)
Demonstrates two classic AI defects discovered during engineering review:
1. Over-broad selector `article.product_page > p` instead of `#product_description + p`.
2. Retrying all non-200 status codes including HTTP 404 Not Found.
"""

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel

USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/ThatoNtaopane/crud-todo-api)"


@dataclass
class RunMetrics:
    pages_fetched: int = 0
    cache_hits: int = 0
    valid_records: int = 0
    invalid_records: int = 0
    failed_pages: int = 0


class AIBookSchemaV1(BaseModel):
    title: str
    product_url: str
    price_text: str
    price_gbp: float
    availability_text: str
    rating_text: str
    description: Optional[str] = None
    source_page: str
    fetched_at: str


def extract_v1_flawed(html_text: str, product_url: str, source_page: str, fetched_at: str) -> dict:
    soup = BeautifulSoup(html_text, "html.parser")
    article = soup.select_one("article.product_page")
    # Defect 1: `article.select_one("p")` matches `<p class="price_color">` if not scoped to `#product_description + p`
    desc_el = article.select_one("#product_description ~ p") if article else None
    return {
        "title": article.select_one("h1").get_text(strip=True),
        "product_url": product_url,
        "price_text": article.select_one("p.price_color").get_text(strip=True),
        "availability_text": article.select_one("p.availability").get_text(strip=True),
        "rating_text": article.select_one("p.star-rating")["class"][1],
        "description": desc_el.get_text(strip=True) if desc_el else None,
        "source_page": source_page,
        "fetched_at": fetched_at,
    }
