"""
load_bigquery.py
------------------
Loads the cleaned CSV into BigQuery, creating a partitioned + clustered
table. This is the "Load" step of the pipeline.

SETUP (do this once, before running this file):

1. Install the client library:
   pip install google-cloud-bigquery

2. Install and auth the gcloud CLI (https://cloud.google.com/sdk/docs/install):
   gcloud auth application-default login

3. Create a GCP project (or use an existing one) and enable the BigQuery API:
   https://console.cloud.google.com/apis/library/bigquery.googleapis.com

4. Set your project ID as an environment variable:
   export GCP_PROJECT_ID="your-project-id"      (Git Bash)
   $env:GCP_PROJECT_ID="your-project-id"         (PowerShell)

5. Run this script:
   python src/load_bigquery.py
"""

import os
import pandas as pd
from pathlib import Path
from google.cloud import bigquery

PROCESSED_DATA_DIR = Path(__file__).parent.parent / "data" / "processed"
DATASET_ID = "github_analytics"
TABLE_ID = "repos"


def get_latest_processed_csv() -> Path:
    files = sorted(PROCESSED_DATA_DIR.glob("repos_clean_*.csv"))
    if not files:
        raise FileNotFoundError("No processed data found — run transform.py first.")
    return files[-1]


def ensure_dataset_exists(client: bigquery.Client, dataset_id: str):
    """Verify the dataset exists. In BigQuery Sandbox mode, datasets must be
    created manually via the console UI since the API create call requires billing."""
    dataset_ref = bigquery.DatasetReference(client.project, dataset_id)
    try:
        client.get_dataset(dataset_ref)
        print(f"Found existing dataset {dataset_id}")
    except Exception as e:
        raise RuntimeError(
            f"Dataset '{dataset_id}' not found. In BigQuery Sandbox mode, "
            f"create it manually first via the console UI (Datasets > Create dataset)."
        ) from e


def load_to_bigquery(csv_path: Path):
    project_id = os.environ.get("GCP_PROJECT_ID")
    if not project_id:
        raise EnvironmentError(
            "Set GCP_PROJECT_ID env var first."
        )

    client = bigquery.Client(project=project_id)
    ensure_dataset_exists(client, DATASET_ID)

    table_ref = f"{project_id}.{DATASET_ID}.{TABLE_ID}"

    df = pd.read_csv(csv_path, parse_dates=["created_at", "updated_at", "extracted_at"])

    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE",  # overwrite for demo simplicity
        time_partitioning=bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field="extracted_at",
        ),
        clustering_fields=["language", "owner"],
    )

    job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
    job.result()  # wait for the job to finish

    table = client.get_table(table_ref)
    print(f"Loaded {table.num_rows} rows into {table_ref}")


if __name__ == "__main__":
    csv_path = get_latest_processed_csv()
    load_to_bigquery(csv_path)