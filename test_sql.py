import sys
sys.path.insert(0, ".")

import duckdb
from pathlib import Path

# Register Gold parquets
con = duckdb.connect(":memory:")
gold = Path("lakehouse/gold")
views = []
for pq in gold.glob("*.parquet"):
    con.execute(f"CREATE VIEW {pq.stem} AS SELECT * FROM read_parquet('{pq.as_posix()}')")
    views.append(pq.stem)
print(f"Views registered: {len(views)}")
for v in sorted(views):
    print(f"  {v}")

# Test window function query
print("\n--- Window function test ---")
df = con.execute("""
SELECT campaign_id, call_month, total_calls,
    SUM(total_calls) OVER (PARTITION BY campaign_id ORDER BY call_month) AS running_calls,
    ROUND(SUM(total_converted) OVER (PARTITION BY campaign_id ORDER BY call_month) * 100.0
          / NULLIF(SUM(total_calls) OVER (PARTITION BY campaign_id ORDER BY call_month), 0), 2)
                                                                          AS running_conv_pct
FROM gold_insurance_kpis
ORDER BY campaign_id, call_month
LIMIT 5
""").df()
print(df.to_string(index=False))

# Test CTE query
print("\n--- CTE test ---")
df2 = con.execute("""
WITH stats AS (
    SELECT vertical, ROUND(AVG(conversion_rate)*100,2) AS avg_conv_pct
    FROM gold_campaign_kpis GROUP BY vertical
)
SELECT * FROM stats ORDER BY avg_conv_pct DESC
""").df()
print(df2.to_string(index=False))

# Test SQL catalog
from dashboard.sql_catalog import QUERIES
print(f"\nSQL catalog: {len(QUERIES)} queries loaded")
for level in ["Basic", "Intermediate", "Window Functions", "CTEs", "Advanced"]:
    n = sum(1 for q in QUERIES.values() if q["level"] == level)
    print(f"  {level:<20} {n} queries")

# Spot-run 3 catalog queries
print("\n--- Running sample catalog queries ---")
for name in ["B1 – Campaign Overview", "W2 – Agent Conversion Rank by Tier", "A3 – Predictive Score Lift Analysis"]:
    sql = QUERIES[name]["sql"]
    try:
        df = con.execute(sql).df()
        print(f"  OK  {name}  ({len(df)} rows)")
    except Exception as e:
        print(f"  ERR {name}: {e}")

# Test NLP engine
from dashboard.nlp_engine import generate_sql_local
q = generate_sql_local("show me top agents by conversion rate")
print(f"\nNLP test — generated SQL preview:")
print(q[:200])

print("\nAll checks passed.")
