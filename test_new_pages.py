import sys
sys.path.insert(0, ".")

# Test glossary data loads
from dashboard.glossary_page import CATEGORIES
total = sum(len(v) for v in CATEGORIES.values())
print(f"Glossary: {len(CATEGORIES)} categories, {total} terms")
for cat, terms in CATEGORIES.items():
    live = sum(1 for t in terms if t.get("table"))
    print(f"  {cat}: {len(terms)} terms, {live} with live data")

# Test AI chat chart detection
from dashboard.ai_chat_page import detect_chart_type, build_chart
import pandas as pd

df = pd.DataFrame({
    "month": ["2026-01","2026-02","2026-03"],
    "conversion_rate": [0.21, 0.19, 0.23],
})
ct = detect_chart_type("show conversion rate trend over time", df)
print(f"\nChart type detected for 'trend over time': {ct}")
fig = build_chart(df, ct, "Conversion Rate Trend")
print(f"Chart built: {type(fig).__name__}")

df2 = pd.DataFrame({
    "vertical": ["Insurance","Healthcare","AR","RealEstate"],
    "total_calls": [1500, 1200, 1800, 900],
})
ct2 = detect_chart_type("compare total calls across verticals", df2)
print(f"Chart type for 'compare': {ct2}")
fig2 = build_chart(df2, ct2, "Calls by Vertical")
print(f"Chart built: {type(fig2).__name__}")

# Test NLP + chart end-to-end
from dashboard.nlp_engine import generate_sql_local
import duckdb
from pathlib import Path

con = duckdb.connect(":memory:")
for pq in Path("lakehouse/gold").glob("*.parquet"):
    con.execute(f"CREATE VIEW {pq.stem} AS SELECT * FROM read_parquet('{pq.as_posix()}')")

questions = [
    "Which agents need QA review?",
    "Show compliance violations by vertical",
    "What is the AR recovery rate trend?",
]
for q in questions:
    sql = generate_sql_local(q)
    try:
        df = con.execute(sql.replace("-- Auto-generated (local NLP)\n", "")).df()
        ct = detect_chart_type(q, df)
        fig = build_chart(df, ct, q)
        print(f"  OK  '{q}' -> {ct} chart, {len(df)} rows")
    except Exception as e:
        print(f"  ERR '{q}': {e}")

print("\nAll checks passed.")
