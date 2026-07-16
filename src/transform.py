"""
transform.py
-------------
Takes raw GitHub API JSON and turns it into a clean, analytics-ready table.
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

RAW_DATA_DIR = Path(__file__).parent.parent / "data" / "raw"
PROCESSED_DATA_DIR = Path(__file__).parent.parent / "data" / "processed"


def load_latest_raw() -> list[dict]:
    """Load the most recently extracted raw JSON file."""
    files = sorted(RAW_DATA_DIR.glob("github_repos_*.json"))
    if not files:
        raise FileNotFoundError("No raw data found — run extract.py first.")
    latest = files[-1]
    with open(latest) as f:
        return json.load(f)


def transform(raw_repos: list[dict]) -> pd.DataFrame:
    """
    Flatten nested JSON, select relevant fields, enforce types,
    engineer a couple of useful derived columns, and deduplicate.
    """
    records = []
    for repo in raw_repos:
        records.append({
            "repo_id": repo.get("id"),
            "full_name": repo.get("full_name"),
            "owner": repo.get("owner", {}).get("login"),          # nested field flattened
            "description": repo.get("description"),
            "language": repo.get("language"),
            "stars": repo.get("stargazers_count", 0),
            "forks": repo.get("forks_count", 0),
            "open_issues": repo.get("open_issues_count", 0),
            "watchers": repo.get("watchers_count", 0),
            "created_at": repo.get("created_at"),
            "updated_at": repo.get("updated_at"),
            "license": (repo.get("license") or {}).get("name"),   # nested + null-safe
            "is_fork": repo.get("fork", False),
            "url": repo.get("html_url"),
        })

    df = pd.DataFrame(records)

    # --- Cleaning ---
    df = df.drop_duplicates(subset="repo_id")                     # dedupe on primary key
    df["created_at"] = pd.to_datetime(df["created_at"])
    df["updated_at"] = pd.to_datetime(df["updated_at"])
    df["description"] = df["description"].fillna("")
    df["license"] = df["license"].fillna("No license")

    # --- Derived / engineered columns (common interview talking point) ---
    df["repo_age_days"] = (
        pd.Timestamp.now(tz="UTC") - df["created_at"]
    ).dt.days
    df["stars_per_day"] = (df["stars"] / df["repo_age_days"]).round(2)
    df["fork_to_star_ratio"] = (df["forks"] / df["stars"].replace(0, 1)).round(3)
    df["extracted_at"] = datetime.now(timezone.utc)

    # --- Sort for readability ---
    df = df.sort_values("stars", ascending=False).reset_index(drop=True)

    return df


def save_processed(df: pd.DataFrame) -> Path:
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = PROCESSED_DATA_DIR / f"repos_clean_{timestamp}.csv"
    df.to_csv(out_path, index=False)
    print(f"Saved {len(df)} clean rows to {out_path}")
    return out_path


if __name__ == "__main__":
    raw = load_latest_raw()
    df = transform(raw)
    print(df[["full_name", "stars", "forks", "stars_per_day"]].head(10))
    save_processed(df)