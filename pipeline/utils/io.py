"""File I/O helpers — read/write CSV, Parquet, JSONL."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import pandas as pd


def read_csv(path: str | Path, **kwargs) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False, **kwargs)


def read_parquet(path: str | Path) -> pd.DataFrame:
    return pd.read_parquet(path)


def write_parquet(df: pd.DataFrame, path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False, engine="pyarrow")


def write_csv(df: pd.DataFrame, path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def read_jsonl(path: str | Path) -> list[dict]:
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def write_jsonl(records: list[dict], path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def load_layer(base: str | Path, table: str) -> Optional[pd.DataFrame]:
    """Load a layer table (parquet preferred, csv fallback)."""
    base = Path(base)
    p = base / f"{table}.parquet"
    if p.exists():
        return read_parquet(p)
    c = base / f"{table}.csv"
    if c.exists():
        return read_csv(c)
    return None
