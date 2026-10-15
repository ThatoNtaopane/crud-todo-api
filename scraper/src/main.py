#!/usr/bin/env python3
"""
FlyRank Internship · Backend Track · Week 5 · Assignment A9
The Polite Scraper — Stage 0: Target Classification & robots.txt Check
"""

import requests

USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/ThatoNtaopane/crud-todo-api)"
ROBOTS_URL = "https://books.toscrape.com/robots.txt"
TIMEOUT_SECONDS = 10


def check_robots_txt(url: str = ROBOTS_URL) -> dict:
    """Request robots.txt once with an honest User-Agent and timeout."""
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=TIMEOUT_SECONDS)
    if response.status_code == 404:
        note = "no robots file found — a missing file is not permission, it is just a missing file."
    elif response.status_code == 200:
        note = response.text.strip()
    else:
        note = f"unexpected status {response.status_code}"
    return {
        "url": url,
        "status_code": response.status_code,
        "result": note,
    }


if __name__ == "__main__":
    print("Stage 0: Target classification configured. See README.md for details.")
