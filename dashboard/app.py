"""
BPO Platform Intelligence Dashboard
====================================
Professional Streamlit dashboard with:
  - Executive Summary
  - Operations Center (real-time KPIs)
  - Vertical Deep-Dives (Insurance / Healthcare / Real Estate / AR)
  - Agent & QA Performance
  - Compliance & Risk Monitor
  - ML / AI Insights
  - Data Mesh Health
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dashboard.sql_page import render_sql_page
from dashboard.glossary_page import render_glossary_page
from dashboard.ai_chat_page import render_ai_chat_page

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="BPO Intelligence Platform",
    page_icon="📞",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent.parent
GOLD = BASE / "lakehouse" / "gold"
SILVER = BASE / "lakehouse" / "silver"
BRONZE = BASE / "lakehouse" / "bronze"
ML_REPORT = BASE / "ml" / "reports" / "model_report.json"
FI_PATH = BASE / "ml" / "reports" / "feature_importance.csv"

# ── Brand palette ─────────────────────────────────────────────────────────────
COLORS = {
    "primary":    "#1A56DB",
    "success":    "#057A55",
    "warning":    "#C27803",
    "danger":     "#E02424",
    "neutral":    "#6B7280",
    "bg":         "#F9FAFB",
    "Insurance":  "#3B82F6",
    "Healthcare": "#10B981",
    "RealEstate": "#F59E0B",
    "AR":         "#EF4444",
}

VERTICAL_ICONS = {
    "Insurance": "🛡️",
    "Healthcare": "🏥",
    "RealEstate": "🏠",
    "AR": "💳",
}

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  [data-testid="stSidebar"] { background: #111827; }
  [data-testid="stSidebar"] * { color: #F9FAFB !important; }
  .metric-card {
    background: white; border-radius: 12px; padding: 20px 24px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08); border-left: 4px solid #1A56DB;
    margin-bottom: 8px;
  }
  .metric-card.green  { border-color: #057A55; }
  .metric-card.red    { border-color: #E02424; }
  .metric-card.amber  { border-color: #C27803; }
  .metric-label { font-size: 12px; color: #6B7280; font-weight: 600;
                  text-transform: uppercase; letter-spacing: .05em; }
  .metric-value { font-size: 28px; font-weight: 700; color: #111827;
                  line-height: 1.2; }
  .metric-delta { font-size: 13px; margin-top: 2px; }
  .section-title { font-size: 22px; font-weight: 700; color: #111827;
                   margin: 16px 0 4px; }
  .section-sub   { font-size: 14px; color: #6B7280; margin-bottom: 16px; }
  div[data-testid="stMarkdownContainer"] h1 { color: #111827; }
  .stTabs [data-baseweb="tab"] { font-weight: 600; font-size: 14px; }
  .stTabs [aria-selected="true"] { color: #1A56DB !important; }
</style>
""", unsafe_allow_html=True)


# ── Data loaders ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load(name: str, layer: str = "gold") -> pd.DataFrame:
    dirs = {"gold": GOLD, "silver": SILVER, "bronze": BRONZE}
    p = dirs[layer] / f"{name}.parquet"
    return pd.read_parquet(p) if p.exists() else pd.DataFrame()


@st.cache_data
def load_ml_report() -> dict:
    if ML_REPORT.exists():
        return json.loads(ML_REPORT.read_text())
    return {}


@st.cache_data
def load_feature_importance() -> pd.DataFrame:
    return pd.read_csv(FI_PATH) if FI_PATH.exists() else pd.DataFrame()


def card(label: str, value: str, delta: str = "", color: str = "") -> str:
    cls = f"metric-card {color}"
    delta_html = (f'<div class="metric-delta" style="color:'
                  f'{"#057A55" if "▲" in delta else "#E02424" if "▼" in delta else "#6B7280"}">'
                  f'{delta}</div>') if delta else ""
    return (f'<div class="{cls}"><div class="metric-label">{label}</div>'
            f'<div class="metric-value">{value}</div>{delta_html}</div>')


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📞 BPO Intelligence")
    st.markdown("---")
    page = st.radio("Navigation", [
        "🏠 Executive Summary",
        "📊 Operations Center",
        "🛡️ Insurance",
        "🏥 Healthcare",
        "🏠 Real Estate",
        "💳 AR Sales",
        "👥 Agent & QA",
        "⚠️ Compliance & Risk",
        "🤖 ML / AI Insights",
        "🔍 SQL & AI Query Studio",
        "💬 AI Data Assistant",
        "📖 Glossary & Definitions",
        "🗄️ Data Mesh Health",
    ], label_visibility="collapsed")
    st.markdown("---")
    st.caption("Pakistan BPO Platform v1.0")
    st.caption("Powered by Azure + Data Mesh")

# ── Load core data ────────────────────────────────────────────────────────────
camp   = load("gold_campaign_kpis")
dial   = load("gold_dialer_performance")
agent  = load("gold_agent_performance")
qa_sc  = load("gold_qa_agent_scores")
comp   = load("gold_compliance_summary")
ml_feat = load("gold_ml_feature_store")
ins_k  = load("gold_insurance_kpis")
hc_k   = load("gold_healthcare_kpis")
re_k   = load("gold_realestate_kpis")
ar_k   = load("gold_ar_kpis")

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: Executive Summary
# ─────────────────────────────────────────────────────────────────────────────
if "Executive" in page:
    st.markdown("# 🏢 Executive Summary")
    st.markdown("*Pakistan BPO Platform — Unified Performance Intelligence*")
    st.markdown("---")

    # Top KPI strip
    total_calls  = int(camp["total_calls"].sum()) if not camp.empty else 0
    total_conv   = int(camp["total_converted"].sum()) if not camp.empty else 0
    avg_conv     = camp["conversion_rate"].mean() if not camp.empty else 0
    total_talk   = camp["total_talk_minutes"].sum() / 60 if not camp.empty else 0
    total_comp   = int(camp["compliance_flags"].sum()) if not camp.empty else 0
    n_campaigns  = len(camp) if not camp.empty else 0

    cols = st.columns(6)
    kpis = [
        ("Total Calls", f"{total_calls:,}", "", ""),
        ("Conversions", f"{total_conv:,}", "", "green"),
        ("Avg Conv Rate", f"{avg_conv:.1%}", "", "green" if avg_conv > 0.15 else "amber"),
        ("Talk Hours", f"{total_talk:,.0f} h", "", ""),
        ("Compliance Flags", f"{total_comp:,}", "", "red" if total_comp > 100 else "amber"),
        ("Active Campaigns", f"{n_campaigns}", "", ""),
    ]
    for col, (lbl, val, delta, color) in zip(cols, kpis):
        col.markdown(card(lbl, val, delta, color), unsafe_allow_html=True)

    st.markdown("---")

    col1, col2 = st.columns([3, 2])
    with col1:
        st.markdown('<div class="section-title">Conversion Rate by Vertical</div>',
                    unsafe_allow_html=True)
        if not camp.empty:
            vg = camp.groupby("vertical").agg(
                total_calls=("total_calls", "sum"),
                total_converted=("total_converted", "sum"),
            ).reset_index()
            vg["conv_rate"] = vg["total_converted"] / vg["total_calls"]
            fig = px.bar(
                vg, x="vertical", y="conv_rate", color="vertical",
                color_discrete_map=COLORS, text_auto=".1%",
                labels={"conv_rate": "Conversion Rate", "vertical": "Vertical"},
            )
            fig.update_layout(showlegend=False, plot_bgcolor="white",
                              yaxis_tickformat=".0%", height=320)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown('<div class="section-title">Call Volume by Vertical</div>',
                    unsafe_allow_html=True)
        if not camp.empty:
            vg2 = camp.groupby("vertical")["total_calls"].sum().reset_index()
            fig2 = px.pie(
                vg2, names="vertical", values="total_calls",
                color="vertical", color_discrete_map=COLORS,
                hole=0.45,
            )
            fig2.update_traces(textposition="outside", textinfo="percent+label")
            fig2.update_layout(showlegend=False, height=320,
                               margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig2, use_container_width=True)

    # Monthly trend
    st.markdown('<div class="section-title">Monthly Call Volume & Conversions</div>',
                unsafe_allow_html=True)
    if not dial.empty:
        dial["call_date"] = pd.to_datetime(dial["call_date"], errors="coerce")
        dial["month"] = dial["call_date"].dt.to_period("M").astype(str)
        monthly = dial.groupby("month").agg(
            total_dials=("total_dials", "sum"),
            answered=("answered", "sum"),
        ).reset_index()
        fig3 = go.Figure()
        fig3.add_trace(go.Bar(x=monthly["month"], y=monthly["total_dials"],
                              name="Total Dials", marker_color="#BFDBFE"))
        fig3.add_trace(go.Bar(x=monthly["month"], y=monthly["answered"],
                              name="Answered", marker_color=COLORS["primary"]))
        fig3.update_layout(barmode="overlay", plot_bgcolor="white",
                           height=300, legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig3, use_container_width=True)

    # Campaign table
    st.markdown('<div class="section-title">Campaign Scorecard</div>', unsafe_allow_html=True)
    if not camp.empty:
        tbl = camp[["name", "vertical", "dialing_mode", "status",
                    "total_calls", "conversion_rate", "avg_sentiment",
                    "compliance_flags"]].copy()
        tbl["conversion_rate"] = (tbl["conversion_rate"] * 100).round(1).astype(str) + "%"
        tbl["avg_sentiment"] = tbl["avg_sentiment"].round(3)
        tbl.columns = ["Campaign", "Vertical", "Dialing Mode", "Status",
                       "Calls", "Conv Rate", "Avg Sentiment", "Compliance Flags"]
        st.dataframe(tbl, use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: Operations Center
# ─────────────────────────────────────────────────────────────────────────────
elif "Operations" in page:
    st.markdown("# 📊 Operations Center")
    st.markdown("*Dialer performance, answer rates, FDCPA compliance, and daily throughput*")
    st.markdown("---")

    if dial.empty:
        st.warning("No dialer data found.")
    else:
        dial["call_date"] = pd.to_datetime(dial["call_date"], errors="coerce")

        # KPIs
        total_dials = int(dial["total_dials"].sum())
        avg_answer  = dial["answer_rate"].mean()
        avg_abandon = dial["abandon_rate"].mean()
        fdcpa_flags = int(dial["above_fdcpa_abandon_threshold"].sum())

        cols = st.columns(4)
        cols[0].markdown(card("Total Dials", f"{total_dials:,}"), unsafe_allow_html=True)
        cols[1].markdown(card("Avg Answer Rate", f"{avg_answer:.1%}", color="green"),
                         unsafe_allow_html=True)
        cols[2].markdown(card("Avg Abandon Rate", f"{avg_abandon:.1%}",
                              color="red" if avg_abandon > 0.03 else "green"),
                         unsafe_allow_html=True)
        cols[3].markdown(card("FDCPA Abandon Violations", f"{fdcpa_flags:,}",
                              color="red" if fdcpa_flags > 0 else "green"),
                         unsafe_allow_html=True)

        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Daily Abandon Rate Trend")
            daily = dial.groupby("call_date").agg(
                abandon_rate=("abandon_rate", "mean"),
                total_dials=("total_dials", "sum"),
            ).reset_index()
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=daily["call_date"], y=daily["abandon_rate"],
                mode="lines", name="Abandon Rate", line=dict(color=COLORS["danger"], width=2),
                fill="tozeroy", fillcolor="rgba(224,36,36,0.08)",
            ))
            fig.add_hline(y=0.03, line_dash="dot", line_color=COLORS["warning"],
                          annotation_text="FDCPA 3% Limit")
            fig.update_layout(plot_bgcolor="white", height=300,
                              yaxis_tickformat=".0%",
                              xaxis_title="", yaxis_title="Abandon Rate")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("#### Dialing Mode Distribution")
            mode_df = dial.groupby("dialing_mode")["total_dials"].sum().reset_index()
            fig2 = px.pie(mode_df, names="dialing_mode", values="total_dials",
                          color_discrete_sequence=[COLORS["primary"], "#60A5FA", "#BFDBFE"],
                          hole=0.4)
            fig2.update_layout(height=300, showlegend=True,
                               margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown("#### Answer Rate by Vertical & Dialing Mode")
        vd = dial.groupby(["vertical", "dialing_mode"]).agg(
            answer_rate=("answer_rate", "mean"),
            total_dials=("total_dials", "sum"),
        ).reset_index()
        fig3 = px.bar(vd, x="vertical", y="answer_rate", color="dialing_mode",
                      barmode="group", text_auto=".0%",
                      color_discrete_sequence=[COLORS["primary"], "#60A5FA", "#BFDBFE"],
                      labels={"answer_rate": "Answer Rate", "vertical": "Vertical"})
        fig3.update_layout(plot_bgcolor="white", height=300,
                           yaxis_tickformat=".0%")
        st.plotly_chart(fig3, use_container_width=True)

        # Peak hours heatmap
        st.markdown("#### Peak Calling Hours by Vertical")
        dial["peak_hour"] = pd.to_numeric(dial["peak_hour"], errors="coerce")
        hour_df = dial.dropna(subset=["peak_hour"]).copy()
        hour_df["peak_hour"] = hour_df["peak_hour"].astype(int)
        heatmap_data = hour_df.groupby(["vertical", "peak_hour"])["total_dials"].sum().reset_index()
        pivot = heatmap_data.pivot(index="vertical", columns="peak_hour", values="total_dials").fillna(0)
        fig4 = px.imshow(pivot, color_continuous_scale="Blues",
                         labels=dict(x="Hour of Day", y="Vertical", color="Dials"),
                         aspect="auto")
        fig4.update_layout(height=280)
        st.plotly_chart(fig4, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: Insurance
# ─────────────────────────────────────────────────────────────────────────────
elif "Insurance" in page and "Real" not in page:
    st.markdown("# 🛡️ Insurance Vertical")
    st.markdown("*ACA eligibility, product mix, transfer pipeline, monthly trends*")
    st.markdown("---")

    if ins_k.empty:
        st.warning("No insurance data.")
    else:
        tc = int(ins_k["total_calls"].sum())
        tv = int(ins_k["total_converted"].sum())
        cr = tv / tc if tc else 0
        aca = ins_k["aca_eligible_count"].sum()
        aca_rate = aca / tc if tc else 0
        transfers = int(ins_k["total_transfers"].sum())

        cols = st.columns(5)
        metrics = [
            ("Total Calls", f"{tc:,}", ""),
            ("Converted", f"{tv:,}", "green"),
            ("Conv Rate", f"{cr:.1%}", "green" if cr > 0.15 else "amber"),
            ("ACA Eligible", f"{aca_rate:.1%}", ""),
            ("Warm Transfers", f"{transfers:,}", ""),
        ]
        for col, (l, v, c) in zip(cols, metrics):
            col.markdown(card(l, v, color=c), unsafe_allow_html=True)

        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Monthly Conversion Rate")
            monthly = ins_k.groupby("call_month").agg(
                total_calls=("total_calls", "sum"),
                total_converted=("total_converted", "sum"),
                avg_sentiment=("avg_sentiment", "mean"),
            ).reset_index()
            monthly["conv_rate"] = monthly["total_converted"] / monthly["total_calls"]
            fig = go.Figure()
            fig.add_trace(go.Bar(x=monthly["call_month"], y=monthly["total_calls"],
                                 name="Calls", marker_color="#BFDBFE", yaxis="y"))
            fig.add_trace(go.Scatter(x=monthly["call_month"], y=monthly["conv_rate"],
                                     name="Conv Rate", line=dict(color=COLORS["primary"], width=3),
                                     yaxis="y2", mode="lines+markers"))
            fig.update_layout(
                plot_bgcolor="white", height=320,
                yaxis=dict(title="Calls"),
                yaxis2=dict(title="Conv Rate", overlaying="y", side="right",
                            tickformat=".0%"),
                legend=dict(orientation="h", y=1.1),
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("#### Product Mix")
            prod_cols = [c for c in ins_k.columns if c.startswith("product_")]
            if prod_cols:
                prod_totals = ins_k[prod_cols].sum().reset_index()
                prod_totals.columns = ["product", "count"]
                prod_totals["product"] = prod_totals["product"].str.replace("product_", "").str.title()
                fig2 = px.pie(prod_totals, names="product", values="count",
                              color_discrete_sequence=px.colors.sequential.Blues_r,
                              hole=0.4)
                fig2.update_layout(height=320, margin=dict(t=10, b=10))
                st.plotly_chart(fig2, use_container_width=True)

        # ACA eligibility trend
        st.markdown("#### ACA Eligibility & Subsidy Rate Over Time")
        ins_k["aca_rate"] = ins_k["aca_eligible_count"] / ins_k["total_calls"]
        ins_k["subsidy_rate"] = ins_k["aca_subsidy_count"] / ins_k["total_calls"]
        monthly_aca = ins_k.groupby("call_month").agg(
            aca_rate=("aca_rate", "mean"),
            subsidy_rate=("subsidy_rate", "mean"),
        ).reset_index()
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(x=monthly_aca["call_month"], y=monthly_aca["aca_rate"],
                                  name="ACA Eligible", fill="tozeroy",
                                  line=dict(color=COLORS["primary"])))
        fig3.add_trace(go.Scatter(x=monthly_aca["call_month"], y=monthly_aca["subsidy_rate"],
                                  name="Subsidy Eligible", fill="tozeroy",
                                  line=dict(color="#93C5FD")))
        fig3.update_layout(plot_bgcolor="white", height=280, yaxis_tickformat=".0%")
        st.plotly_chart(fig3, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: Healthcare
# ─────────────────────────────────────────────────────────────────────────────
elif "Healthcare" in page:
    st.markdown("# 🏥 Healthcare Vertical")
    st.markdown("*Appointment scheduling, benefits verification, specialty breakdown*")
    st.markdown("---")

    if hc_k.empty:
        st.warning("No healthcare data.")
    else:
        tc = int(hc_k["total_calls"].sum())
        appts = int(hc_k["total_appointments_scheduled"].sum())
        appt_rate = appts / tc if tc else 0
        webhooks = int(hc_k["webhook_sent_count"].sum())
        conv = int(hc_k["total_converted"].sum())

        cols = st.columns(4)
        for col, (l, v, c) in zip(cols, [
            ("Total Calls", f"{tc:,}", ""),
            ("Appointments Scheduled", f"{appts:,}", "green"),
            ("Appointment Rate", f"{appt_rate:.1%}", "green" if appt_rate > 0.20 else "amber"),
            ("Webhooks Sent", f"{webhooks:,}", ""),
        ]):
            col.markdown(card(l, v, color=c), unsafe_allow_html=True)

        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Monthly Appointment Rate")
            monthly = hc_k.groupby("call_month").agg(
                total_calls=("total_calls", "sum"),
                appts=("total_appointments_scheduled", "sum"),
            ).reset_index()
            monthly["appt_rate"] = monthly["appts"] / monthly["total_calls"]
            fig = go.Figure()
            fig.add_trace(go.Bar(x=monthly["call_month"], y=monthly["appts"],
                                 name="Appointments", marker_color="#6EE7B7"))
            fig.add_trace(go.Scatter(x=monthly["call_month"], y=monthly["appt_rate"],
                                     name="Appt Rate", line=dict(color=COLORS["success"], width=3),
                                     yaxis="y2", mode="lines+markers"))
            fig.update_layout(
                plot_bgcolor="white", height=320,
                yaxis2=dict(overlaying="y", side="right", tickformat=".0%"),
                legend=dict(orientation="h", y=1.1),
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("#### Specialty Distribution")
            spec_cols = [c for c in hc_k.columns if c.startswith("spec_")]
            if spec_cols:
                spec_totals = hc_k[spec_cols].sum().reset_index()
                spec_totals.columns = ["specialty", "count"]
                spec_totals["specialty"] = (spec_totals["specialty"]
                                            .str.replace("spec_", "")
                                            .str.replace("_", " ").str.title())
                spec_totals = spec_totals.sort_values("count", ascending=True)
                fig2 = px.bar(spec_totals, x="count", y="specialty", orientation="h",
                              color="count", color_continuous_scale="Greens")
                fig2.update_layout(height=320, showlegend=False,
                                   coloraxis_showscale=False)
                st.plotly_chart(fig2, use_container_width=True)

        # Sentiment trend
        st.markdown("#### Average Sentiment Trend")
        sent = hc_k.groupby("call_month")["avg_sentiment"].mean().reset_index()
        fig3 = go.Figure(go.Scatter(
            x=sent["call_month"], y=sent["avg_sentiment"],
            mode="lines+markers", fill="tozeroy",
            line=dict(color=COLORS["success"], width=2),
            fillcolor="rgba(5,122,85,0.08)",
        ))
        fig3.add_hline(y=0, line_dash="dash", line_color=COLORS["neutral"])
        fig3.update_layout(plot_bgcolor="white", height=260,
                           yaxis_title="Sentiment Score")
        st.plotly_chart(fig3, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: Real Estate
# ─────────────────────────────────────────────────────────────────────────────
elif "Real" in page:
    st.markdown("# 🏠 Real Estate Vertical")
    st.markdown("*Lead qualification, agent matching, buyer vs seller pipeline*")
    st.markdown("---")

    if re_k.empty:
        st.warning("No real estate data.")
    else:
        tc = int(re_k["total_calls"].sum())
        qual = int(re_k["total_qualified"].sum())
        matched = int(re_k["total_agent_matched"].sum())
        qual_rate = qual / tc if tc else 0

        cols = st.columns(4)
        for col, (l, v, c) in zip(cols, [
            ("Total Calls", f"{tc:,}", ""),
            ("Leads Qualified", f"{qual:,}", "green"),
            ("Qualification Rate", f"{qual_rate:.1%}", ""),
            ("Agent Matches", f"{matched:,}", "green"),
        ]):
            col.markdown(card(l, v, color=c), unsafe_allow_html=True)

        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Buyer vs Seller Lead Volume")
            monthly = re_k.groupby("call_month").agg(
                buyers=("lead_type_buyer", "sum"),
                sellers=("lead_type_seller", "sum"),
            ).reset_index()
            fig = go.Figure()
            fig.add_trace(go.Bar(x=monthly["call_month"], y=monthly["buyers"],
                                 name="Buyers", marker_color=COLORS["warning"]))
            fig.add_trace(go.Bar(x=monthly["call_month"], y=monthly["sellers"],
                                 name="Sellers", marker_color="#FCD34D"))
            fig.update_layout(barmode="stack", plot_bgcolor="white", height=320,
                              legend=dict(orientation="h", y=1.1))
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("#### Monthly Qualification Rate")
            re_k["qual_rate"] = re_k["total_qualified"] / re_k["total_calls"]
            monthly_q = re_k.groupby("call_month")["qual_rate"].mean().reset_index()
            fig2 = go.Figure(go.Scatter(
                x=monthly_q["call_month"], y=monthly_q["qual_rate"],
                mode="lines+markers", fill="tozeroy",
                line=dict(color=COLORS["warning"], width=2),
                fillcolor="rgba(195,126,3,0.08)",
            ))
            fig2.update_layout(plot_bgcolor="white", height=320,
                               yaxis_tickformat=".0%")
            st.plotly_chart(fig2, use_container_width=True)

        # Budget distribution
        st.markdown("#### Average Budget Range by Month")
        budget = re_k.groupby("call_month").agg(
            avg_min=("avg_budget_min", "mean"),
            avg_max=("avg_budget_max", "mean"),
        ).reset_index()
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(x=budget["call_month"], y=budget["avg_max"],
                                  name="Avg Budget Max", fill="tonexty",
                                  line=dict(color=COLORS["warning"])))
        fig3.add_trace(go.Scatter(x=budget["call_month"], y=budget["avg_min"],
                                  name="Avg Budget Min", fill="tozeroy",
                                  line=dict(color="#FCD34D")))
        fig3.update_layout(plot_bgcolor="white", height=280,
                           yaxis_tickprefix="$", yaxis_tickformat=",.0f")
        st.plotly_chart(fig3, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: AR Sales
# ─────────────────────────────────────────────────────────────────────────────
elif "AR" in page:
    st.markdown("# 💳 AR Sales Vertical")
    st.markdown("*Recovery rates, settlement analysis, SOL exposure, FDCPA compliance*")
    st.markdown("---")

    if ar_k.empty:
        st.warning("No AR data.")
    else:
        tc = int(ar_k["total_calls"].sum())
        arr = int(ar_k["total_arrangements"].sum())
        total_bal = ar_k["total_original_balance"].sum()
        total_set = ar_k["total_settlement_amount"].sum()
        recovery = total_set / total_bal if total_bal else 0
        sol_exp = int(ar_k["sol_expired_count"].sum())

        cols = st.columns(5)
        for col, (l, v, c) in zip(cols, [
            ("Total Calls", f"{tc:,}", ""),
            ("Arrangements Made", f"{arr:,}", "green"),
            ("Total Balance", f"${total_bal:,.0f}", ""),
            ("Total Recovered", f"${total_set:,.0f}", "green"),
            ("Recovery Rate", f"{recovery:.1%}", "green" if recovery > 0.5 else "amber"),
        ]):
            col.markdown(card(l, v, color=c), unsafe_allow_html=True)

        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Monthly Balance vs Recovered")
            monthly = ar_k.groupby("call_month").agg(
                original=("total_original_balance", "sum"),
                recovered=("total_settlement_amount", "sum"),
            ).reset_index()
            fig = go.Figure()
            fig.add_trace(go.Bar(x=monthly["call_month"], y=monthly["original"],
                                 name="Original Balance", marker_color="#FCA5A5"))
            fig.add_trace(go.Bar(x=monthly["call_month"], y=monthly["recovered"],
                                 name="Recovered", marker_color=COLORS["danger"]))
            fig.update_layout(barmode="overlay", plot_bgcolor="white", height=320,
                              yaxis_tickprefix="$", yaxis_tickformat=",.0f",
                              legend=dict(orientation="h", y=1.1))
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("#### Settlement % Distribution")
            monthly_s = ar_k.groupby("call_month")["avg_settlement_pct"].mean().reset_index()
            fig2 = go.Figure(go.Scatter(
                x=monthly_s["call_month"], y=monthly_s["avg_settlement_pct"] * 100,
                mode="lines+markers", fill="tozeroy",
                line=dict(color=COLORS["danger"], width=2),
                fillcolor="rgba(224,36,36,0.08)",
            ))
            fig2.update_layout(plot_bgcolor="white", height=320,
                               yaxis_title="Avg Settlement %")
            st.plotly_chart(fig2, use_container_width=True)

        # SOL exposure
        if sol_exp > 0:
            st.warning(f"⚠️ **SOL Exposure**: {sol_exp} calls on accounts with expired statute "
                       f"of limitations. Legal review recommended.")

        st.markdown("#### Recovery Rate Trend")
        ar_k["recovery"] = ar_k["total_settlement_amount"] / ar_k["total_original_balance"].replace(0, float("nan"))
        monthly_r = ar_k.groupby("call_month")["recovery"].mean().reset_index()
        fig3 = go.Figure(go.Scatter(
            x=monthly_r["call_month"], y=monthly_r["recovery"],
            mode="lines+markers+text",
            text=(monthly_r["recovery"] * 100).round(1).astype(str) + "%",
            textposition="top center",
            line=dict(color=COLORS["danger"], width=2),
        ))
        fig3.update_layout(plot_bgcolor="white", height=260, yaxis_tickformat=".0%")
        st.plotly_chart(fig3, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: Agent & QA
# ─────────────────────────────────────────────────────────────────────────────
elif "Agent" in page:
    st.markdown("# 👥 Agent & QA Performance")
    st.markdown("*Individual and team performance, QA scoring, auto-flag monitoring*")
    st.markdown("---")

    if agent.empty:
        st.warning("No agent data.")
    else:
        cols = st.columns(4)
        active = int((agent["days_active"] > 0).sum()) if "days_active" in agent.columns else 0
        flagged = int(agent["consecutive_below_threshold_flag"].sum()) if \
            "consecutive_below_threshold_flag" in agent.columns else 0
        avg_conv = agent["avg_conversion_rate"].mean() if "avg_conversion_rate" in agent.columns else 0
        avg_qa = qa_sc["avg_qa_score"].mean() if not qa_sc.empty else 0

        for col, (l, v, c) in zip(cols, [
            ("Active Agents", f"{active}", ""),
            ("Avg Conversion Rate", f"{avg_conv:.1%}", "green" if avg_conv > 0.12 else "amber"),
            ("Avg QA Score", f"{avg_qa:.2f} / 5.0", "green" if avg_qa > 3.5 else "amber"),
            ("Auto-Flagged for Review", f"{flagged}", "red" if flagged > 0 else "green"),
        ]):
            col.markdown(card(l, v, color=c), unsafe_allow_html=True)

        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Agent Performance by Tier")
            tier_g = agent.groupby("performance_tier").agg(
                agents=("agent_id", "count"),
                avg_conv=("avg_conversion_rate", "mean"),
                avg_talk=("total_talk_hours", "mean"),
            ).reset_index()
            fig = px.bar(tier_g, x="performance_tier", y="avg_conv",
                         color="performance_tier",
                         color_discrete_map={"high": COLORS["success"],
                                             "mid": COLORS["warning"],
                                             "low": COLORS["danger"]},
                         text_auto=".1%",
                         labels={"avg_conv": "Avg Conv Rate", "performance_tier": "Tier"})
            fig.update_layout(showlegend=False, plot_bgcolor="white", height=300,
                              yaxis_tickformat=".0%")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("#### QA Score Distribution")
            if not qa_sc.empty:
                fig2 = px.histogram(qa_sc, x="avg_qa_score", nbins=15,
                                    color_discrete_sequence=[COLORS["primary"]],
                                    labels={"avg_qa_score": "Avg QA Score"})
                fig2.add_vline(x=qa_sc["avg_qa_score"].mean(), line_dash="dash",
                               line_color=COLORS["warning"],
                               annotation_text=f"Mean: {qa_sc['avg_qa_score'].mean():.2f}")
                fig2.update_layout(plot_bgcolor="white", height=300)
                st.plotly_chart(fig2, use_container_width=True)

        # Agent leaderboard
        st.markdown("#### Agent Leaderboard")
        if "first_name" in agent.columns:
            lb = agent.copy()
            lb["Agent Name"] = lb["first_name"] + " " + lb["last_name"]
            lb = lb[["Agent Name", "role", "performance_tier", "avg_conversion_rate",
                      "total_calls", "total_talk_hours", "days_below_threshold",
                      "consecutive_below_threshold_flag"]].copy()
            lb["avg_conversion_rate"] = (lb["avg_conversion_rate"] * 100).round(1).astype(str) + "%"
            lb["total_talk_hours"] = lb["total_talk_hours"].round(1)
            lb.columns = ["Agent", "Role", "Tier", "Conv Rate", "Calls",
                          "Talk Hours", "Days Below", "Auto-Flagged"]
            lb = lb.sort_values("Conv Rate", ascending=False)
            st.dataframe(lb, use_container_width=True, hide_index=True)

        # Auto-flag list
        if flagged > 0:
            st.markdown("#### ⚠️ Agents Flagged for Mandatory QA Review")
            flagged_agents = agent[agent["consecutive_below_threshold_flag"] == True].copy()
            if "first_name" in flagged_agents.columns:
                flagged_agents["Name"] = flagged_agents["first_name"] + " " + flagged_agents["last_name"]
                st.dataframe(
                    flagged_agents[["Name", "role", "avg_conversion_rate",
                                    "days_below_threshold"]].rename(columns={
                        "avg_conversion_rate": "Avg Conv Rate",
                        "days_below_threshold": "Days Below Threshold",
                    }),
                    use_container_width=True, hide_index=True,
                )


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: Compliance & Risk
# ─────────────────────────────────────────────────────────────────────────────
elif "Compliance" in page:
    st.markdown("# ⚠️ Compliance & Risk Monitor")
    st.markdown("*TCPA, HIPAA, FDCPA — flags, violation trends, DNC tracking*")
    st.markdown("---")

    if comp.empty:
        st.warning("No compliance data.")
    else:
        total_flags = int(comp["compliance_flags"].sum())
        avg_flag_rate = comp["compliance_flag_rate"].mean()
        max_rate = comp["compliance_flag_rate"].max()
        worst_v = comp.loc[comp["compliance_flag_rate"].idxmax(), "vertical"] \
            if not comp.empty else "N/A"

        cols = st.columns(4)
        for col, (l, v, c) in zip(cols, [
            ("Total Compliance Flags", f"{total_flags:,}",
             "red" if total_flags > 200 else "amber"),
            ("Avg Flag Rate", f"{avg_flag_rate:.1%}",
             "red" if avg_flag_rate > 0.1 else "amber"),
            ("Peak Flag Rate", f"{max_rate:.1%}", "red"),
            ("Highest Risk Vertical", worst_v, "red"),
        ]):
            col.markdown(card(l, v, color=c), unsafe_allow_html=True)

        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Compliance Flag Rate by Vertical & Month")
            fig = px.line(
                comp, x="call_month", y="compliance_flag_rate",
                color="vertical", color_discrete_map=COLORS,
                markers=True,
                labels={"compliance_flag_rate": "Flag Rate", "call_month": "Month"},
            )
            fig.add_hline(y=0.05, line_dash="dot", line_color=COLORS["danger"],
                          annotation_text="5% Alert Threshold")
            fig.update_layout(plot_bgcolor="white", height=320,
                              yaxis_tickformat=".0%")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("#### Total Flags by Vertical")
            vf = comp.groupby("vertical")["compliance_flags"].sum().reset_index()
            fig2 = px.bar(vf, x="vertical", y="compliance_flags",
                          color="vertical", color_discrete_map=COLORS,
                          text_auto=True)
            fig2.update_layout(showlegend=False, plot_bgcolor="white", height=320)
            st.plotly_chart(fig2, use_container_width=True)

        # FDCPA violations from dialer
        if not dial.empty:
            st.markdown("#### FDCPA Abandon Rate Violations (> 3%)")
            violations = dial[dial["above_fdcpa_abandon_threshold"] == True].copy()
            if len(violations):
                violations["call_date"] = pd.to_datetime(violations["call_date"], errors="coerce")
                v_monthly = violations.groupby(
                    violations["call_date"].dt.to_period("M").astype(str)
                )["total_dials"].sum().reset_index()
                v_monthly.columns = ["Month", "Dials During Violations"]
                st.dataframe(v_monthly, use_container_width=True, hide_index=True)
                st.error(f"⚠️ {len(violations):,} sessions exceeded the FDCPA 3% abandon rate "
                         f"limit. Immediate dialer configuration review recommended.")
            else:
                st.success("✅ No FDCPA abandon rate violations detected.")

        # Campaign compliance leaderboard
        st.markdown("#### Campaign Compliance Risk Ranking")
        camp_comp = camp[["name", "vertical", "total_calls",
                           "compliance_flags", "conversion_rate"]].copy()
        camp_comp["flag_rate"] = (camp_comp["compliance_flags"] / camp_comp["total_calls"]).round(3)
        camp_comp = camp_comp.sort_values("flag_rate", ascending=False)
        camp_comp["flag_rate"] = (camp_comp["flag_rate"] * 100).round(1).astype(str) + "%"
        camp_comp["conversion_rate"] = (camp_comp["conversion_rate"] * 100).round(1).astype(str) + "%"
        st.dataframe(camp_comp.rename(columns={
            "name": "Campaign", "vertical": "Vertical",
            "total_calls": "Calls", "compliance_flags": "Flags",
            "flag_rate": "Flag Rate", "conversion_rate": "Conv Rate",
        }), use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: ML / AI Insights
# ─────────────────────────────────────────────────────────────────────────────
elif "ML" in page:
    st.markdown("# 🤖 ML / AI Insights")
    st.markdown("*Lead scoring, propensity models, feature importance, model performance*")
    st.markdown("---")

    report = load_ml_report()
    fi_df  = load_feature_importance()

    if not report:
        st.warning("No ML report found. Run `python ml/train.py` first.")
    else:
        models = report.get("models", [])
        col1, col2 = st.columns([3, 2])

        with col1:
            st.markdown("#### Model Performance Summary")
            model_df = pd.DataFrame(models)
            if not model_df.empty:
                fig = go.Figure()
                metrics_to_plot = ["auc_roc", "precision", "recall", "f1"]
                colors_m = [COLORS["primary"], COLORS["success"],
                            COLORS["warning"], COLORS["danger"]]
                for metric, color in zip(metrics_to_plot, colors_m):
                    if metric in model_df.columns:
                        fig.add_trace(go.Bar(
                            name=metric.upper().replace("_", " "),
                            x=model_df["model"],
                            y=model_df[metric],
                            marker_color=color,
                            text=model_df[metric].round(3),
                            textposition="outside",
                        ))
                fig.update_layout(
                    barmode="group", plot_bgcolor="white", height=360,
                    yaxis=dict(range=[0, 1.1]),
                    legend=dict(orientation="h", y=1.1),
                )
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("#### AUC-ROC Gauges")
            for m in models:
                auc = m.get("auc_roc", 0)
                color = COLORS["success"] if auc >= 0.85 else COLORS["warning"]
                fig_g = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=auc,
                    title={"text": m["model"], "font": {"size": 13}},
                    gauge={
                        "axis": {"range": [0, 1]},
                        "bar": {"color": color},
                        "steps": [
                            {"range": [0, 0.7], "color": "#FEE2E2"},
                            {"range": [0.7, 0.85], "color": "#FEF3C7"},
                            {"range": [0.85, 1], "color": "#D1FAE5"},
                        ],
                    },
                    domain={"x": [0, 1], "y": [0, 1]},
                ))
                fig_g.update_layout(height=160, margin=dict(t=30, b=10, l=20, r=20))
                st.plotly_chart(fig_g, use_container_width=True)

        # Feature Importance
        if not fi_df.empty:
            st.markdown("---")
            st.markdown("#### Feature Importance by Vertical")
            selected_v = st.selectbox(
                "Select vertical", ["Global"] + list(fi_df["vertical"].unique()),
            )
            fi_sel = fi_df[fi_df["vertical"] == selected_v].head(15)
            fig3 = px.bar(
                fi_sel.sort_values("importance"),
                x="importance", y="feature", orientation="h",
                color="importance", color_continuous_scale="Blues",
                labels={"importance": "Importance", "feature": "Feature"},
            )
            fig3.update_layout(plot_bgcolor="white", height=400,
                               coloraxis_showscale=False)
            st.plotly_chart(fig3, use_container_width=True)

        # Lead score distribution
        if not ml_feat.empty and "predicted_score" in ml_feat.columns:
            st.markdown("---")
            st.markdown("#### Lead Score Distribution by Vertical")
            fig4 = px.histogram(
                ml_feat.dropna(subset=["predicted_score"]),
                x="predicted_score", color="vertical",
                color_discrete_map=COLORS, nbins=20,
                facet_col="vertical", facet_col_wrap=2,
                labels={"predicted_score": "Propensity Score"},
            )
            fig4.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig4, use_container_width=True)

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### Score vs Actual Conversion")
                fig5 = px.box(
                    ml_feat.dropna(subset=["predicted_score"]),
                    x="converted", y="predicted_score",
                    color="converted",
                    color_discrete_map={0: COLORS["danger"], 1: COLORS["success"]},
                    labels={"converted": "Converted", "predicted_score": "Model Score"},
                )
                fig5.update_layout(plot_bgcolor="white", height=320, showlegend=False)
                st.plotly_chart(fig5, use_container_width=True)

            with col2:
                st.markdown("#### Score Buckets — Conversion Rate")
                ml_copy = ml_feat.dropna(subset=["predicted_score"]).copy()
                ml_copy["score_bucket"] = pd.cut(
                    ml_copy["predicted_score"],
                    bins=[0, 20, 40, 60, 80, 100],
                    labels=["0-20", "20-40", "40-60", "60-80", "80-100"],
                )
                bucket_df = ml_copy.groupby("score_bucket", observed=True).agg(
                    leads=("lead_id", "count"),
                    conv_rate=("converted", "mean"),
                ).reset_index()
                fig6 = go.Figure()
                fig6.add_trace(go.Bar(x=bucket_df["score_bucket"].astype(str),
                                      y=bucket_df["leads"], name="Leads",
                                      marker_color="#BFDBFE"))
                fig6.add_trace(go.Scatter(x=bucket_df["score_bucket"].astype(str),
                                          y=bucket_df["conv_rate"],
                                          name="Conv Rate", yaxis="y2",
                                          line=dict(color=COLORS["primary"], width=3),
                                          mode="lines+markers"))
                fig6.update_layout(
                    plot_bgcolor="white", height=320,
                    yaxis2=dict(overlaying="y", side="right", tickformat=".0%"),
                    legend=dict(orientation="h", y=1.1),
                )
                st.plotly_chart(fig6, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: SQL & AI Query Studio
# ─────────────────────────────────────────────────────────────────────────────
elif "SQL" in page:
    render_sql_page()

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: AI Data Assistant
# ─────────────────────────────────────────────────────────────────────────────
elif "AI Data Assistant" in page:
    render_ai_chat_page()

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: Glossary & Definitions
# ─────────────────────────────────────────────────────────────────────────────
elif "Glossary" in page:
    render_glossary_page()

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: Data Mesh Health
# ─────────────────────────────────────────────────────────────────────────────
elif "Data Mesh" in page:
    st.markdown("# 🗄️ Data Mesh Health")
    st.markdown("*Lakehouse layer status, domain pipeline health, DLQ monitoring*")
    st.markdown("---")

    def layer_stats(layer: str) -> list[dict]:
        d = BASE / "lakehouse" / layer
        if not d.exists():
            return []
        rows = []
        for f in sorted(d.rglob("*.parquet")):
            df = pd.read_parquet(f)
            rows.append({
                "Layer": layer.title(),
                "Table": f.stem,
                "Path": str(f.relative_to(d.parent)),
                "Rows": len(df),
                "Columns": len(df.columns),
                "Size KB": round(f.stat().st_size / 1024, 1),
            })
        return rows

    all_stats = []
    for layer in ["bronze", "silver", "gold"]:
        all_stats.extend(layer_stats(layer))

    if all_stats:
        stats_df = pd.DataFrame(all_stats)

        # Layer summary cards
        cols = st.columns(3)
        for col, layer in zip(cols, ["Bronze", "Silver", "Gold"]):
            sub = stats_df[stats_df["Layer"] == layer]
            total_rows = sub["Rows"].sum()
            total_size = sub["Size KB"].sum() / 1024
            n_tables = len(sub)
            col.markdown(card(
                f"{layer} Layer",
                f"{n_tables} tables",
                f"{total_rows:,} rows  ·  {total_size:.2f} MB",
            ), unsafe_allow_html=True)

        st.markdown("---")

        # Pipeline flow diagram (text-based)
        st.markdown("#### Data Mesh Pipeline Flow")
        st.markdown("""
```
Source CSVs / Event Hubs JSONL
    │
    ▼
┌─────────────────── BRONZE ───────────────────┐
│  Raw partitioned parquet (by vertical)        │
│  clients · agents · campaigns · leads · calls │
│  qa_reviews · appointments · arrangements     │
│  pipeline_events · ml_features                │
└──────────────────────┬───────────────────────┘
                       │
    ┌──────────────────┼──────────────────┐
    ▼                  ▼                  ▼
┌ Insurance ┐   ┌ Healthcare ┐   ┌ RealEstate ┐  ┌ AR ┐
│ Domain    │   │ Domain     │   │ Domain     │  │    │
│ Pipeline  │   │ Pipeline   │   │ Pipeline   │  │    │
└─────┬─────┘   └─────┬──────┘   └─────┬──────┘  └─┬──┘
      └────────────────┴──────────────┴─────────────┘
                       │
                       ▼
┌─────────────────── SILVER ───────────────────┐
│  dim_agents · dim_campaigns · dim_clients     │
│  silver_calls_all · silver_leads              │
│  silver_insurance · silver_healthcare         │
│  silver_realestate · silver_ar                │
│  silver_qa_reviews · silver_agent_performance │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────── GOLD ────────────────────┐
│  gold_campaign_kpis · gold_agent_performance  │
│  gold_insurance_kpis · gold_healthcare_kpis   │
│  gold_realestate_kpis · gold_ar_kpis          │
│  gold_compliance_summary · gold_dialer_perf   │
│  gold_ml_feature_store · gold_qa_agent_scores │
└──────────────────────┬───────────────────────┘
                       │
               ┌───────┴────────┐
               ▼                ▼
         ML Training      Dashboard
```
""")

        # Table inventory
        st.markdown("#### Lakehouse Table Inventory")
        st.dataframe(
            stats_df.sort_values(["Layer", "Table"]),
            use_container_width=True, hide_index=True,
        )

        # Row counts bar chart
        st.markdown("#### Row Counts by Layer")
        layer_totals = stats_df.groupby("Layer")["Rows"].sum().reset_index()
        fig = px.bar(layer_totals, x="Layer", y="Rows", text_auto=True,
                     color="Layer",
                     color_discrete_map={"Bronze": "#92400E",
                                         "Silver": "#6B7280",
                                         "Gold": "#B45309"})
        fig.update_layout(showlegend=False, plot_bgcolor="white", height=280)
        st.plotly_chart(fig, use_container_width=True)

    # DLQ status
    st.markdown("#### Dead Letter Queue (DLQ)")
    dlq_dir = BASE / "lakehouse" / "dlq"
    if dlq_dir.exists():
        dlq_files = list(dlq_dir.glob("*.csv"))
        if dlq_files:
            st.error(f"⚠️ {len(dlq_files)} DLQ file(s) require attention:")
            for f in dlq_files:
                df_dlq = pd.read_csv(f, nrows=5)
                with st.expander(f.name):
                    st.dataframe(df_dlq, use_container_width=True)
        else:
            st.success("✅ No DLQ files — all events processed successfully.")
    else:
        st.success("✅ DLQ directory empty.")
