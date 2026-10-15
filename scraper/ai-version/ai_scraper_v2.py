#!/usr/bin/env python3
"""
AI Version 2 — Rematch (Quarantined in ai-version/ai_scraper_v2.py)
Regenerated from prompt_v2.txt with explicit selector anchor (#product_description + p)
and explicit non-retry rule for HTTP 404 and 403 responses.
"""

import re
from typing import Literal, Optional
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

NON_RETRYABLE = {403, 404}


class AIBookSchemaV2(BaseModel):
    title: str = Field(..., min_length=1)
    product_url: str = Field(..., min_length=1)
    price_text: str = Field(..., min_length=2)
    price_gbp: float = Field(..., gt=0)
    availability_text: str = Field(..., min_length=1)
    rating_text: Literal["One", "Two", "Three", "Four", "Five"]
    description: Optional[str] = None
    source_page: str = Field(..., min_length=1)
    fetched_at: str = Field(..., min_length=10)


def extract_v2_fixed(html_text: str, product_url: str, source_page: str, fetched_at: str) -> dict:
    soup = BeautifulSoup(html_text, "html.parser")
    article = soup.select_one("article.product_page")
    main = article.select_one("div.product_main")
    desc_el = article.select_one("#product_description + p")
    description = re.sub(r"\s+", " ", desc_el.get_text(strip=True)) if desc_el else None
    return {
        "title": main.select_one("h1").get_text(strip=True),
        "product_url": product_url,
        "price_text": main.select_one("p.price_color").get_text(strip=True),
        "availability_text": re.sub(r"\s+", " ", main.select_one("p.availability").get_text(strip=True)),
        "rating_text": [c for c in main.select_one("p.star-rating")["class"] if c != "star-rating"][0],
        "description": description or None,
        "source_page": source_page,
        "fetched_at": fetched_at,
    }
