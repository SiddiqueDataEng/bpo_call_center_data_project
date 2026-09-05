"""
Gold Layer — Business-Ready Aggregates (ELT).

Reads Silver parquet, produces Gold analytical tables for:
  - Campaign KPIs
  - Agent Performance Summary
  - Vertical Domain KPIs (Insurance, Healthcare, Real Estate, AR)
  - Compliance & QA Summary
  - ML Feature Store (enriched)
  - Dialer Performance
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from pipeline.utils.io import write_parquet
from pipeline.utils.logger import pipeline_log

SILVER_DIR = Path("lakehouse/silver")
GOLD_DIR = Path("lakehouse/gold")


def _silver(name: str) -> pd.DataFrame:
    p = SILVER_DIR / f"{name}.parquet"
    return pd.read_parquet(p) if p.exists() else pd.DataFrame()


def _write_gold(df: pd.DataFrame, name: str) -> None:
    write_parquet(df, GOLD_DIR / f"{name}.parquet")


# ---------------------------------------------------------------------------
# 1. Campaign KPIs
# ---------------------------------------------------------------------------

def gold_campaign_kpis() -> pd.DataFrame:
    calls = _silver("silver_calls_all")
    campaigns = _silver("dim_campaigns")
    if calls.empty:
        return pd.DataFrame()

    calls["started_at"] = pd.to_datetime(calls["started_at"], utc=True, errors="coerce")
    calls["is_converted"] = calls["disposition"].isin(["Interested", "Transfer"])

    agg = calls.groupby("campaign_id").agg(
        total_calls=("call_id", "count"),
        total_converted=("is_converted", "sum"),
        total_dnc=("disposition", lambda x: (x == "DNC").sum()),
        total_transfer=("disposition", lambda x: (x == "Transfer").sum()),
        total_voicemail=("disposition", lambda x: (x == "Voicemail").sum()),
        total_no_answer=("disposition", lambda x: (x == "NoAnswer").sum()),
        total_callback=("disposition", lambda x: (x == "Callback").sum()),
        avg_duration_seconds=("duration_seconds", "mean"),
        total_talk_minutes=("talk_minutes", "sum"),
        avg_sentiment=("sentiment_score", "mean"),
        compliance_flags=("is_compliance_issue", "sum"),
        unique_agents=("agent_id", "nunique"),
        unique_leads=("lead_id", "nunique"),
        first_call_date=("started_at", "min"),
        last_call_date=("started_at", "max"),
    ).reset_index()

    agg["conversion_rate"] = (agg["total_converted"] / agg["total_calls"]).round(4)
    agg["dnc_rate"] = (agg["total_dnc"] / agg["total_calls"]).round(4)
    agg["avg_duration_seconds"] = agg["avg_duration_seconds"].round(1)
    agg["total_talk_minutes"] = agg["total_talk_minutes"].round(1)
    agg["avg_sentiment"] = agg["avg_sentiment"].round(4)

    # Join campaign metadata
    if not campaigns.empty:
        agg = agg.merge(
            campaigns[["campaign_id", "name", "vertical", "dialing_mode",
                        "status", "client_id", "created_at"]],
            on="campaign_id", how="left",
        )

    _write_gold(agg, "gold_campaign_kpis")
    pipeline_log("GOLD", "gold_campaign_kpis", len(calls), len(agg))
    return agg


# ---------------------------------------------------------------------------
# 2. Agent Performance Summary
# ---------------------------------------------------------------------------

def gold_agent_performance() -> pd.DataFrame:
    perf = _silver("silver_agent_performance")
    agents = _silver("dim_agents")
    if perf.empty:
        return pd.DataFrame()

    agg = perf.groupby("agent_id").agg(
        days_active=("date", "nunique"),
        total_calls=("total_calls", "sum"),
        total_interested=("interested_count", "sum"),
        total_transfers=("transfer_count", "sum"),
        total_dnc=("dnc_count", "sum"),
        total_talk_time_seconds=("talk_time_seconds", "sum"),
        avg_handle_time=("avg_handle_time", "mean"),
        avg_conversion_rate=("conversion_rate", "mean"),
        min_conversion_rate=("conversion_rate", "min"),
        max_conversion_rate=("conversion_rate", "max"),
        days_below_threshold=("below_threshold", "sum"),
        consecutive_below_threshold_flag=("below_threshold_3d", "max"),
    ).reset_index()

    agg["avg_handle_time"] = agg["avg_handle_time"].round(1)
    agg["avg_conversion_rate"] = agg["avg_conversion_rate"].round(4)
    agg["total_talk_hours"] = (agg["total_talk_time_seconds"] / 3600).round(2)

    if not agents.empty:
        agg = agg.merge(
            agents[["agent_id", "first_name", "last_name", "role",
                     "performance_tier", "vertical_specialization",
                     "base_conversion_rate", "hire_date", "tenure_days"]],
            on="agent_id", how="left",
        )

    _write_gold(agg, "gold_agent_performance")
    pipeline_log("GOLD", "gold_agent_performance", len(perf), len(agg))
    return agg


# ---------------------------------------------------------------------------
# 3. Insurance Domain KPIs
# ---------------------------------------------------------------------------

def gold_insurance_kpis() -> pd.DataFrame:
    df = _silver("silver_insurance")
    if df.empty:
        return pd.DataFrame()

    df["started_at"] = pd.to_datetime(df["started_at"], utc=True, errors="coerce")
    df["call_month"] = df["started_at"].dt.tz_localize(None).dt.to_period("M").astype(str)

    agg = df.groupby(["campaign_id", "call_month"]).agg(
        total_calls=("call_id", "count"),
        total_converted=("is_converted", "sum"),
        total_transfers=("disposition", lambda x: (x == "Transfer").sum()),
        aca_eligible_count=("aca_eligible", lambda x: pd.to_numeric(x, errors="coerce").sum()),
        aca_subsidy_count=("aca_subsidy_eligible", lambda x: pd.to_numeric(x, errors="coerce").sum()),
        avg_annual_income=("annual_income", lambda x: pd.to_numeric(x, errors="coerce").mean()),
        avg_household_size=("household_size", lambda x: pd.to_numeric(x, errors="coerce").mean()),
        avg_sentiment=("sentiment_score", "mean"),
        compliance_flags=("compliance_flagged", lambda x: pd.to_numeric(
            x.map({True: 1, False: 0, "True": 1, "False": 0}), errors="coerce"
        ).sum()),
    ).reset_index()

    agg["conversion_rate"] = (agg["total_converted"] / agg["total_calls"]).round(4)
    agg["aca_eligible_rate"] = (agg["aca_eligible_count"] / agg["total_calls"]).round(4)

    # Product type breakdown
    if "product_type" in df.columns:
        prod_counts = (
            df.groupby(["campaign_id", "call_month", "product_type"])
            .size().unstack(fill_value=0)
        )
        prod_counts.columns = [f"product_{c}" for c in prod_counts.columns]
        agg = agg.merge(prod_counts.reset_index(), on=["campaign_id", "call_month"], how="left")

    _write_gold(agg, "gold_insurance_kpis")
    pipeline_log("GOLD", "gold_insurance_kpis", len(df), len(agg))
    return agg


# ---------------------------------------------------------------------------
# 4. Healthcare Domain KPIs
# ---------------------------------------------------------------------------

def gold_healthcare_kpis() -> pd.DataFrame:
    df = _silver("silver_healthcare")
    if df.empty:
        return pd.DataFrame()

    df["started_at"] = pd.to_datetime(df["started_at"], utc=True, errors="coerce")
    df["call_month"] = df["started_at"].dt.tz_localize(None).dt.to_period("M").astype(str)

    agg = df.groupby(["campaign_id", "call_month"]).agg(
        total_calls=("call_id", "count"),
        total_appointments_scheduled=("appointment_scheduled", "sum"),
        total_converted=("is_converted", "sum"),
        avg_sentiment=("sentiment_score", "mean"),
        webhook_sent_count=("webhook_sent", lambda x: pd.to_numeric(
            x.map({True: 1, False: 0}), errors="coerce").sum()),
        confirmation_email_count=("confirmation_email_sent", lambda x: pd.to_numeric(
            x.map({True: 1, False: 0}), errors="coerce").sum()),
    ).reset_index()

    agg["conversion_rate"] = (agg["total_converted"] / agg["total_calls"]).round(4)
    agg["appointment_rate"] = (
        agg["total_appointments_scheduled"] / agg["total_calls"]
    ).round(4)

    if "specialty" in df.columns:
        spec_counts = (
            df.dropna(subset=["specialty"])
            .groupby(["campaign_id", "call_month", "specialty"])
            .size().unstack(fill_value=0)
        )
        spec_counts.columns = [f"spec_{c.lower().replace(' ','_')}" for c in spec_counts.columns]
        agg = agg.merge(spec_counts.reset_index(), on=["campaign_id", "call_month"], how="left")

    _write_gold(agg, "gold_healthcare_kpis")
    pipeline_log("GOLD", "gold_healthcare_kpis", len(df), len(agg))
    return agg


# ---------------------------------------------------------------------------
# 5. Real Estate Domain KPIs
# ---------------------------------------------------------------------------

def gold_realestate_kpis() -> pd.DataFrame:
    df = _silver("silver_realestate")
    if df.empty:
        return pd.DataFrame()

    df["started_at"] = pd.to_datetime(df["started_at"], utc=True, errors="coerce")
    df["call_month"] = df["started_at"].dt.tz_localize(None).dt.to_period("M").astype(str)

    agg = df.groupby(["campaign_id", "call_month"]).agg(
        total_calls=("call_id", "count"),
        total_qualified=("lead_qualified", "sum"),
        total_converted=("is_converted", "sum"),
        total_agent_matched=("agent_matched", lambda x: pd.to_numeric(
            x.map({True: 1, False: 0}), errors="coerce").sum()),
        avg_budget_min=("budget_min", lambda x: pd.to_numeric(x, errors="coerce").mean()),
        avg_budget_max=("budget_max", lambda x: pd.to_numeric(x, errors="coerce").mean()),
        avg_sentiment=("sentiment_score", "mean"),
    ).reset_index()

    agg["conversion_rate"] = (agg["total_converted"] / agg["total_calls"]).round(4)
    agg["qualification_rate"] = (agg["total_qualified"] / agg["total_calls"]).round(4)

    if "interest_type" in df.columns:
        type_counts = (
            df.dropna(subset=["interest_type"])
            .groupby(["campaign_id", "call_month", "interest_type"])
            .size().unstack(fill_value=0)
        )
        type_counts.columns = [f"lead_type_{c}" for c in type_counts.columns]
        agg = agg.merge(type_counts.reset_index(), on=["campaign_id", "call_month"], how="left")

    _write_gold(agg, "gold_realestate_kpis")
    pipeline_log("GOLD", "gold_realestate_kpis", len(df), len(agg))
    return agg


# ---------------------------------------------------------------------------
# 6. AR Sales Domain KPIs
# ---------------------------------------------------------------------------

def gold_ar_kpis() -> pd.DataFrame:
    df = _silver("silver_ar")
    if df.empty:
        return pd.DataFrame()

    df["started_at"] = pd.to_datetime(df["started_at"], utc=True, errors="coerce")
    df["call_month"] = df["started_at"].dt.tz_localize(None).dt.to_period("M").astype(str)

    # Numeric safety
    for col in ["original_balance", "settlement_amount", "settlement_pct"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    agg = df.groupby(["campaign_id", "call_month"]).agg(
        total_calls=("call_id", "count"),
        total_arrangements=("arrangement_made", "sum"),
        total_converted=("is_converted", "sum"),
        total_original_balance=("original_balance", "sum"),
        total_settlement_amount=("settlement_amount", "sum"),
        avg_settlement_pct=("settlement_pct", "mean"),
        avg_sentiment=("sentiment_score", "mean"),
        sol_expired_count=("sol_expired", lambda x: pd.to_numeric(
            x.map({True: 1, False: 0}), errors="coerce").sum()),
    ).reset_index()

    agg["conversion_rate"] = (agg["total_converted"] / agg["total_calls"]).round(4)
    agg["arrangement_rate"] = (agg["total_arrangements"] / agg["total_calls"]).round(4)
    agg["recovery_rate"] = (
        agg["total_settlement_amount"] / agg["total_original_balance"].replace(0, np.nan)
    ).round(4)
    agg["avg_settlement_pct"] = agg["avg_settlement_pct"].round(4)

    _write_gold(agg, "gold_ar_kpis")
    pipeline_log("GOLD", "gold_ar_kpis", len(df), len(agg))
    return agg


# ---------------------------------------------------------------------------
# 7. QA & Compliance Summary
# ---------------------------------------------------------------------------

def gold_qa_compliance() -> pd.DataFrame:
    calls = _silver("silver_calls_all")
    qa = _silver("silver_qa_reviews")
    if calls.empty:
        return pd.DataFrame()

    calls["started_at"] = pd.to_datetime(calls["started_at"], utc=True, errors="coerce")
    calls["call_month"] = calls["started_at"].dt.tz_localize(None).dt.to_period("M").astype(str)

    compliance_agg = calls.groupby(["campaign_id", "vertical", "call_month"]).agg(
        total_calls=("call_id", "count"),
        compliance_flags=("is_compliance_issue", "sum"),
        compliance_flag_rate=("is_compliance_issue", "mean"),
    ).reset_index()

    if not qa.empty:
        qa["reviewed_at"] = pd.to_datetime(qa["reviewed_at"], utc=True, errors="coerce")
        qa_agg = qa.groupby("agent_id").agg(
            total_reviews=("qa_review_id", "count"),
            avg_qa_score=("total_score", "mean"),
            min_qa_score=("total_score", "min"),
            max_qa_score=("total_score", "max"),
        ).reset_index()
        _write_gold(qa_agg, "gold_qa_agent_scores")
        pipeline_log("GOLD", "gold_qa_agent_scores", len(qa), len(qa_agg))

    _write_gold(compliance_agg, "gold_compliance_summary")
    pipeline_log("GOLD", "gold_compliance_summary", len(calls), len(compliance_agg))
    return compliance_agg


# ---------------------------------------------------------------------------
# 8. ML Feature Store (Gold enriched)
# ---------------------------------------------------------------------------

def gold_ml_feature_store() -> pd.DataFrame:
    """Enrich raw ML features with Silver-computed call aggregates."""
    from pathlib import Path as _P
    raw_path = _P("output/ml_features.csv")
    if not raw_path.exists():
        return pd.DataFrame()

    features = pd.read_csv(raw_path, low_memory=False)
    calls = _silver("silver_calls_all")

    if not calls.empty:
        calls["is_converted"] = calls["disposition"].isin(["Interested", "Transfer"])
        call_agg = calls.groupby("lead_id").agg(
            n_calls=("call_id", "count"),
            max_sentiment=("sentiment_score", "max"),
            min_sentiment=("sentiment_score", "min"),
            std_sentiment=("sentiment_score", "std"),
            avg_duration=("duration_seconds", "mean"),
            any_compliance_flag=("is_compliance_issue", "max"),
            n_dnc_dispositions=("disposition", lambda x: (x == "DNC").sum()),
            n_callbacks=("disposition", lambda x: (x == "Callback").sum()),
            n_no_answers=("disposition", lambda x: (x == "NoAnswer").sum()),
            distinct_agents=("agent_id", "nunique"),
        ).reset_index()
        call_agg.columns = ["lead_id"] + [f"feat_{c}" for c in call_agg.columns[1:]]
        features = features.merge(call_agg, on="lead_id", how="left")

    # Encode categoricals
    for col in ["vertical", "state"]:
        if col in features.columns:
            features[f"{col}_enc"] = pd.Categorical(features[col]).codes

    _write_gold(features, "gold_ml_feature_store")
    pipeline_log("GOLD", "gold_ml_feature_store", len(features), len(features))
    return features


# ---------------------------------------------------------------------------
# 9. Dialer Performance Fact
# ---------------------------------------------------------------------------

def gold_dialer_performance() -> pd.DataFrame:
    calls = _silver("silver_calls_all")
    campaigns = _silver("dim_campaigns")
    if calls.empty:
        return pd.DataFrame()

    calls["started_at"] = pd.to_datetime(calls["started_at"], utc=True, errors="coerce")
    calls["call_date"] = calls["started_at"].dt.date.astype(str)
    calls["call_hour"] = calls["started_at"].dt.hour

    agg = calls.groupby(["campaign_id", "call_date"]).agg(
        total_dials=("call_id", "count"),
        answered=("disposition", lambda x: (x != "NoAnswer").sum()),
        abandoned=("disposition", lambda x: (x == "NoAnswer").sum()),
        avg_handle_time=("duration_seconds", "mean"),
        peak_hour=("call_hour", lambda x: x.mode().iloc[0] if len(x) > 0 else None),
        active_agents=("agent_id", "nunique"),
    ).reset_index()

    agg["answer_rate"] = (agg["answered"] / agg["total_dials"]).round(4)
    agg["abandon_rate"] = (agg["abandoned"] / agg["total_dials"]).round(4)
    agg["above_fdcpa_abandon_threshold"] = agg["abandon_rate"] > 0.03

    if not campaigns.empty:
        agg = agg.merge(
            campaigns[["campaign_id", "vertical", "dialing_mode"]],
            on="campaign_id", how="left",
        )

    _write_gold(agg, "gold_dialer_performance")
    pipeline_log("GOLD", "gold_dialer_performance", len(calls), len(agg))
    return agg


# ---------------------------------------------------------------------------
# Gold Run
# ---------------------------------------------------------------------------

def run_gold() -> None:
    print("\n" + "=" * 70)
    print("  GOLD LAYER — Business Aggregates")
    print("=" * 70)
    gold_campaign_kpis()
    gold_agent_performance()
    gold_insurance_kpis()
    gold_healthcare_kpis()
    gold_realestate_kpis()
    gold_ar_kpis()
    gold_qa_compliance()
    gold_ml_feature_store()
    gold_dialer_performance()


if __name__ == "__main__":
    run_gold()
