# GitHub Repo Analytics Pipeline

An end-to-end ETL pipeline that extracts repository data from the GitHub API,
cleans and enriches it with Python/pandas, and loads it into a partitioned,
clustered BigQuery table for analysis.

Built to demonstrate the core data engineering + analytics engineering skill
set: API extraction, data cleaning, cloud data warehousing, and SQL analysis.

## Architecture

```
GitHub API  →  extract.py  →  raw JSON (data/raw/)
                                     ↓
                              transform.py (pandas)
                                     ↓
                          clean CSV (data/processed/)
                                     ↓
                            load_bigquery.py
                                     ↓
                  BigQuery table (partitioned + clustered)
                                     ↓
                       SQL analysis / Looker Studio dashboard
```

## Why this project

- **Extract**: pulls live data from a real REST API (GitHub), including
  pagination and rate-limit handling.
- **Transform**: flattens nested JSON, handles nulls, deduplicates, and
  engineers derived metrics (e.g. stars-per-day growth velocity).
- **Load**: writes to BigQuery with a **daily partition** and **clustering**
  on `language`/`owner` — the exact pattern used to keep query costs down
  at scale, and a common interview talking point.
- **Analyze**: includes window functions, CTEs, conditional bucketing, and
  BigQuery-specific SQL (`QUALIFY`, `STRUCT`) in `sql/analysis_queries.sql`.

## Project structure

```
github-analytics-pipeline/
├── main.py                    # orchestrates the full pipeline
├── requirements.txt
├── src/
│   ├── extract.py             # pulls data from GitHub API
│   ├── transform.py           # cleans and enriches with pandas
│   └── load_bigquery.py       # loads into BigQuery
├── sql/
│   └── analysis_queries.sql   # analytics queries to run in BigQuery
└── data/
    ├── raw/                   # raw JSON snapshots (gitignored in practice)
    └── processed/             # cleaned CSVs ready to load
```

## Setup

```bash
git clone <your-repo-url>
cd github-analytics-pipeline
pip install -r requirements.txt
```

## Running the pipeline

**Extract + transform only (no cloud account needed):**
```bash
python main.py
```

**Full pipeline including BigQuery load:**

1. Create a GCP project at [console.cloud.google.com](https://console.cloud.google.com).
   BigQuery's Sandbox mode works fine for this and doesn't require a billing
   account — the console offers it automatically if you open BigQuery
   without setting up billing.

2. Create a service account with the **BigQuery Admin** role:
   - IAM & Admin > Service Accounts > Create Service Account
   - Then go to **IAM & Admin > IAM** (not the Service Accounts page) and
     confirm the role actually shows up next to the service account's
     email — role grants during creation don't always persist, so this
     is worth double-checking directly.

3. Generate a JSON key for the service account (Keys tab > Add Key > JSON),
   save it in your project folder, and add its filename to `.gitignore` —
   never commit this file.

4. If your project is in Sandbox mode, create the dataset manually first:
   BigQuery console > Datasets > Create dataset > ID `github_analytics`.
   Sandbox mode blocks dataset creation via the API, but loading data into
   an existing dataset works fine.

5. Set your credentials and project:
   ```bash
   # Windows (cmd)
   set GOOGLE_APPLICATION_CREDENTIALS=C:\path\to\your-key.json
   set GCP_PROJECT_ID=your-project-id

   # Mac/Linux
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your-key.json"
   export GCP_PROJECT_ID="your-project-id"
   ```

6. Run with the load flag:
   ```bash
   python main.py --load
   ```

## Example insight produced

Running this pipeline against Python repos with 1,000+ stars surfaces things
like which repos are gaining stars fastest relative to their age — a metric
(`stars_per_day`) that isn't available directly from the API and has to be
engineered from raw fields, which is exactly the kind of transformation
step this project is meant to show off.

## Lessons learned

A few real issues came up getting this running end to end, worth noting
since they're common gotchas with BigQuery specifically:

- **CSV round-trips lose datetime types.** `transform.py` writes proper
  `datetime` columns to CSV, but `pd.read_csv()` reads them back as plain
  strings unless told otherwise. BigQuery then rejects the load because
  the partition field (`extracted_at`) arrives as `STRING` instead of
  `TIMESTAMP`. Fixed by passing `parse_dates=[...]` to `read_csv()` in
  `load_bigquery.py`.
- **Sandbox mode has API restrictions.** A GCP project without a billing
  account attached runs BigQuery in "Sandbox" mode, which blocks dataset
  creation through the API (`bigquery.datasets.create`) even for a
  project Owner. The dataset has to be created once through the console
  UI; after that, loading data into it via the API works normally.
- **Service account roles should be verified on the IAM page, not the
  Service Accounts page.** Role assignment during service account
  creation can silently fail to persist. `IAM & Admin > IAM` is the
  source of truth for what access a principal actually has.

## Possible extensions

- Orchestrate with **Airflow** (schedule as a daily DAG instead of manual runs)
- Add **dbt** models on top of the BigQuery table for a proper analytics
  engineering layer
- Build a **Looker Studio** dashboard connected directly to BigQuery
- Add a `Dockerfile` for containerized, reproducible runs
