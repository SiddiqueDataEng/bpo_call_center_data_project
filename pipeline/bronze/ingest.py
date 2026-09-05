"""
Bronze Layer — Raw Ingestion (ELT).

Reads source CSV/JSONL files, validates schemas, routes valid rows to
Bronze parquet partitioned by vertical+date, routes invalid rows to DLQ.
No transformations — Bronze is immutable raw records.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from pipeline.utils.io import read_csv, read_jsonl, write_parquet, write_csv
from pipeline.utils.logger import pipeline_log
from pipeline.utils.schema_validator import validate

SOURCE_DIR = Path("output")
BRONZE_DIR = Path("lakehouse/bronze")
DLQ_DIR = Path("lakehouse/dlq")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _add_bronze_meta(df: pd.DataFrame, source_file: str) -> pd.DataFrame:
    """Add Bronze metadata columns (lineage, ingestion timestamp)."""
    now = datetime.now(timezone.utc).isoformat()
    df = df.copy()
    df["_bronze_ingested_at"] = now
    df["_bronze_source_file"] = source_file
    df["_bronze_schema_version"] = "1.0"
    return df


def _write_bronze(df: pd.DataFrame, table: str, partition_col: str | None = None) -> None:
    """Write to bronze layer, optionally partitioning by a column (e.g. vertical)."""
    if partition_col and partition_col in df.columns:
        for val, group in df.groupby(partition_col):
            safe_val = str(val).replace(" ", "_").lower()
            path = BRONZE_DIR / table / f"partition={safe_val}" / f"{table}.parquet"
            write_parquet(group.reset_index(drop=True), path)
    else:
        path = BRONZE_DIR / table / f"{table}.parquet"
        write_parquet(df, path)


def _write_dlq(df: pd.DataFrame, table: str) -> None:
    now = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = DLQ_DIR / f"{table}_dlq_{now}.csv"
    write_csv(df, path)


# ---------------------------------------------------------------------------
# Per-table ingestors
# ---------------------------------------------------------------------------

def ingest_table(name: str, partition_col: str | None = None) -> dict:
    src = SOURCE_DIR / f"{name}.csv"
    if not src.exists():
        pipeline_log("BRONZE", name, 0, 0, extra="[SKIP] source not found")
        return {"table": name, "rows_in": 0, "rows_valid": 0, "rows_dlq": 0}

    df = read_csv(src)
    rows_in = len(df)

    valid_df, invalid_df = validate(df, name)
    valid_df = _add_bronze_meta(valid_df, str(src))

    _write_bronze(valid_df, name, partition_col=partition_col)
    if len(invalid_df):
        _write_dlq(invalid_df, name)

    pipeline_log(
        "BRONZE", name, rows_in, len(valid_df), len(invalid_df),
        f"partition={partition_col}" if partition_col else "",
    )
    return {
        "table": name,
        "rows_in": rows_in,
        "rows_valid": len(valid_df),
        "rows_dlq": len(invalid_df),
    }


def ingest_pipeline_events() -> dict:
    """Special ingestor for JSONL event stream."""
    src = SOURCE_DIR / "pipeline_events.jsonl"
    if not src.exists():
        pipeline_log("BRONZE", "pipeline_events", 0, 0, extra="[SKIP] source not found")
        return {"table": "pipeline_events", "rows_in": 0, "rows_valid": 0, "rows_dlq": 0}

    records = read_jsonl(src)
    rows_in = len(records)

    # Flatten payload JSON field for storage
    flat = []
    for r in records:
        row = {k: v for k, v in r.items() if k != "payload"}
        payload = r.get("payload", {})
        for k, v in payload.items():
            row[f"payload_{k}"] = v
        flat.append(row)

    df = pd.DataFrame(flat)
    valid_df, invalid_df = validate(df, "pipeline_events")
    valid_df = _add_bronze_meta(valid_df, str(src))

    # Partition by vertical
    if "payload_vertical" in valid_df.columns:
        _write_bronze(valid_df, "pipeline_events", partition_col="payload_vertical")
    else:
        _write_bronze(valid_df, "pipeline_events")

    if len(invalid_df):
        _write_dlq(invalid_df, "pipeline_events")

    pipeline_log("BRONZE", "pipeline_events", rows_in, len(valid_df), len(invalid_df))
    return {
        "table": "pipeline_events",
        "rows_in": rows_in,
        "rows_valid": len(valid_df),
        "rows_dlq": len(invalid_df),
    }


# ---------------------------------------------------------------------------
# Bronze run
# ---------------------------------------------------------------------------

BRONZE_TABLES = [
    ("clients",                     None),
    ("agents",                      None),
    ("campaigns",                   "vertical"),
    ("dnc_list",                    None),
    ("leads",                       "vertical"),
    ("calls",                       "vertical"),
    ("qa_reviews",                  None),
    ("insurance_qualifications",    None),
    ("appointments",                None),
    ("realestate_qualifications",   None),
    ("payment_arrangements",        None),
    ("agent_daily_performance",     None),
    ("ml_features",                 "vertical"),
]


def run_bronze() -> list[dict]:
    print("\n" + "=" * 70)
    print("  BRONZE LAYER — Raw Ingestion")
    print("=" * 70)
    stats = []
    for table, partition_col in BRONZE_TABLES:
        stats.append(ingest_table(table, partition_col=partition_col))
    stats.append(ingest_pipeline_events())
    total_in = sum(s["rows_in"] for s in stats)
    total_valid = sum(s["rows_valid"] for s in stats)
    total_dlq = sum(s["rows_dlq"] for s in stats)
    print(f"\n  BRONZE TOTAL  in={total_in:,}  valid={total_valid:,}  dlq={total_dlq:,}")
    return stats


if __name__ == "__main__":
    run_bronze()
