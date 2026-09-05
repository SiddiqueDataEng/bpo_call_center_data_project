"""
Silver Layer — Domain-Owned Transformations (ETL).

One transform function per domain data product.
Each reads from Bronze, applies business rules, enforces referential
integrity, and writes clean Silver parquet.

Domains:
  1. Platform Dims   — dim_agents, dim_campaigns, dim_clients
  2. Insurance       — silver_insurance_calls, silver_insurance_qualified
  3. Healthcare      — silver_healthcare_calls, silver_appointments
  4. Real Estate     — silver_realestate_calls, silver_realestate_qualified
  5. AR Sales        — silver_ar_calls, silver_ar_arrangements
  6. Platform Ops    — silver_calls_all, silver_qa_reviews, silver_agent_performance
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline.utils.io import write_parquet, load_layer
from pipeline.utils.logger import pipeline_log

BRONZE_DIR = Path("lakehouse/bronze")
SILVER_DIR = Path("lakehouse/silver")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bronze(table: str, vertical: str | None = None) -> pd.DataFrame:
    """Load a Bronze table, optionally a single vertical partition."""
    if vertical:
        safe = vertical.replace(" ", "_").lower()
        p = BRONZE_DIR / table / f"partition={safe}" / f"{table}.parquet"
        if p.exists():
            return pd.read_parquet(p)
    base = BRONZE_DIR / table / f"{table}.parquet"
    if base.exists():
        return pd.read_parquet(base)
    # Try all partitions
    parts = list((BRONZE_DIR / table).rglob("*.parquet"))
    if parts:
        return pd.concat([pd.read_parquet(p) for p in parts], ignore_index=True)
    return pd.DataFrame()


def _write_silver(df: pd.DataFrame, name: str) -> None:
    path = SILVER_DIR / f"{name}.parquet"
    write_parquet(df, path)


def _cast_datetime(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce", utc=True)
    return df


def _cast_bool(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = df[c].map(
                lambda x: True if str(x).strip().lower() in ("true", "1", "yes") else False
            )
    return df


def _cast_numeric(df: pd.DataFrame, int_cols: list[str], float_cols: list[str]) -> pd.DataFrame:
    for c in int_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")
    for c in float_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype(float)
    return df


# ---------------------------------------------------------------------------
# 1. Platform Dimensions
# ---------------------------------------------------------------------------

def transform_dim_agents() -> pd.DataFrame:
    df = _bronze("agents")
    if df.empty:
        return df
    df = _cast_datetime(df, ["hire_date"])
    df = _cast_bool(df, ["is_active"])
    df = _cast_numeric(df, [], ["base_conversion_rate"])
    # Derive tenure_days
    df["tenure_days"] = (
        pd.Timestamp.now(tz="UTC") - df["hire_date"]
    ).dt.days.astype("Int64")
    df = df.drop(columns=[c for c in df.columns if c.startswith("_bronze")], errors="ignore")
    _write_silver(df, "dim_agents")
    pipeline_log("SILVER", "dim_agents", len(df), len(df))
    return df


def transform_dim_campaigns() -> pd.DataFrame:
    df = _bronze("campaigns")
    if df.empty:
        return df
    df = _cast_datetime(df, ["created_at", "closed_at"])
    df = _cast_numeric(df, [], ["dial_ratio", "target_abandon_rate", "conversion_threshold"])
    # Derive is_active
    df["is_active"] = df["status"] == "Active"
    # Duration days for closed campaigns
    df["campaign_duration_days"] = (
        (df["closed_at"] - df["created_at"]).dt.days.where(df["closed_at"].notna())
    ).astype("Int64")
    df = df.drop(columns=[c for c in df.columns if c.startswith("_bronze")], errors="ignore")
    _write_silver(df, "dim_campaigns")
    pipeline_log("SILVER", "dim_campaigns", len(df), len(df))
    return df


def transform_dim_clients() -> pd.DataFrame:
    df = _bronze("clients")
    if df.empty:
        return df
    df = _cast_datetime(df, ["created_at"])
    df = df.drop(columns=[c for c in df.columns if c.startswith("_bronze")], errors="ignore")
    _write_silver(df, "dim_clients")
    pipeline_log("SILVER", "dim_clients", len(df), len(df))
    return df


def transform_dim_dnc() -> pd.DataFrame:
    df = _bronze("dnc_list")
    if df.empty:
        return df
    df = _cast_datetime(df, ["added_at"])
    df = df.drop_duplicates(subset=["phone_e164"])
    df = df.drop(columns=[c for c in df.columns if c.startswith("_bronze")], errors="ignore")
    _write_silver(df, "dim_dnc")
    pipeline_log("SILVER", "dim_dnc", len(df), len(df))
    return df


# ---------------------------------------------------------------------------
# 2. Core Calls Silver (all verticals)
# ---------------------------------------------------------------------------

def transform_silver_calls() -> pd.DataFrame:
    """Full calls table enriched with agent and campaign dims."""
    calls = _bronze("calls")
    if calls.empty:
        return calls

    calls = _cast_datetime(calls, ["started_at", "ended_at", "created_at"])
    calls = _cast_bool(calls, ["compliance_flagged"])
    calls = _cast_numeric(
        calls,
        int_cols=["duration_seconds", "compliance_phrase_position"],
        float_cols=["sentiment_score"],
    )
    # Derived columns
    calls["call_date"] = calls["started_at"].dt.date.astype(str)
    calls["call_hour"] = calls["started_at"].dt.hour.astype("Int64")
    calls["call_week"] = calls["started_at"].dt.isocalendar().week.astype("Int64")
    calls["call_month"] = calls["started_at"].dt.month.astype("Int64")
    calls["call_year"] = calls["started_at"].dt.year.astype("Int64")
    calls["is_converted"] = calls["disposition"].isin(["Interested", "Transfer"])
    calls["is_compliance_issue"] = calls["compliance_flagged"] == True
    calls["talk_minutes"] = (calls["duration_seconds"].fillna(0) / 60).round(2)

    # Enrich with agent dims
    agents = _bronze("agents")[["agent_id", "role", "performance_tier",
                                "base_conversion_rate", "vertical_specialization"]].copy()
    agents.columns = ["agent_id", "agent_role", "agent_perf_tier",
                      "agent_base_conv_rate", "agent_vertical"]
    calls = calls.merge(agents, on="agent_id", how="left")

    # Drop bronze meta
    calls = calls.drop(columns=[c for c in calls.columns if c.startswith("_bronze")],
                       errors="ignore")
    _write_silver(calls, "silver_calls_all")
    pipeline_log("SILVER", "silver_calls_all", len(calls), len(calls))
    return calls


def transform_silver_leads() -> pd.DataFrame:
    """Leads enriched with DNC status and campaign info."""
    leads = _bronze("leads")
    if leads.empty:
        return leads

    leads = _cast_datetime(leads, ["created_at", "updated_at",
                                   "consent_timestamp", "dnc_flagged_at"])
    leads = _cast_bool(leads, ["dnc_flagged"])
    leads = _cast_numeric(leads, int_cols=["lead_score"], float_cols=[])

    # Parse vertical_data JSON to flat columns with prefix
    def _parse_vdata(row):
        try:
            return json.loads(row) if isinstance(row, str) else {}
        except Exception:
            return {}

    vdata_df = leads["vertical_data"].apply(_parse_vdata).apply(pd.Series)
    # Prefix all extracted columns
    vdata_df.columns = [f"vd_{c}" for c in vdata_df.columns]
    leads = pd.concat([leads.drop(columns=["vertical_data"]), vdata_df], axis=1)

    leads["lead_age_days"] = (
        pd.Timestamp.now(tz="UTC") - leads["created_at"]
    ).dt.days.astype("Int64")

    leads = leads.drop(columns=[c for c in leads.columns if c.startswith("_bronze")],
                       errors="ignore")
    _write_silver(leads, "silver_leads")
    pipeline_log("SILVER", "silver_leads", len(leads), len(leads))
    return leads


# ---------------------------------------------------------------------------
# 3. Insurance Domain Silver
# ---------------------------------------------------------------------------

def transform_silver_insurance() -> pd.DataFrame:
    calls = _bronze("calls", vertical="insurance")
    quals = _bronze("insurance_qualifications")
    leads = pd.read_parquet(SILVER_DIR / "silver_leads.parquet") if (
        SILVER_DIR / "silver_leads.parquet").exists() else _bronze("leads")

    if calls.empty:
        return pd.DataFrame()

    calls = _cast_datetime(calls, ["started_at", "ended_at"])
    calls = _cast_bool(calls, ["compliance_flagged"])
    calls = _cast_numeric(calls, ["duration_seconds"], ["sentiment_score"])
    calls["is_converted"] = calls["disposition"].isin(["Interested", "Transfer"])

    quals = _cast_datetime(quals, ["created_at"])
    quals = _cast_bool(quals, ["aca_eligible", "aca_subsidy_eligible",
                               "tobacco_user", "transfer_completed"])
    quals = _cast_numeric(quals, ["household_size"],
                          ["annual_income"])

    # Join calls → quals → leads
    df = calls.merge(quals, on=["call_id", "lead_id"], how="left", suffixes=("", "_qual"))
    ins_lead_cols = [c for c in leads.columns if c.startswith("vd_ins") or
                     c in ("lead_id", "state", "city", "zip_code", "lead_score")]
    df = df.merge(leads[ins_lead_cols], on="lead_id", how="left")

    df["call_date"] = pd.to_datetime(df["started_at"], utc=True, errors="coerce").dt.date.astype(str)

    df = df.drop(columns=[c for c in df.columns if c.startswith("_bronze")], errors="ignore")
    _write_silver(df, "silver_insurance")
    pipeline_log("SILVER", "silver_insurance", len(df), len(df))
    return df


# ---------------------------------------------------------------------------
# 4. Healthcare Domain Silver
# ---------------------------------------------------------------------------

def transform_silver_healthcare() -> pd.DataFrame:
    calls = _bronze("calls", vertical="healthcare")
    appts = _bronze("appointments")
    leads = pd.read_parquet(SILVER_DIR / "silver_leads.parquet") if (
        SILVER_DIR / "silver_leads.parquet").exists() else _bronze("leads")

    if calls.empty:
        return pd.DataFrame()

    calls = _cast_datetime(calls, ["started_at", "ended_at"])
    calls = _cast_numeric(calls, ["duration_seconds"], ["sentiment_score"])
    calls["is_converted"] = calls["disposition"].isin(["Interested", "Callback"])

    appts = _cast_datetime(appts, ["created_at", "appointment_date"])
    appts = _cast_bool(appts, ["webhook_sent", "confirmation_email_sent"])

    df = calls.merge(appts, on=["call_id", "lead_id"], how="left",
                     suffixes=("", "_appt"))
    hc_lead_cols = [c for c in leads.columns if c.startswith("vd_hc") or
                    c in ("lead_id", "state", "lead_score")]
    df = df.merge(leads[hc_lead_cols], on="lead_id", how="left")

    df["appointment_scheduled"] = df["appointment_id"].notna()
    df["call_date"] = pd.to_datetime(df["started_at"], utc=True, errors="coerce").dt.date.astype(str)
    df = df.drop(columns=[c for c in df.columns if c.startswith("_bronze")], errors="ignore")
    _write_silver(df, "silver_healthcare")
    pipeline_log("SILVER", "silver_healthcare", len(df), len(df))
    return df


# ---------------------------------------------------------------------------
# 5. Real Estate Domain Silver
# ---------------------------------------------------------------------------

def transform_silver_realestate() -> pd.DataFrame:
    calls = _bronze("calls", vertical="realestate")
    quals = _bronze("realestate_qualifications")
    leads = pd.read_parquet(SILVER_DIR / "silver_leads.parquet") if (
        SILVER_DIR / "silver_leads.parquet").exists() else _bronze("leads")

    if calls.empty:
        return pd.DataFrame()

    calls = _cast_datetime(calls, ["started_at", "ended_at"])
    calls = _cast_numeric(calls, ["duration_seconds"], ["sentiment_score"])
    calls["is_converted"] = calls["disposition"].isin(["Interested", "Transfer"])

    quals = _cast_datetime(quals, ["created_at"])
    quals = _cast_bool(quals, ["agent_matched"])
    quals = _cast_numeric(quals, ["budget_min", "budget_max", "timeline_months"],
                          ["estimated_value"])

    df = calls.merge(quals, on=["call_id", "lead_id"], how="left", suffixes=("", "_qual"))
    re_lead_cols = [c for c in leads.columns if c.startswith("vd_re") or
                    c in ("lead_id", "state", "lead_score")]
    df = df.merge(leads[re_lead_cols], on="lead_id", how="left")

    df["lead_qualified"] = df["qualification_id"].notna()
    df["call_date"] = pd.to_datetime(df["started_at"], utc=True, errors="coerce").dt.date.astype(str)
    df = df.drop(columns=[c for c in df.columns if c.startswith("_bronze")], errors="ignore")
    _write_silver(df, "silver_realestate")
    pipeline_log("SILVER", "silver_realestate", len(df), len(df))
    return df


# ---------------------------------------------------------------------------
# 6. AR Sales Domain Silver
# ---------------------------------------------------------------------------

def transform_silver_ar() -> pd.DataFrame:
    calls = _bronze("calls", vertical="ar")
    arrangements = _bronze("payment_arrangements")
    leads = pd.read_parquet(SILVER_DIR / "silver_leads.parquet") if (
        SILVER_DIR / "silver_leads.parquet").exists() else _bronze("leads")

    if calls.empty:
        return pd.DataFrame()

    calls = _cast_datetime(calls, ["started_at", "ended_at"])
    calls = _cast_numeric(calls, ["duration_seconds"], ["sentiment_score"])
    calls["is_converted"] = calls["disposition"].isin(["Interested", "Callback"])

    arrangements = _cast_datetime(arrangements, ["created_at"])
    arrangements = _cast_bool(arrangements, ["verbal_confirmation",
                                             "confirmation_email_sent", "sol_expired"])
    arrangements = _cast_numeric(arrangements, [],
                                 ["original_balance", "settlement_amount", "settlement_pct"])

    df = calls.merge(arrangements, on=["call_id", "lead_id"], how="left",
                     suffixes=("", "_arr"))
    ar_lead_cols = [c for c in leads.columns if c.startswith("vd_ar") or
                    c in ("lead_id", "state", "lead_score")]
    df = df.merge(leads[ar_lead_cols], on="lead_id", how="left")

    df["arrangement_made"] = df["arrangement_id"].notna()
    df["call_date"] = pd.to_datetime(df["started_at"], utc=True, errors="coerce").dt.date.astype(str)
    df = df.drop(columns=[c for c in df.columns if c.startswith("_bronze")], errors="ignore")
    _write_silver(df, "silver_ar")
    pipeline_log("SILVER", "silver_ar", len(df), len(df))
    return df


# ---------------------------------------------------------------------------
# 7. QA & Agent Performance Silver
# ---------------------------------------------------------------------------

def transform_silver_qa() -> pd.DataFrame:
    reviews = _bronze("qa_reviews")
    if reviews.empty:
        return reviews
    reviews = _cast_datetime(reviews, ["reviewed_at"])
    reviews = _cast_numeric(reviews, [], ["total_score"])

    # Parse rubric scores JSON
    def _parse_scores(val):
        try:
            return json.loads(val) if isinstance(val, str) else {}
        except Exception:
            return {}

    scores_df = reviews["scores"].apply(_parse_scores).apply(pd.Series)
    scores_df.columns = [f"rubric_{c.lower().replace(' ','_')}" for c in scores_df.columns]
    reviews = pd.concat([reviews.drop(columns=["scores"]), scores_df], axis=1)
    reviews = reviews.drop(columns=[c for c in reviews.columns if c.startswith("_bronze")],
                           errors="ignore")
    _write_silver(reviews, "silver_qa_reviews")
    pipeline_log("SILVER", "silver_qa_reviews", len(reviews), len(reviews))
    return reviews


def transform_silver_agent_performance() -> pd.DataFrame:
    perf = _bronze("agent_daily_performance")
    if perf.empty:
        return perf
    perf = _cast_datetime(perf, ["date"])
    perf = _cast_bool(perf, ["below_threshold"])
    perf = _cast_numeric(
        perf,
        ["total_calls", "interested_count", "transfer_count",
         "not_interested_count", "dnc_count", "talk_time_seconds"],
        ["avg_handle_time", "conversion_rate", "campaign_threshold"],
    )
    # Rolling 3-day below-threshold flag (for auto-flag logic)
    perf = perf.sort_values(["agent_id", "date"])
    perf["below_threshold_3d"] = (
        perf.groupby("agent_id")["below_threshold"]
        .transform(lambda x: x.rolling(3, min_periods=3).sum() == 3)
    )
    perf = perf.drop(columns=[c for c in perf.columns if c.startswith("_bronze")],
                     errors="ignore")
    _write_silver(perf, "silver_agent_performance")
    pipeline_log("SILVER", "silver_agent_performance", len(perf), len(perf))
    return perf


# ---------------------------------------------------------------------------
# Silver Run
# ---------------------------------------------------------------------------

def run_silver() -> None:
    print("\n" + "=" * 70)
    print("  SILVER LAYER — Domain Transforms")
    print("=" * 70)
    transform_dim_clients()
    transform_dim_agents()
    transform_dim_campaigns()
    transform_dim_dnc()
    transform_silver_leads()
    transform_silver_calls()
    transform_silver_insurance()
    transform_silver_healthcare()
    transform_silver_realestate()
    transform_silver_ar()
    transform_silver_qa()
    transform_silver_agent_performance()


if __name__ == "__main__":
    run_silver()
