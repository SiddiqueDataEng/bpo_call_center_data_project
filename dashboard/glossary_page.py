"""Glossary & Definitions page — terms, metrics, data examples from the live lakehouse."""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

GOLD = Path(__file__).parent.parent / "lakehouse" / "gold"

CATEGORIES = {
    "BPO Operations": [
        {
            "term": "Agent",
            "abbr": None,
            "definition": "A call center employee who makes or receives calls on behalf of a campaign.",
            "example": "An agent dials 80 leads per day across the Insurance vertical, spending ~3.5 hours on live calls.",
            "metric": None,
            "table": "gold_agent_performance",
            "field": "avg_conversion_rate",
            "chart_label": "Avg Conversion Rate by Performance Tier",
        },
        {
            "term": "Campaign",
            "abbr": None,
            "definition": "A structured outbound calling effort targeting a list of leads for a specific vertical and client.",
            "example": "Insurance Campaign 1 ran for 90 days targeting 1,200 health insurance leads with Predictive dialing.",
            "metric": "Active / Closed",
            "table": "gold_campaign_kpis",
            "field": "total_calls",
            "chart_label": "Total Calls by Campaign",
        },
        {
            "term": "Disposition",
            "abbr": None,
            "definition": "The outcome classification assigned to a call after it ends.",
            "example": "Possible dispositions: Interested, Not Interested, Callback, DNC, Transfer, No Answer, Voicemail.",
            "metric": "7 disposition types",
            "table": None,
            "field": None,
            "chart_label": None,
        },
        {
            "term": "Conversion Rate",
            "abbr": "CR",
            "definition": "Ratio of calls resulting in a positive outcome (Interested or Transfer) to total calls made.",
            "example": "A healthcare campaign with 500 calls and 130 positive outcomes has a 26% conversion rate.",
            "metric": "= (Interested + Transfer) / Total Calls",
            "table": "gold_campaign_kpis",
            "field": "conversion_rate",
            "chart_label": "Conversion Rate by Vertical",
        },
        {
            "term": "Talk Time",
            "abbr": None,
            "definition": "Total duration an agent spends on live calls, measured in minutes or hours.",
            "example": "An agent with 9 talk hours handled 150 calls averaging 3.6 minutes each.",
            "metric": "Total seconds / 3600 = hours",
            "table": "gold_agent_performance",
            "field": "total_talk_hours",
            "chart_label": "Talk Hours by Agent Tier",
        },
        {
            "term": "Average Handle Time",
            "abbr": "AHT",
            "definition": "Average duration per call including talk time and any post-call work.",
            "example": "An AHT of 169 seconds (2.8 min) on an AR campaign indicates short negotiation calls.",
            "metric": "= Total Call Seconds / Total Calls",
            "table": "gold_campaign_kpis",
            "field": "avg_duration_seconds",
            "chart_label": "Avg Duration (seconds) by Vertical",
        },
        {
            "term": "QA Score",
            "abbr": None,
            "definition": "Numeric quality score (1.0–5.0) assigned by a QA reviewer across weighted rubric categories.",
            "example": "Rubric categories: Opening, Script Compliance, Product Knowledge, Objection Handling, Closing.",
            "metric": "Scale: 1.0 (Poor) → 5.0 (Excellent)",
            "table": "gold_qa_agent_scores",
            "field": "avg_qa_score",
            "chart_label": "QA Score Distribution",
        },
    ],
    "Compliance & Regulation": [
        {
            "term": "Do Not Call",
            "abbr": "DNC",
            "definition": "A registry of phone numbers that must not be contacted for telemarketing purposes.",
            "example": "A lead flagged as DNC is blocked from all outbound campaigns and logged with a suppression timestamp.",
            "metric": "DNC Rate = DNC Calls / Total Calls",
            "table": "gold_campaign_kpis",
            "field": "dnc_rate",
            "chart_label": "DNC Rate by Campaign",
        },
        {
            "term": "Telephone Consumer Protection Act",
            "abbr": "TCPA",
            "definition": "USA federal law governing telemarketing calls, auto-dialers, and consent requirements.",
            "example": "TCPA requires written consent before using predictive dialers to contact mobile numbers.",
            "metric": None,
            "table": None,
            "field": None,
            "chart_label": None,
        },
        {
            "term": "Fair Debt Collection Practices Act",
            "abbr": "FDCPA",
            "definition": "USA federal law governing debt collection, including contact hour restrictions (8AM–9PM local).",
            "example": "An AR campaign dialing a debtor in California at 9:30 PM PST violates FDCPA hours.",
            "metric": "Abandon Rate Limit: ≤ 3%",
            "table": "gold_dialer_performance",
            "field": "abandon_rate",
            "chart_label": "Abandon Rate vs 3% FDCPA Limit",
        },
        {
            "term": "Health Insurance Portability and Accountability Act",
            "abbr": "HIPAA",
            "definition": "USA federal law protecting patient health information (PHI). All healthcare PII is AES-256 encrypted.",
            "example": "Patient name, date of birth, and member ID are encrypted at rest and masked in agent views.",
            "metric": None,
            "table": None,
            "field": None,
            "chart_label": None,
        },
        {
            "term": "Compliance Flag",
            "abbr": None,
            "definition": "A call flagged by NLP analysis for containing a regulated keyword or phrase requiring mandatory QA review.",
            "example": "A call where the customer said 'cease and desist' is auto-flagged and routed for QA review.",
            "metric": "Flag Rate = Flagged Calls / Total Calls",
            "table": "gold_compliance_summary",
            "field": "compliance_flag_rate",
            "chart_label": "Compliance Flag Rate by Vertical",
        },
        {
            "term": "Statute of Limitations",
            "abbr": "SOL",
            "definition": "The legal time limit within which a creditor can sue to collect a debt, varying by US state.",
            "example": "California SOL on credit card debt is 4 years. A 5-year-old account has an expired SOL.",
            "metric": "Range: 3–10 years depending on state",
            "table": None,
            "field": None,
            "chart_label": None,
        },
    ],
    "Dialers & Telephony": [
        {
            "term": "Predictive Dialer",
            "abbr": None,
            "definition": "An algorithm-driven dialer that dials multiple numbers simultaneously and connects answered calls to available agents.",
            "example": "With 10 agents and a 2.5x dial ratio, the dialer calls 25 numbers every 30 seconds.",
            "metric": "Abandon Rate must stay ≤ 3%",
            "table": "gold_dialer_performance",
            "field": "total_dials",
            "chart_label": "Daily Dials by Dialing Mode",
        },
        {
            "term": "Progressive Dialer",
            "abbr": None,
            "definition": "Dials one number per available agent — safer than Predictive, slower throughput.",
            "example": "Progressive dialing ensures every answered call has an agent ready — no abandoned calls.",
            "metric": "1:1 dial-to-agent ratio",
            "table": None,
            "field": None,
            "chart_label": None,
        },
        {
            "term": "Preview Dialer",
            "abbr": None,
            "definition": "Agent reviews lead information before manually initiating the call.",
            "example": "Used for high-value AR accounts where agents need context before dialing.",
            "metric": "Agent-controlled",
            "table": None,
            "field": None,
            "chart_label": None,
        },
        {
            "term": "Abandon Rate",
            "abbr": None,
            "definition": "Percentage of dialed calls where a person answers but no agent is available — the call is dropped.",
            "example": "If 100 calls are answered and 4 have no agent available, the abandon rate is 4% — above FDCPA limit.",
            "metric": "= Abandoned / Answered × 100",
            "table": "gold_dialer_performance",
            "field": "abandon_rate",
            "chart_label": "Abandon Rate Trend",
        },
        {
            "term": "Answer Rate",
            "abbr": None,
            "definition": "Percentage of dialed numbers that are answered by a live person.",
            "example": "An answer rate of 35% means 35 of 100 dialed numbers were answered.",
            "metric": "= Answered / Total Dials × 100",
            "table": "gold_dialer_performance",
            "field": "answer_rate",
            "chart_label": "Answer Rate by Dialing Mode",
        },
    ],
    "Data Engineering": [
        {
            "term": "Medallion Architecture",
            "abbr": None,
            "definition": "A layered data lakehouse pattern: Bronze (raw) → Silver (cleaned) → Gold (aggregated).",
            "example": "Raw call events land in Bronze, get validated in Silver, and become campaign KPIs in Gold.",
            "metric": "3 layers: Bronze, Silver, Gold",
            "table": None,
            "field": None,
            "chart_label": None,
        },
        {
            "term": "Dead Letter Queue",
            "abbr": "DLQ",
            "definition": "A storage area for events that failed schema validation during pipeline processing.",
            "example": "An insurance qualification record missing 'date_of_birth' fails validation and lands in the DLQ.",
            "metric": None,
            "table": None,
            "field": None,
            "chart_label": None,
        },
        {
            "term": "Extract, Transform, Load",
            "abbr": "ETL",
            "definition": "A data integration process: extract from source, transform/clean, load into destination.",
            "example": "Raw call CSVs → Bronze parquet → Silver enriched joins → Gold campaign KPIs.",
            "metric": None,
            "table": None,
            "field": None,
            "chart_label": None,
        },
        {
            "term": "Data Mesh",
            "abbr": None,
            "definition": "A federated data architecture where each business domain owns its data pipeline and products.",
            "example": "Insurance, Healthcare, Real Estate, and AR each own their Bronze→Gold pipeline in this platform.",
            "metric": "4 domain data products",
            "table": None,
            "field": None,
            "chart_label": None,
        },
        {
            "term": "E.164",
            "abbr": None,
            "definition": "International telephone number format: + followed by country code and subscriber number.",
            "example": "+12125551234 — US number (country code 1, area code 212, number 5551234).",
            "metric": "Max 15 digits",
            "table": None,
            "field": None,
            "chart_label": None,
        },
    ],
    "ML / AI": [
        {
            "term": "Lead Score",
            "abbr": None,
            "definition": "A propensity score (0–100) predicting the likelihood a lead will convert, generated by an ML model.",
            "example": "A score of 85 means the model predicts an 85% probability of conversion for that lead.",
            "metric": "Range: 0 (unlikely) → 100 (highly likely)",
            "table": "gold_ml_feature_store",
            "field": "predicted_score",
            "chart_label": "Lead Score Distribution",
        },
        {
            "term": "AUC-ROC",
            "abbr": None,
            "definition": "Area Under the Receiver Operating Characteristic curve — measures model discrimination ability.",
            "example": "Our Healthcare model achieves AUC=0.989, meaning it correctly ranks positive leads almost perfectly.",
            "metric": "Range: 0.5 (random) → 1.0 (perfect)",
            "table": None,
            "field": None,
            "chart_label": None,
        },
        {
            "term": "Model Drift",
            "abbr": None,
            "definition": "Degradation in model performance over time as the real-world data distribution shifts from training data.",
            "example": "If AR debt balances rise significantly, a model trained on older data under-predicts conversions.",
            "metric": "Detected via KS-test (numerical) and chi-squared (categorical)",
            "table": None,
            "field": None,
            "chart_label": None,
        },
        {
            "term": "Sentiment Score",
            "abbr": None,
            "definition": "A float value from -1.0 (very negative) to +1.0 (very positive) extracted from call transcripts via NLP.",
            "example": "A DNC call scores -0.70 (hostile). An interested insurance lead scores +0.60 (positive).",
            "metric": "Range: -1.0 → +1.0",
            "table": "gold_ml_feature_store",
            "field": "avg_sentiment_score",
            "chart_label": "Sentiment Score by Vertical",
        },
        {
            "term": "Gradient Boosting Machine",
            "abbr": "GBM",
            "definition": "An ensemble ML algorithm that builds decision trees sequentially to minimize prediction error.",
            "example": "Used as the per-vertical propensity model with 200 estimators and 0.05 learning rate.",
            "metric": None,
            "table": None,
            "field": None,
            "chart_label": None,
        },
    ],
    "Vertical Domains": [
        {
            "term": "ACA Eligibility",
            "abbr": None,
            "definition": "Whether a person qualifies for Affordable Care Act health insurance subsidies based on income and household size.",
            "example": "A household of 4 with income ≤ $120,000 (400% FPL) qualifies for ACA subsidies.",
            "metric": "FPL thresholds: 1-person=$14,580 → 8-person=$50,560",
            "table": "gold_insurance_kpis",
            "field": "aca_eligible_rate",
            "chart_label": "ACA Eligibility Rate by Month",
        },
        {
            "term": "Benefits Verification",
            "abbr": None,
            "definition": "The process of confirming a patient's insurance coverage details with the payer before scheduling.",
            "example": "Checking if BCBS plan MBR-12345678 covers orthopedic appointments at Sunrise Medical Center.",
            "metric": "Requires: Payer ID, Member ID, Date of Birth",
            "table": "gold_healthcare_kpis",
            "field": "appointment_rate",
            "chart_label": "Appointment Rate Trend",
        },
        {
            "term": "Payment Arrangement",
            "abbr": None,
            "definition": "A negotiated debt repayment agreement including settlement amount, schedule, and payment method.",
            "example": "A $5,000 debt settled for $3,200 in 6 monthly ACH payments — 64% settlement rate.",
            "metric": "Settlement % = Settlement Amount / Original Balance",
            "table": "gold_ar_kpis",
            "field": "avg_settlement_pct",
            "chart_label": "Avg Settlement % Trend",
        },
        {
            "term": "Warm Transfer",
            "abbr": None,
            "definition": "A call transfer where the originating agent briefs the receiving agent before connecting the customer.",
            "example": "An insurance agent qualifies a lead then warm-transfers to a licensed broker to close the sale.",
            "metric": None,
            "table": "gold_insurance_kpis",
            "field": "total_transfers",
            "chart_label": "Warm Transfers by Month",
        },
    ],
}


@st.cache_data
def _load(table: str) -> pd.DataFrame:
    p = GOLD / f"{table}.parquet"
    return pd.read_parquet(p) if p.exists() else pd.DataFrame()


def _live_example(term_def: dict) -> None:
    """Show a live data snippet and mini-chart for a term if available."""
    table = term_def.get("table")
    field = term_def.get("field")
    label = term_def.get("chart_label")
    if not table or not field:
        return

    df = _load(table)
    if df.empty or field not in df.columns:
        return

    # Choose the best grouping column
    str_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    group_col = None
    for candidate in ["vertical", "performance_tier", "dialing_mode",
                      "call_month", "name", "agent_id"]:
        if candidate in df.columns:
            group_col = candidate
            break

    if group_col and group_col in df.columns:
        agg = df.groupby(group_col)[field].mean().reset_index()
        agg.columns = [group_col, field]
        agg[field] = agg[field].round(4)
        if len(agg) > 1:
            fig = px.bar(
                agg.head(12), x=group_col, y=field,
                color=field, color_continuous_scale="Blues",
                title=label,
                labels={field: field.replace("_", " ").title(),
                        group_col: group_col.replace("_", " ").title()},
            )
            fig.update_layout(
                height=220, showlegend=False,
                margin=dict(t=32, b=8, l=8, r=8),
                plot_bgcolor="white",
                coloraxis_showscale=False,
            )
            st.plotly_chart(fig, use_container_width=True)
        # Show sample row
        sample = df[[group_col, field]].dropna().head(3)
        st.caption(f"Live data sample from `{table}`:")
        st.dataframe(sample, use_container_width=True,
                     hide_index=True, height=100)
    else:
        # Just show histogram of the field
        vals = df[field].dropna()
        if len(vals) > 0:
            fig = px.histogram(vals, nbins=15, title=label,
                               color_discrete_sequence=["#1A56DB"])
            fig.update_layout(height=200, margin=dict(t=32, b=8, l=8, r=8),
                              plot_bgcolor="white", showlegend=False)
            st.plotly_chart(fig, use_container_width=True)


def render_glossary_page() -> None:
    st.markdown("# 📖 Glossary & Definitions")
    st.markdown(
        "*Every term used in this platform — with plain-English definitions, "
        "formulas, examples, and live data from the lakehouse.*"
    )
    st.markdown("---")

    # Search bar
    search = st.text_input(
        "🔍 Search terms",
        placeholder="Type a term, abbreviation, or keyword…",
        key="gloss_search",
    )
    search_lower = search.strip().lower()

    # Category filter
    all_cats = ["All Categories"] + list(CATEGORIES.keys())
    selected_cat = st.selectbox("Filter by category", all_cats, key="gloss_cat")

    st.markdown("---")

    # Term count summary
    total_terms = sum(len(v) for v in CATEGORIES.values())
    cols_summary = st.columns(len(CATEGORIES))
    for i, (cat, terms) in enumerate(CATEGORIES.items()):
        icon = {
            "BPO Operations": "📞",
            "Compliance & Regulation": "⚖️",
            "Dialers & Telephony": "📡",
            "Data Engineering": "🗄️",
            "ML / AI": "🤖",
            "Vertical Domains": "🏢",
        }.get(cat, "📌")
        cols_summary[i].metric(f"{icon} {cat}", f"{len(terms)} terms")

    st.markdown("---")

    shown = 0
    for cat, terms in CATEGORIES.items():
        if selected_cat != "All Categories" and cat != selected_cat:
            continue

        filtered = terms
        if search_lower:
            filtered = [
                t for t in terms
                if search_lower in t["term"].lower()
                or search_lower in t["definition"].lower()
                or search_lower in (t.get("abbr") or "").lower()
                or search_lower in t["example"].lower()
            ]
        if not filtered:
            continue

        icon = {
            "BPO Operations": "📞",
            "Compliance & Regulation": "⚖️",
            "Dialers & Telephony": "📡",
            "Data Engineering": "🗄️",
            "ML / AI": "🤖",
            "Vertical Domains": "🏢",
        }.get(cat, "📌")

        st.markdown(f"## {icon} {cat}")

        for term_def in filtered:
            shown += 1
            term = term_def["term"]
            abbr = term_def.get("abbr")
            title = f"**{term}**" + (f" ({abbr})" if abbr else "")

            has_chart = bool(term_def.get("table"))
            expander_label = f"{'📊 ' if has_chart else ''}{term}" + (f" ({abbr})" if abbr else "")

            with st.expander(expander_label, expanded=False):
                if has_chart:
                    col1, col2 = st.columns([3, 2])
                else:
                    col1 = st.container()
                    col2 = None

                with col1:
                    st.markdown(f"### {title}")
                    st.markdown(term_def["definition"])

                    if term_def.get("metric"):
                        st.markdown(
                            f'<div style="background:#EFF6FF;border-left:4px solid #1A56DB;'
                            f'padding:8px 12px;border-radius:4px;font-family:monospace;'
                            f'font-size:13px;margin:8px 0">{term_def["metric"]}</div>',
                            unsafe_allow_html=True,
                        )

                    st.markdown(
                        f'<div style="background:#F0FDF4;border-left:4px solid #057A55;'
                        f'padding:8px 12px;border-radius:4px;font-size:13px;margin:8px 0">'
                        f'<strong>Example:</strong> {term_def["example"]}</div>',
                        unsafe_allow_html=True,
                    )

                if has_chart and col2 is not None:
                    with col2:
                        _live_example(term_def)

        st.markdown("---")

    if shown == 0:
        st.warning(f"No terms found matching **'{search}'**. Try a different keyword.")
    else:
        st.caption(f"Showing {shown} of {total_terms} terms.")
