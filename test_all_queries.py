"""Run every query in the catalog and report pass/fail."""
import sys
sys.path.insert(0, ".")

import duckdb
from pathlib import Path
from dashboard.sql_catalog import QUERIES

con = duckdb.connect(":memory:")
for pq in Path("lakehouse/gold").glob("*.parquet"):
    con.execute(f"CREATE VIEW {pq.stem} AS SELECT * FROM read_parquet('{pq.as_posix()}')")

passed, failed = 0, []
for name, meta in QUERIES.items():
    try:
        df = con.execute(meta["sql"]).df()
        print(f"  OK  {name}  ({len(df)} rows)")
        passed += 1
    except Exception as e:
        print(f"  ERR {name}: {e}")
        failed.append((name, str(e)))

print(f"\n{passed}/{len(QUERIES)} passed")
if failed:
    print("FAILURES:")
    for n, e in failed:
        print(f"  {n}: {e}")
    sys.exit(1)
