"""
PySpark ETL Pipeline — mirrors the pandas pipeline using Spark DataFrames.
Run with: spark-submit pipeline/spark_pipeline.py
Or via Python if pyspark is installed: python pipeline/spark_pipeline.py

Produces the same Bronze/Silver/Gold structure as the pandas pipeline
but uses distributed Spark processing — suitable for large-scale runs.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    from pyspark.sql import SparkSession, DataFrame
    from pyspark.sql import functions as F
    from pyspark.sql.types import (
        BooleanType, DoubleType, IntegerType, LongType,
        StringType, StructField, StructType, TimestampType,
    )
    SPARK_AVAILABLE = True
except ImportError:
    SPARK_AVAILABLE = False

SOURCE_DIR = "output"
LAKEHOUSE_DIR = "lakehouse"


def get_spark() -> "SparkSession":
    return (
        SparkSession.builder
        .appName("BPO-Platform-Pipeline")
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.sql.parquet.compression.codec", "snappy")
        .config("spark.driver.memory", "2g")
        .getOrCreate()
    )


# ---------------------------------------------------------------------------
# Bronze
# ---------------------------------------------------------------------------

def spark_bronze(spark: "SparkSession") -> None:
    print("\n[SPARK] BRONZE — Raw Ingestion")
    tables = [
        "clients", "agents", "campaigns", "dnc_list", "leads",
        "calls", "qa_reviews", "insurance_qualifications",
        "appointments", "realestate_qualifications",
        "payment_arrangements", "agent_daily_performance", "ml_features",
    ]
    for table in tables:
        src = f"{SOURCE_DIR}/{table}.csv"
        if not Path(src).exists():
            print(f"  [skip] {table}")
            continue
        df = spark.read.csv(src, header=True, inferSchema=True)
        n = df.count()
        # Partition by vertical if column exists
        if "vertical" in df.columns:
            out = f"{LAKEHOUSE_DIR}/bronze/{table}"
            df.write.mode("overwrite").partitionBy("vertical").parquet(out)
        else:
            out = f"{LAKEHOUSE_DIR}/bronze/{table}/{table}.parquet"
            df.write.mode("overwrite").parquet(out)
        print(f"  {table:<40} {n:>7,} rows  → {out}")

    # Pipeline events JSONL
    events_src = f"{SOURCE_DIR}/pipeline_events.jsonl"
    if Path(events_src).exists():
        df = spark.read.json(events_src)
        # Flatten payload struct
        if "payload" in df.columns:
            payload_cols = df.schema["payload"].dataType.fieldNames()
            for col in payload_cols:
                df = df.withColumn(f"payload_{col}", F.col(f"payload.{col}"))
            df = df.drop("payload")
        out = f"{LAKEHOUSE_DIR}/bronze/pipeline_events"
        df.write.mode("overwrite").parquet(out)
        print(f"  pipeline_events                          {df.count():>7,} rows  → {out}")


# ---------------------------------------------------------------------------
# Silver
# ---------------------------------------------------------------------------

def spark_silver(spark: "SparkSession") -> None:
    print("\n[SPARK] SILVER — Domain Transforms")

    def _read(table: str, vertical: str | None = None) -> "DataFrame":
        path = f"{LAKEHOUSE_DIR}/bronze/{table}"
        if not Path(path).exists():
            return spark.createDataFrame([], StructType([]))
        df = spark.read.parquet(path)
        if vertical and "vertical" in df.columns:
            df = df.filter(F.col("vertical") == vertical)
        return df

    # Dims
    agents = _read("agents")
    if not agents.rdd.isEmpty():
        agents = agents.withColumn("tenure_days",
                    F.datediff(F.current_date(), F.to_date("hire_date")))
        agents.write.mode("overwrite").parquet(f"{LAKEHOUSE_DIR}/silver/dim_agents")
        print(f"  dim_agents                               {agents.count():>7,} rows")

    campaigns = _read("campaigns")
    if not campaigns.rdd.isEmpty():
        campaigns = campaigns.withColumn("is_active", F.col("status") == "Active")
        campaigns.write.mode("overwrite").parquet(f"{LAKEHOUSE_DIR}/silver/dim_campaigns")
        print(f"  dim_campaigns                            {campaigns.count():>7,} rows")

    # Calls — enrich with agent info
    calls = _read("calls")
    if not calls.rdd.isEmpty():
        calls = (calls
            .withColumn("started_at", F.to_timestamp("started_at"))
            .withColumn("ended_at", F.to_timestamp("ended_at"))
            .withColumn("call_date", F.to_date("started_at"))
            .withColumn("call_hour", F.hour("started_at"))
            .withColumn("call_month", F.month("started_at"))
            .withColumn("call_year", F.year("started_at"))
            .withColumn("is_converted",
                F.col("disposition").isin(["Interested", "Transfer"]))
            .withColumn("talk_minutes",
                (F.col("duration_seconds").cast(DoubleType()) / 60).cast(DoubleType()))
        )
        if not agents.rdd.isEmpty():
            agent_slim = agents.select(
                "agent_id",
                F.col("role").alias("agent_role"),
                F.col("performance_tier").alias("agent_perf_tier"),
            )
            calls = calls.join(agent_slim, on="agent_id", how="left")

        calls.write.mode("overwrite").parquet(f"{LAKEHOUSE_DIR}/silver/silver_calls_all")
        print(f"  silver_calls_all                         {calls.count():>7,} rows")

    # Leads — flatten vertical_data JSON
    leads_raw = _read("leads")
    if not leads_raw.rdd.isEmpty():
        leads_raw = leads_raw.withColumn("lead_age_days",
            F.datediff(F.current_date(), F.to_date("created_at")))
        leads_raw.write.mode("overwrite").parquet(f"{LAKEHOUSE_DIR}/silver/silver_leads")
        print(f"  silver_leads                             {leads_raw.count():>7,} rows")

    # Agent performance — rolling 3-day flag via window
    perf = _read("agent_daily_performance")
    if not perf.rdd.isEmpty():
        from pyspark.sql.window import Window
        w = Window.partitionBy("agent_id").orderBy("date").rowsBetween(-2, 0)
        perf = perf.withColumn(
            "below_threshold_3d",
            F.sum(F.col("below_threshold").cast(IntegerType())).over(w) == 3,
        )
        perf.write.mode("overwrite").parquet(f"{LAKEHOUSE_DIR}/silver/silver_agent_performance")
        print(f"  silver_agent_performance                 {perf.count():>7,} rows")


# ---------------------------------------------------------------------------
# Gold
# ---------------------------------------------------------------------------

def spark_gold(spark: "SparkSession") -> None:
    print("\n[SPARK] GOLD — Business Aggregates")

    def _read_silver(name: str) -> "DataFrame":
        path = f"{LAKEHOUSE_DIR}/silver/{name}"
        if not Path(path).exists():
            return spark.createDataFrame([], StructType([]))
        return spark.read.parquet(path)

    calls = _read_silver("silver_calls_all")
    campaigns = _read_silver("dim_campaigns")

    # Campaign KPIs
    if not calls.rdd.isEmpty():
        kpis = calls.groupBy("campaign_id").agg(
            F.count("call_id").alias("total_calls"),
            F.sum(F.col("is_converted").cast(IntegerType())).alias("total_converted"),
            F.avg("duration_seconds").alias("avg_duration_seconds"),
            F.sum("talk_minutes").alias("total_talk_minutes"),
            F.avg("sentiment_score").alias("avg_sentiment"),
            F.countDistinct("agent_id").alias("unique_agents"),
            F.countDistinct("lead_id").alias("unique_leads"),
        ).withColumn("conversion_rate",
            F.round(F.col("total_converted") / F.col("total_calls"), 4)
        )
        if not campaigns.rdd.isEmpty():
            kpis = kpis.join(
                campaigns.select("campaign_id", "name", "vertical",
                                 "dialing_mode", "status"),
                on="campaign_id", how="left",
            )
        kpis.write.mode("overwrite").parquet(f"{LAKEHOUSE_DIR}/gold/gold_campaign_kpis")
        print(f"  gold_campaign_kpis                       {kpis.count():>7,} rows")

    # Agent Performance Gold
    perf = _read_silver("silver_agent_performance")
    agents = _read_silver("dim_agents")
    if not perf.rdd.isEmpty():
        agent_kpis = perf.groupBy("agent_id").agg(
            F.sum("total_calls").alias("total_calls"),
            F.avg("conversion_rate").alias("avg_conversion_rate"),
            F.sum("talk_time_seconds").alias("total_talk_time_seconds"),
            F.max("below_threshold_3d").alias("consecutive_below_flag"),
        )
        if not agents.rdd.isEmpty():
            agent_kpis = agent_kpis.join(
                agents.select("agent_id", "first_name", "last_name",
                              "role", "performance_tier"),
                on="agent_id", how="left",
            )
        agent_kpis.write.mode("overwrite").parquet(
            f"{LAKEHOUSE_DIR}/gold/gold_agent_performance")
        print(f"  gold_agent_performance                   {agent_kpis.count():>7,} rows")

    # ML Feature Store Gold
    ml_path = f"{SOURCE_DIR}/ml_features.csv"
    if Path(ml_path).exists():
        ml = spark.read.csv(ml_path, header=True, inferSchema=True)
        if not calls.rdd.isEmpty():
            call_feats = calls.groupBy("lead_id").agg(
                F.count("call_id").alias("feat_n_calls"),
                F.avg("sentiment_score").alias("feat_avg_sentiment"),
                F.avg("duration_seconds").alias("feat_avg_duration"),
                F.countDistinct("agent_id").alias("feat_distinct_agents"),
            )
            ml = ml.join(call_feats, on="lead_id", how="left")
        ml.write.mode("overwrite").parquet(f"{LAKEHOUSE_DIR}/gold/gold_ml_feature_store_spark")
        print(f"  gold_ml_feature_store_spark              {ml.count():>7,} rows")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_spark_pipeline() -> None:
    if not SPARK_AVAILABLE:
        print("PySpark not installed. Run: pip install pyspark")
        print("Falling back to pandas pipeline.")
        return False

    print("\n" + "=" * 70)
    print("  SPARK PIPELINE — BPO Platform")
    print("=" * 70)
    spark = get_spark()
    spark.sparkContext.setLogLevel("ERROR")
    try:
        spark_bronze(spark)
        spark_silver(spark)
        spark_gold(spark)
        print("\n[SPARK] Pipeline complete.")
    finally:
        spark.stop()
    return True


if __name__ == "__main__":
    run_spark_pipeline()
