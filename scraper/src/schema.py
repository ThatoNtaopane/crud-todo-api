#!/usr/bin/env python3
"""
FlyRank Internship · Backend Track · Week 5 · Assignment A9
The Polite Scraper — Stage 4: Clean It, Check It, Store It
"""

import re
from typing import Literal, Optional
from pydantic import BaseModel, Field, validator


class BookRecord(BaseModel):
    """Pydantic schema validating every normalized book record before storage."""
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
    def must_be_https_url(cls, v: str) -> str:
        if not v.startswith("https://"):
            raise ValueError(f"URL must start with https://, got '{v}'")
        return v


def normalize_price(price_text: str) -> float:
    """Turn raw price_text (e.g. '£51.77') into numeric float 51.77."""
    if not price_text or not isinstance(price_text, str):
        raise ValueError(f"Invalid price_text: {price_text!r}")
    cleaned = price_text.strip()
    match = re.match(r"^£?\s*(\d+(?:\.\d{1,2})?)$", cleaned)
    if not match:
        raise ValueError(f"Cannot parse GBP price from {price_text!r}")
    value = float(match.group(1))
    if value <= 0:
        raise ValueError(f"Price must be positive, got {value}")
    return round(value, 2)
