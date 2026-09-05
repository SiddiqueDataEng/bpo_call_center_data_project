"""
AI Chat Page — Natural language Q&A with automatic chart generation.
Works without API key (local NLP). Upgrade to GPT-4o by setting OPENAI_API_KEY.
"""
from __future__ import annotations
import os
from pathlib import Path
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from .nlp_engine import generate_sql, answer_question

GOLD = Path(__file__).parent.parent / "lakehouse" / "gold"

CHART_KEYWORDS = {
    "trend": "line", "over time": "line", "monthly": "line",
    "compare": "bar", "comparison": "bar", "vs": "bar",
    "distribution": "histogram", "breakdown": "pie",
    "scatter": "scatter", "correlation": "scatter",
    "top": "bar", "bottom": "bar", "rank": "bar",
    "rate": "line", "percentage": "bar",
}

SUGGESTED_QUESTIONS = [
    ("📈 Performance", [
        "Which campaign has the highest conversion rate?",
        "Show me top 5 agents by talk time",
        "Compare conversion rates across all verticals",
        "Which dialing mode performs best?",
    ]),
    ("⚠️ Compliance", [
        "Which vertical has the most compliance flags?",
        "Show FDCPA abandon rate violations by campaign",
        "What is the DNC rate trend over time?",
        "Which campaigns have compliance flag rates above 5%?",
    ]),
    ("💰 Revenue", [
        "What is the AR recovery rate by month?",
        "Show total settlement amounts recovered",
        "Which AR campaign recovered the most money?",
        "Estimate revenue potential across verticals",
    ]),
    ("🤖 ML Insights", [
        "Show lead score distribution by vertical",
        "Which leads have the highest predicted conversion score?",
        "Compare actual vs predicted conversion rates",
        "Show sentiment trend for all verticals",
    ]),
    ("👥 Agents", [
        "Which agents are flagged for QA review?",
        "Show agent performance by tier",
        "What is the average QA score per agent?",
        "Show agents with the most days below threshold",
    ]),
]


@st.cache_resource
def get_db():
    con = duckdb.connect(":memory:")
    for pq in GOLD.glob("*.parquet"):
        con.execute(
            f"CREATE OR REPLACE VIEW {pq.stem} AS "
            f"SELECT * FROM read_parquet('{pq.as_posix()}')"
        )
    return con


def run_sql(sql: str):
    try:
        return get_db().execute(sql).df(), None
    except Exception as e:
        return None, str(e)


def detect_chart_type(question: str, df: pd.DataFrame) -> str:
    q = question.lower()
    for kw, chart in CHART_KEYWORDS.items():
        if kw in q:
            return chart
    num = df.select_dtypes(include="number").columns.tolist()
    str_c = df.select_dtypes(include=["object", "category"]).columns.tolist()
    if str_c and any(
        df[str_c[0]].astype(str).str.match(r"\d{4}-\d{2}").any()
        for _ in str_c[:1]
    ):
        return "line"
    if len(num) == 1 and str_c:
        return "bar"
    if len(num) >= 2:
        return "scatter"
    return "bar"


def build_chart(df: pd.DataFrame, chart_type: str, title: str) -> go.Figure | None:
    if df is None or df.empty:
        return None
    num = df.select_dtypes(include="number").columns.tolist()
    cat = df.select_dtypes(include=["object", "category"]).columns.tolist()
    if not num:
        return None

    colors = px.colors.qualitative.Set2
    try:
        if chart_type == "line" and cat:
            fig = px.line(df.head(50), x=cat[0], y=num[:3],
                          title=title, markers=True,
                          color_discrete_sequence=["#1A56DB", "#057A55", "#C27803"])
        elif chart_type == "bar" and cat:
            fig = px.bar(df.head(20), x=cat[0], y=num[0],
                         color=num[0], title=title,
                         color_continuous_scale="Blues",
                         text_auto=".2s")
            fig.update_layout(coloraxis_showscale=False)
        elif chart_type == "histogram":
            fig = px.histogram(df, x=num[0], nbins=20, title=title,
                               color_discrete_sequence=["#1A56DB"])
        elif chart_type == "pie" and cat:
            fig = px.pie(df.head(8), names=cat[0], values=num[0],
                         title=title, hole=0.4)
        elif chart_type == "scatter" and len(num) >= 2:
            fig = px.scatter(df.head(200), x=num[0], y=num[1],
                             color=cat[0] if cat else None,
                             title=title, size_max=14)
        else:
            if cat and num:
                fig = px.bar(df.head(20), x=cat[0], y=num[0],
                             title=title, color_discrete_sequence=["#1A56DB"])
            else:
                return None

        fig.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            height=380,
            margin=dict(t=48, b=16, l=16, r=16),
            font=dict(family="Inter, sans-serif", size=12),
            title_font_size=14,
        )
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(gridcolor="#F3F4F6")
        return fig
    except Exception:
        return None


def render_ai_chat_page() -> None:
    st.markdown("# 🤖 AI Data Assistant")
    st.markdown(
        "*Ask anything about the BPO platform in plain English. "
        "Get instant answers, data tables, and auto-generated charts.*"
    )

    has_openai = bool(os.environ.get("OPENAI_API_KEY"))

    # Top status bar
    col_s1, col_s2, col_s3 = st.columns(3)
    if has_openai:
        col_s1.success("✅ GPT-4o Connected")
    else:
        col_s1.info("💡 Local NLP Active")
    col_s2.metric("Questions Asked",
                  len(st.session_state.get("ai_history", [])))
    col_s3.metric("Charts Generated",
                  sum(1 for t in st.session_state.get("ai_history", [])
                      if t.get("fig") is not None))

    # API key expander
    with st.expander("🔑 Connect OpenAI for smarter answers (optional)"):
        st.markdown(
            "Without an API key, the assistant uses built-in keyword NLP. "
            "With GPT-4o, it understands complex questions and generates precise SQL."
        )
        key_in = st.text_input("OpenAI API Key", type="password",
                               placeholder="sk-...", key="ai_key_input")
        if key_in:
            os.environ["OPENAI_API_KEY"] = key_in
            st.success("Key set for this session. Reload the page to activate.")

    st.markdown("---")

    # Suggested questions grid
    st.markdown("#### 💬 Try these questions")
    for category, questions in SUGGESTED_QUESTIONS:
        st.markdown(f"**{category}**")
        q_cols = st.columns(len(questions))
        for i, q in enumerate(questions):
            if q_cols[i].button(q, key=f"sugg_{category}_{i}",
                                use_container_width=True):
                st.session_state["ai_pending"] = q
        st.markdown("")

    st.markdown("---")

    # Initialise history
    if "ai_history" not in st.session_state:
        st.session_state["ai_history"] = []

    # Render chat history
    for turn in st.session_state["ai_history"]:
        with st.chat_message("user", avatar="👤"):
            st.markdown(f"**{turn['question']}**")

        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(turn["answer"])

            has_fig = bool(turn.get("fig"))
            if has_fig:
                c1, c2 = st.columns([1, 1])
            else:
                c1 = st.container()
                c2 = None
            if turn.get("df") is not None and len(turn["df"]) > 0:
                with c1:
                    with st.expander("📋 Data Table", expanded=not has_fig):
                        st.dataframe(
                            turn["df"].head(20),
                            use_container_width=True,
                            hide_index=True,
                        )
                        st.download_button(
                            "⬇ CSV",
                            turn["df"].to_csv(index=False).encode(),
                            file_name="ai_result.csv",
                            key=f"dl_hist_{id(turn)}",
                        )
            if has_fig and c2 is not None:
                with c2:
                    st.plotly_chart(turn["fig"],
                                    use_container_width=True,
                                    key=f"fig_hist_{id(turn)}")

            with st.expander("🔍 Generated SQL"):
                st.code(turn["sql"], language="sql")

    # New question input
    question = st.chat_input("Ask a question about your BPO data…",
                             key="ai_chat_input")
    if not question and st.session_state.get("ai_pending"):
        question = st.session_state.pop("ai_pending")

    if question:
        with st.chat_message("user", avatar="👤"):
            st.markdown(f"**{question}**")

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Analysing your question…"):
                sql = generate_sql(question, st.session_state["ai_history"])
                df, err = run_sql(sql)
                answer = answer_question(question, df, sql)
                fig = None
                if df is not None and len(df) > 0:
                    chart_type = detect_chart_type(question, df)
                    fig = build_chart(df, chart_type, title=question[:60])

            st.markdown(answer)

            if fig:
                col1, col2 = st.columns([1, 1])
            else:
                col1 = st.container()
                col2 = None
            if df is not None and len(df) > 0:
                with col1:
                    with st.expander("📋 Data Table", expanded=fig is None):
                        st.dataframe(df.head(20), use_container_width=True,
                                     hide_index=True)
                        st.download_button(
                            "⬇ Download CSV",
                            df.to_csv(index=False).encode(),
                            file_name="ai_result.csv",
                            key=f"dl_new_{len(st.session_state['ai_history'])}",
                        )
            if fig and col2 is not None:
                with col2:
                    st.plotly_chart(fig, use_container_width=True,
                                    key=f"fig_new_{len(st.session_state['ai_history'])}")

            if err:
                st.error(f"SQL Error: {err}")

            with st.expander("🔍 Generated SQL"):
                st.code(sql, language="sql")

        st.session_state["ai_history"].append({
            "question": question,
            "sql": sql,
            "answer": answer,
            "df": df,
            "fig": fig,
        })

    # Clear button
    if st.session_state.get("ai_history"):
        st.markdown("---")
        if st.button("🗑 Clear conversation", key="ai_clear"):
            st.session_state["ai_history"] = []
            st.rerun()
