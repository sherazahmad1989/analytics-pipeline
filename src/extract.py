"""
extract.py
-----------
Pulls repository data from the GitHub public search API.
This is the "Extract" step of an ETL pipeline: pulling raw data
from a source system before any cleaning or transformation happens.
"""

import requests
import json
import time
from datetime import datetime, timezone
from pathlib import Path

GITHUB_API_URL = "https://api.github.com/search/repositories"
RAW_DATA_DIR = Path(__file__).parent.parent / "data" / "raw"


def fetch_repos(language: str = "python", min_stars: int = 1000, pages: int = 3) -> list[dict]:
    """
    Fetch repositories from GitHub matching a language and star threshold.
    Paginates through results since the API caps each response at 100 items.
    """
    all_repos = []
    headers = {"Accept": "application/vnd.github+json"}

    for page in range(1, pages + 1):
        params = {
            "q": f"language:{language} stars:>{min_stars}",
            "sort": "stars",
            "order": "desc",
            "per_page": 100,
            "page": page,
        }
        response = requests.get(GITHUB_API_URL, headers=headers, params=params, timeout=30)

        if response.status_code != 200:
            print(f"Request failed on page {page}: {response.status_code} - {response.text[:200]}")
            break

        payload = response.json()
        items = payload.get("items", [])
        if not items:
            break

        all_repos.extend(items)
        print(f"Page {page}: fetched {len(items)} repos (running total: {len(all_repos)})")

        # Be a good API citizen — GitHub rate limits unauthenticated requests
        time.sleep(1)

    return all_repos


def save_raw(repos: list[dict]) -> Path:
    """Persist the raw API response to disk, timestamped, before transformation."""
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = RAW_DATA_DIR / f"github_repos_{timestamp}.json"

    with open(out_path, "w") as f:
        json.dump(repos, f, indent=2)

    print(f"Saved {len(repos)} raw records to {out_path}")
    return out_path


if __name__ == "__main__":
    repos = fetch_repos(language="python", min_stars=1000, pages=3)
    save_raw(repos)