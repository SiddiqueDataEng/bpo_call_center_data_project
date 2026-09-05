"""
Master Pipeline Runner.

Runs full Bronze → Silver → Gold pipeline using pandas (default)
or PySpark if available and --spark flag passed.

Usage:
    python pipeline/run_pipeline.py                  # pandas
    python pipeline/run_pipeline.py --spark          # PySpark
    python pipeline/run_pipeline.py --layer bronze   # single layer
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Ensure pipeline package is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.bronze.ingest import run_bronze
from pipeline.silver.transforms import run_silver
from pipeline.gold.aggregations import run_gold


def print_lakehouse_summary() -> None:
    print("\n" + "=" * 70)
    print("  LAKEHOUSE SUMMARY")
    print("=" * 70)
    base = Path("lakehouse")
    for layer in ["bronze", "silver", "gold"]:
        layer_dir = base / layer
        if not layer_dir.exists():
            continue
        files = list(layer_dir.rglob("*.parquet"))
        total_size = sum(f.stat().st_size for f in files) / (1024 * 1024)
        print(f"  {layer:<10}  {len(files):>4} parquet files   {total_size:>8.2f} MB")
        for f in sorted(files):
            rel = f.relative_to(base)
            size_kb = f.stat().st_size / 1024
            print(f"    {str(rel):<60} {size_kb:>7.1f} KB")

    dlq = base / ".." / "lakehouse" / "dlq"
    dlq_alt = Path("lakehouse/dlq")
    dlq_files = list(dlq_alt.rglob("*.csv")) if dlq_alt.exists() else []
    if dlq_files:
        print(f"\n  DLQ: {len(dlq_files)} files")
        for f in dlq_files:
            print(f"    {f}")


def run_pandas_pipeline(layer: str | None = None) -> None:
    t0 = time.time()
    if layer in (None, "bronze"):
        run_bronze()
    if layer in (None, "silver"):
        run_silver()
    if layer in (None, "gold"):
        run_gold()
    elapsed = time.time() - t0
    print(f"\n  Pandas pipeline finished in {elapsed:.1f}s")
    print_lakehouse_summary()


def run_spark(layer: str | None = None) -> None:
    from pipeline.spark_pipeline import run_spark_pipeline, SPARK_AVAILABLE
    if not SPARK_AVAILABLE:
        print("PySpark not found — falling back to pandas.")
        run_pandas_pipeline(layer)
        return
    t0 = time.time()
    run_spark_pipeline()
    elapsed = time.time() - t0
    print(f"\n  Spark pipeline finished in {elapsed:.1f}s")
    print_lakehouse_summary()


def main() -> None:
    parser = argparse.ArgumentParser(description="BPO Platform ETL/ELT Pipeline")
    parser.add_argument("--spark", action="store_true", help="Use PySpark engine")
    parser.add_argument(
        "--layer",
        choices=["bronze", "silver", "gold"],
        default=None,
        help="Run a single layer only",
    )
    args = parser.parse_args()

    print("\n╔══════════════════════════════════════════════════════════════════╗")
    print("║  BPO Platform — Federated Data Mesh Pipeline                    ║")
    print("║  Bronze → Silver → Gold  (Medallion Architecture)               ║")
    print("╚══════════════════════════════════════════════════════════════════╝")

    if args.spark:
        run_spark(args.layer)
    else:
        run_pandas_pipeline(args.layer)


if __name__ == "__main__":
    main()
