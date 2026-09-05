"""
Schema contract validation — checks column presence and basic type constraints.
Returns (valid_df, invalid_df) tuple for DLQ routing.
"""
from __future__ import annotations

import pandas as pd

# Required columns per raw source table
SCHEMAS: dict[str, list[str]] = {
    "leads": [
        "lead_id", "campaign_id", "vertical", "first_name", "last_name",
        "phone_e164", "state", "status", "dnc_flagged", "created_at",
    ],
    "calls": [
        "call_id", "lead_id", "agent_id", "campaign_id", "vertical",
        "started_at", "ended_at", "duration_seconds", "disposition",
    ],
    "agents": [
        "agent_id", "first_name", "last_name", "email", "role",
        "performance_tier", "base_conversion_rate", "hire_date",
    ],
    "campaigns": [
        "campaign_id", "name", "vertical", "client_id",
        "dialing_mode", "status", "created_at",
    ],
    "qa_reviews": [
        "qa_review_id", "call_id", "agent_id", "reviewer_id",
        "scores", "total_score", "feedback", "reviewed_at",
    ],
    "insurance_qualifications": [
        "qualification_id", "call_id", "lead_id",
        "product_type", "coverage_type", "date_of_birth",
    ],
    "appointments": [
        "appointment_id", "call_id", "lead_id", "patient_name",
        "appointment_date", "provider_name", "facility", "payer_id", "member_id",
    ],
    "realestate_qualifications": [
        "qualification_id", "call_id", "lead_id",
        "interest_type", "target_state", "budget_min", "budget_max",
    ],
    "payment_arrangements": [
        "arrangement_id", "call_id", "lead_id",
        "original_balance", "settlement_amount", "payment_schedule",
        "payment_method", "verbal_confirmation",
    ],
    "pipeline_events": [
        "event_id", "event_type", "schema_version",
        "source_call_id", "emitted_at", "status",
    ],
}

ENUM_CHECKS: dict[str, dict[str, set]] = {
    "leads": {
        "vertical": {"Insurance", "Healthcare", "RealEstate", "AR"},
        "status": {"New", "Dialing", "Contacted", "Dispositioned", "Recycled", "Closed"},
    },
    "calls": {
        "disposition": {
            "Interested", "NotInterested", "Callback",
            "DNC", "Transfer", "NoAnswer", "Voicemail",
        },
        "vertical": {"Insurance", "Healthcare", "RealEstate", "AR"},
    },
    "campaigns": {
        "dialing_mode": {"Preview", "Progressive", "Predictive"},
        "status": {"Draft", "Active", "Paused", "Closed"},
        "vertical": {"Insurance", "Healthcare", "RealEstate", "AR"},
    },
    "agents": {
        "role": {
            "Agent", "Team Lead", "Supervisor", "QA Manager",
            "Campaign Manager", "Data Engineer", "Data Scientist", "Admin",
        },
        "performance_tier": {"high", "mid", "low"},
    },
}


def validate(df: pd.DataFrame, table: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Returns (valid_df, invalid_df).
    invalid_df contains rows that failed schema or enum checks,
    with an extra '_validation_errors' column describing the failure.
    """
    required = SCHEMAS.get(table, [])
    enum_rules = ENUM_CHECKS.get(table, {})

    errors: list[str] = []
    invalid_mask = pd.Series([False] * len(df), index=df.index)
    error_notes = pd.Series([""] * len(df), index=df.index)

    # Missing required columns — entire dataframe is invalid
    missing_cols = [c for c in required if c not in df.columns]
    if missing_cols:
        df["_validation_errors"] = f"Missing columns: {missing_cols}"
        return pd.DataFrame(columns=df.columns), df

    # Null checks on required columns
    for col in required:
        null_mask = df[col].isnull()
        invalid_mask |= null_mask
        error_notes = error_notes.where(~null_mask, error_notes + f"null:{col}; ")

    # Enum value checks
    for col, valid_vals in enum_rules.items():
        if col not in df.columns:
            continue
        bad_mask = ~df[col].isin(valid_vals) & df[col].notna()
        invalid_mask |= bad_mask
        error_notes = error_notes.where(~bad_mask, error_notes + f"invalid_enum:{col}; ")

    valid_df = df[~invalid_mask].copy()
    invalid_df = df[invalid_mask].copy()
    invalid_df["_validation_errors"] = error_notes[invalid_mask]

    return valid_df.reset_index(drop=True), invalid_df.reset_index(drop=True)
