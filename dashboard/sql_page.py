"""
SQL Analytics, AI Chat & Self-Service BI — integrated Streamlit page.
Import render_sql_page() and call it from app.py.
"""

from __future__ import annotations

import traceback
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from .sql_catalog import QUERIES
from .nlp_engine import generate_sql, answer_question

GOLD = Path(__file__).parent.parent / "lakehouse" / "gold"

COLORS = {
    "primary": "#1A56DB", "success": "#057A55",
    "warning": "#C27803", "danger": "#E02424",
}

LEVEL_ICONS = {
    "Basic": "🟢",
    "Intermediate": "🔵",
    "Window Functions": "🟡",
    "CTEs": "🟣",
    "Advanced": "🔴",
}


# ── DuckDB connection ─────────────────────────────────────────────────────────

@st.cache_resource
def get_db() -> duckdb.DuckDBPyConnection:
    """Persistent in-process DuckDB with all Gold parquets registered as views."""
    con = duckdb.connect(database=":memory:")
    gold = Path(__file__).parent.parent / "lakehouse" / "gold"
    for pq in gold.glob("*.parquet"):
        view = pq.stem
        con.execute(f"CREATE OR REPLACE VIEW {view} AS SELECT * FROM read_parquet('{pq.as_posix()}')")
    return con


def run_sql(sql: str) -> tuple[pd.DataFrame | None, str | None]:
    try:
        con = get_db()
        df = con.execute(sql).df()
        return df, None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


# ── Helpers ───────────────────────────────────────────────────────────────────

def level_badge_html(level: str) -> str:
    """HTML badge — for use inside st.markdown() inside expanders."""
    colors = {
        "Basic": ("#D1FAE5", "#065F46"),
        "Intermediate": ("#DBEAFE", "#1E40AF"),
        "Window Functions": ("#FEF3C7", "#92400E"),
        "CTEs": ("#F3E8FF", "#6B21A8"),
        "Advanced": ("#FEE2E2", "#991B1B"),
    }
    bg, fg = colors.get(level, ("#E5E7EB", "#111827"))
    return (f'<span style="background:{bg};color:{fg};padding:3px 12px;'
            f'border-radius:12px;font-size:12px;font-weight:700;'
            f'letter-spacing:.03em">{level}</span>')


def auto_chart(df: pd.DataFrame, title: str = "") -> None:
    """Heuristically build the best chart for a given dataframe."""
    if df is None or df.empty:
        return
    num_cols = df.select_dtypes(include="number").columns.tolist()
    str_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    if not num_cols:
        st.dataframe(df, use_container_width=True, hide_index=True)
        return

    # Time series: string col looks like YYYY-MM
    if str_cols and any(df[str_cols[0]].astype(str).str.match(r"\d{4}-\d{2}").any()
                        for c in str_cols[:1]):
        x = str_cols[0]
        y = num_cols[0]
        color = str_cols[1] if len(str_cols) > 1 else None
        fig = px.line(df, x=x, y=num_cols[:3], title=title, markers=True)
        fig.update_layout(plot_bgcolor="white", height=350)
        st.plotly_chart(fig, use_container_width=True)

    # One categorical + multiple metrics → grouped bar
    elif str_cols and len(num_cols) >= 2:
        fig = px.bar(df.head(25), x=str_cols[0], y=num_cols[:4],
                     barmode="group", title=title,
                     color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_layout(plot_bgcolor="white", height=380)
        st.plotly_chart(fig, use_container_width=True)

    # Single metric bar
    elif str_cols and len(num_cols) == 1:
        fig = px.bar(df.head(25), x=str_cols[0], y=num_cols[0],
                     color=num_cols[0], title=title,
                     color_continuous_scale="Blues")
        fig.update_layout(plot_bgcolor="white", height=350,
                          coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    # All numeric → scatter matrix
    elif len(num_cols) >= 2:
        fig = px.scatter(df.head(200), x=num_cols[0], y=num_cols[1],
                         size=num_cols[2] if len(num_cols) > 2 else None,
                         title=title)
        fig.update_layout(plot_bgcolor="white", height=350)
        st.plotly_chart(fig, use_container_width=True)


# ── Main renderer ─────────────────────────────────────────────────────────────

def render_sql_page() -> None:
    st.markdown("# 🔍 SQL Analytics & AI Query Studio")
    st.markdown("*Query the BPO lakehouse with SQL or plain English — "
                "from basic selects to complex window functions*")
    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs([
        "📚 SQL Library",
        "✏️ SQL Workbench",
        "🤖 AI / NLP Chat",
        "📊 Self-Service BI",
    ])

    # ── TAB 1: SQL Library ────────────────────────────────────────────────────
    with tab1:
        st.markdown("### Curated SQL Query Library")

        # Level legend with counts
        level_counts = {}
        for qmeta in QUERIES.values():
            level_counts[qmeta["level"]] = level_counts.get(qmeta["level"], 0) + 1

        legend_html = " &nbsp; ".join(
            f'{level_badge_html(lvl)} <span style="font-size:12px;color:#6B7280">'
            f'×{level_counts.get(lvl,0)}</span>'
            for lvl in ["Basic", "Intermediate", "Window Functions", "CTEs", "Advanced"]
        )
        st.markdown(legend_html, unsafe_allow_html=True)
        st.markdown(
            '<p style="font-size:13px;color:#6B7280;margin-top:8px">'
            'Click any query to expand — view SQL, run it, auto-visualize, and download results.</p>',
            unsafe_allow_html=True,
        )
        st.markdown("---")

        # Filter by level
        levels = ["All"] + list(["Basic", "Intermediate", "Window Functions", "CTEs", "Advanced"])
        chosen_level = st.selectbox("Filter by level", levels, key="lib_level")

        for qname, qmeta in QUERIES.items():
            if chosen_level != "All" and qmeta["level"] != chosen_level:
                continue
            icon = LEVEL_ICONS.get(qmeta["level"], "⚪")
            with st.expander(f"{icon} {qname}", expanded=False):
                # Badge + description inside expander (HTML renders here)
                st.markdown(
                    f'{level_badge_html(qmeta["level"])} &nbsp; '
                    f'<span style="color:#6B7280;font-size:13px">{qmeta["description"]}</span>',
                    unsafe_allow_html=True,
                )
                st.markdown("")
                st.code(qmeta["sql"], language="sql")
                col_run, col_space = st.columns([1, 5])
                if col_run.button("▶ Run", key=f"run_{qname}", type="primary"):
                    with st.spinner("Running…"):
                        df, err = run_sql(qmeta["sql"])
                    if err:
                        st.error(err)
                    elif df is not None:
                        st.success(f"✅ {len(df):,} rows returned")
                        st.dataframe(df, use_container_width=True,
                                     hide_index=True, height=280)
                        auto_chart(df, title=qname)
                        st.download_button(
                            "⬇ Download CSV",
                            df.to_csv(index=False).encode(),
                            file_name=f"{qname.replace(' ', '_')}.csv",
                            key=f"dl_{qname}",
                        )

    # ── TAB 2: SQL Workbench ──────────────────────────────────────────────────
    with tab2:
        st.markdown("### SQL Workbench")
        st.markdown("Write and run any DuckDB SQL against the lakehouse Gold tables.")

        # Schema reference
        with st.expander("📋 Available Tables & Columns"):
            tables = {
                "gold_campaign_kpis": "name, vertical, dialing_mode, status, total_calls, conversion_rate, avg_sentiment, compliance_flags, …",
                "gold_agent_performance": "first_name, last_name, role, performance_tier, avg_conversion_rate, total_talk_hours, consecutive_below_threshold_flag, …",
                "gold_dialer_performance": "campaign_id, call_date, total_dials, answer_rate, abandon_rate, above_fdcpa_abandon_threshold, dialing_mode, …",
                "gold_compliance_summary": "vertical, call_month, total_calls, compliance_flags, compliance_flag_rate",
                "gold_insurance_kpis": "call_month, total_calls, conversion_rate, aca_eligible_rate, avg_annual_income, product_health, product_auto, …",
                "gold_healthcare_kpis": "call_month, total_calls, appointment_rate, total_appointments_scheduled, spec_cardiology, spec_primary_care, …",
                "gold_realestate_kpis": "call_month, total_calls, qualification_rate, lead_type_buyer, lead_type_seller, avg_budget_min, avg_budget_max, …",
                "gold_ar_kpis": "call_month, total_calls, total_arrangements, recovery_rate, total_settlement_amount, avg_settlement_pct, sol_expired_count",
                "gold_ml_feature_store": "vertical, state, lead_score, converted, predicted_score, global_predicted_score, n_call_attempts, avg_sentiment_score, …",
                "gold_qa_agent_scores": "agent_id, total_reviews, avg_qa_score, min_qa_score, max_qa_score",
            }
            for t, cols in tables.items():
                st.markdown(f"**`{t}`** — {cols}")

        default_sql = QUERIES["B1 – Campaign Overview"]["sql"]
        sql_input = st.text_area(
            "SQL Query",
            value=st.session_state.get("workbench_sql", default_sql),
            height=220,
            key="wb_sql",
        )
        c1, c2, c3 = st.columns([1, 1, 4])
        run_btn = c1.button("▶ Run Query", type="primary")
        clear_btn = c2.button("🗑 Clear")
        if clear_btn:
            st.session_state["workbench_sql"] = ""
            st.rerun()

        if run_btn and sql_input.strip():
            st.session_state["workbench_sql"] = sql_input
            with st.spinner("Executing…"):
                df, err = run_sql(sql_input)
            if err:
                st.error(f"SQL Error: {err}")
            elif df is not None:
                st.success(f"✅ {len(df):,} rows returned")
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    st.dataframe(df, use_container_width=True,
                                 hide_index=True, height=320)
                with col_b:
                    st.metric("Rows", f"{len(df):,}")
                    st.metric("Columns", len(df.columns))
                    if df.select_dtypes(include="number").shape[1] > 0:
                        num_df = df.select_dtypes(include="number")
                        st.metric("Numeric Cols", len(num_df.columns))
                    st.download_button(
                        "⬇ CSV", df.to_csv(index=False).encode(),
                        file_name="query_result.csv",
                    )
                # Auto-chart
                st.markdown("#### Auto-Visualization")
                auto_chart(df)

    # ── TAB 3: AI / NLP Chat ──────────────────────────────────────────────────
    with tab3:
        import os
        st.markdown("### 🤖 Chat with Your Data")

        has_openai = bool(os.environ.get("OPENAI_API_KEY"))
        if has_openai:
            st.success("✅ OpenAI GPT-4o connected — full NLP query generation active.")
        else:
            st.info(
                "💡 Set `OPENAI_API_KEY` environment variable to enable GPT-4o. "
                "Currently using built-in keyword NLP (works without API key)."
            )

        # API key input
        with st.expander("🔑 Set OpenAI API Key (session only)"):
            key_input = st.text_input("OpenAI API Key", type="password",
                                      placeholder="sk-...")
            if key_input:
                os.environ["OPENAI_API_KEY"] = key_input
                st.success("Key set for this session.")

        st.markdown("---")

        # Example questions
        st.markdown("**Example questions you can ask:**")
        examples = [
            "Which campaign has the highest conversion rate?",
            "Show me compliance violations by vertical this year",
            "Which agents are underperforming and need QA review?",
            "What is the AR recovery rate trend over the last 6 months?",
            "Compare healthcare appointment rates across campaigns",
            "Show me insurance leads by ACA eligibility and product type",
            "Which dialing mode has the lowest abandon rate?",
            "What are the top 5 agents by talk time?",
            "Show sentiment trend for all verticals month over month",
            "Which campaigns have the most compliance flags?",
        ]
        cols = st.columns(2)
        for i, ex in enumerate(examples):
            if cols[i % 2].button(ex, key=f"ex_{i}"):
                st.session_state["chat_input"] = ex

        st.markdown("---")

        # Chat history
        if "chat_history" not in st.session_state:
            st.session_state["chat_history"] = []

        # Display chat history
        for turn in st.session_state["chat_history"]:
            with st.chat_message("user"):
                st.markdown(turn["question"])
            with st.chat_message("assistant"):
                st.markdown(turn["answer"])
                with st.expander("Generated SQL"):
                    st.code(turn["sql"], language="sql")
                if turn.get("df") is not None and len(turn["df"]) > 0:
                    st.dataframe(turn["df"].head(15),
                                 use_container_width=True, hide_index=True)
                    auto_chart(turn["df"])

        # Input
        question = st.chat_input("Ask a question about your BPO data…")
        if not question and st.session_state.get("chat_input"):
            question = st.session_state.pop("chat_input")

        if question:
            with st.chat_message("user"):
                st.markdown(question)

            with st.chat_message("assistant"):
                with st.spinner("Thinking…"):
                    sql = generate_sql(question,
                                       st.session_state["chat_history"])
                    df, err = run_sql(sql)
                    answer = answer_question(question, df, sql)

                st.markdown(answer)
                with st.expander("Generated SQL"):
                    st.code(sql, language="sql")

                if err:
                    st.error(f"SQL Error: {err}")
                elif df is not None and len(df) > 0:
                    st.dataframe(df.head(20), use_container_width=True,
                                 hide_index=True)
                    auto_chart(df, title=question)
                    st.download_button(
                        "⬇ Download CSV",
                        df.to_csv(index=False).encode(),
                        file_name="chat_result.csv",
                        key=f"chat_dl_{len(st.session_state['chat_history'])}",
                    )

            st.session_state["chat_history"].append({
                "question": question,
                "sql": sql,
                "answer": answer,
                "df": df,
            })

        if st.session_state["chat_history"]:
            if st.button("🗑 Clear chat history"):
                st.session_state["chat_history"] = []
                st.rerun()

    # ── TAB 4: Self-Service BI ────────────────────────────────────────────────
    with tab4:
        st.markdown("### 📊 Self-Service BI Builder")
        st.markdown("Choose a table and fields to build your own chart — no SQL needed.")

        tables = [
            "gold_campaign_kpis",
            "gold_agent_performance",
            "gold_dialer_performance",
            "gold_compliance_summary",
            "gold_insurance_kpis",
            "gold_healthcare_kpis",
            "gold_realestate_kpis",
            "gold_ar_kpis",
            "gold_ml_feature_store",
            "gold_qa_agent_scores",
        ]

        col1, col2 = st.columns([2, 3])
        with col1:
            selected_table = st.selectbox("Table", tables, key="bi_table")

            @st.cache_data
            def get_table(name: str) -> pd.DataFrame:
                path = Path(__file__).parent.parent / "lakehouse" / "gold" / f"{name}.parquet"
                return pd.read_parquet(path) if path.exists() else pd.DataFrame()

            df_bi = get_table(selected_table)

            if not df_bi.empty:
                all_cols = list(df_bi.columns)
                num_cols = df_bi.select_dtypes(include="number").columns.tolist()
                cat_cols = df_bi.select_dtypes(
                    include=["object", "category"]).columns.tolist()

                chart_type = st.selectbox(
                    "Chart Type",
                    ["Bar", "Line", "Scatter", "Pie", "Histogram",
                     "Box", "Heatmap (Pivot)"],
                    key="bi_chart",
                )
                x_col = st.selectbox("X Axis", all_cols, key="bi_x",
                                     index=min(0, len(all_cols)-1))
                y_col = st.selectbox(
                    "Y Axis", num_cols if num_cols else all_cols,
                    key="bi_y",
                )
                color_col = st.selectbox(
                    "Color By (optional)", ["None"] + cat_cols, key="bi_color",
                )
                color_by = color_col if color_col != "None" else None

                row_limit = st.slider("Max rows", 10, 500, 100, key="bi_limit")
                agg_func = st.selectbox(
                    "Aggregation (if grouping)", ["None", "sum", "mean", "count", "max", "min"],
                    key="bi_agg",
                )

                build_btn = st.button("🔨 Build Chart", type="primary")

        with col2:
            if not df_bi.empty and build_btn:
                df_plot = df_bi.copy().head(row_limit)

                # Apply aggregation
                if agg_func != "None" and color_by:
                    agg_map = {"sum": "sum", "mean": "mean", "count": "count",
                               "max": "max", "min": "min"}
                    df_plot = (df_plot.groupby([x_col, color_by])[y_col]
                               .agg(agg_map[agg_func]).reset_index())
                elif agg_func != "None":
                    df_plot = (df_plot.groupby(x_col)[y_col]
                               .agg(agg_func).reset_index())

                fig = None
                try:
                    if chart_type == "Bar":
                        fig = px.bar(df_plot, x=x_col, y=y_col, color=color_by,
                                     barmode="group")
                    elif chart_type == "Line":
                        fig = px.line(df_plot, x=x_col, y=y_col, color=color_by,
                                      markers=True)
                    elif chart_type == "Scatter":
                        fig = px.scatter(df_plot, x=x_col, y=y_col, color=color_by,
                                         size=y_col if y_col in num_cols else None)
                    elif chart_type == "Pie":
                        fig = px.pie(df_plot, names=x_col, values=y_col, hole=0.35)
                    elif chart_type == "Histogram":
                        fig = px.histogram(df_plot, x=y_col, color=color_by, nbins=20)
                    elif chart_type == "Box":
                        fig = px.box(df_plot, x=color_by or x_col, y=y_col)
                    elif chart_type == "Heatmap (Pivot)" and color_by:
                        pivot = df_plot.pivot_table(
                            index=x_col, columns=color_by,
                            values=y_col, aggfunc="mean",
                        ).fillna(0)
                        fig = px.imshow(pivot, color_continuous_scale="Blues",
                                        aspect="auto")

                    if fig:
                        fig.update_layout(plot_bgcolor="white", height=450)
                        st.plotly_chart(fig, use_container_width=True)
                        st.download_button(
                            "⬇ Download Data",
                            df_plot.to_csv(index=False).encode(),
                            file_name=f"{selected_table}_{chart_type}.csv",
                        )

                except Exception as e:
                    st.error(f"Chart error: {e}")

            elif not df_bi.empty:
                st.markdown("#### Table Preview")
                st.dataframe(df_bi.head(20), use_container_width=True,
                             hide_index=True)
                c1_, c2_, c3_ = st.columns(3)
                c1_.metric("Rows", f"{len(df_bi):,}")
                c2_.metric("Columns", len(df_bi.columns))
                c3_.metric("Numeric Fields",
                           len(df_bi.select_dtypes(include="number").columns))
