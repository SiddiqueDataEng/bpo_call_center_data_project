"""
NLP Query Engine — Natural language → SQL, then execute via DuckDB.

Two modes:
  1. OpenAI GPT-4o (if OPENAI_API_KEY set)
  2. Local keyword-based pattern matching (no API key needed)
"""

from __future__ import annotations

import os
import re
from typing import Optional

SYSTEM_PROMPT = """You are an expert SQL analyst for a BPO call center platform.
You write DuckDB SQL queries against these tables (already registered as views):

TABLES:
- gold_campaign_kpis: campaign_id, name, vertical, dialing_mode, status, total_calls,
  total_converted, total_dnc, total_transfer, total_voicemail, total_no_answer,
  total_callback, avg_duration_seconds, total_talk_minutes, avg_sentiment,
  compliance_flags, unique_agents, unique_leads, first_call_date, last_call_date,
  conversion_rate, dnc_rate, client_id, created_at

- gold_agent_performance: agent_id, days_active, total_calls, total_interested,
  total_transfers, total_dnc, total_talk_time_seconds, avg_handle_time,
  avg_conversion_rate, min_conversion_rate, max_conversion_rate, days_below_threshold,
  consecutive_below_threshold_flag, total_talk_hours, first_name, last_name,
  role, performance_tier, vertical_specialization, base_conversion_rate,
  hire_date, tenure_days

- gold_dialer_performance: campaign_id, call_date, total_dials, answered, abandoned,
  avg_handle_time, peak_hour, active_agents, answer_rate, abandon_rate,
  above_fdcpa_abandon_threshold, vertical, dialing_mode

- gold_compliance_summary: campaign_id, vertical, call_month, total_calls,
  compliance_flags, compliance_flag_rate

- gold_insurance_kpis: campaign_id, call_month, total_calls, total_converted,
  total_transfers, aca_eligible_count, aca_subsidy_count, avg_annual_income,
  avg_household_size, avg_sentiment, compliance_flags, conversion_rate,
  aca_eligible_rate, product_auto, product_health, product_home, product_life

- gold_healthcare_kpis: campaign_id, call_month, total_calls,
  total_appointments_scheduled, total_converted, avg_sentiment, webhook_sent_count,
  confirmation_email_count, conversion_rate, appointment_rate,
  spec_cardiology, spec_dermatology, spec_endocrinology, spec_gastroenterology,
  spec_mental_health, spec_neurology, spec_oncology, spec_orthopedics,
  spec_primary_care, spec_pulmonology

- gold_realestate_kpis: campaign_id, call_month, total_calls, total_qualified,
  total_converted, total_agent_matched, avg_budget_min, avg_budget_max,
  avg_sentiment, conversion_rate, qualification_rate, lead_type_buyer, lead_type_seller

- gold_ar_kpis: campaign_id, call_month, total_calls, total_arrangements,
  total_converted, total_original_balance, total_settlement_amount,
  avg_settlement_pct, avg_sentiment, sol_expired_count, conversion_rate,
  arrangement_rate, recovery_rate

- gold_ml_feature_store: feature_row_id, lead_id, vertical, state, lead_score,
  dnc_flagged, n_call_attempts, avg_sentiment_score, has_consent, converted,
  predicted_score, global_predicted_score, vertical_enc, state_enc

- gold_qa_agent_scores: agent_id, total_reviews, avg_qa_score, min_qa_score, max_qa_score

RULES:
- Return ONLY the SQL query, no explanation, no markdown fences
- Use DuckDB syntax (STRFTIME, PERCENTILE_CONT, PIVOT supported)
- Always include meaningful column aliases
- Default LIMIT 500 unless aggregating
- Use CTEs for multi-step logic
"""


def generate_sql_openai(question: str, history: list[dict]) -> str:
    """Use OpenAI GPT-4o to generate SQL from natural language."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for h in history[-6:]:  # keep last 3 exchanges
            messages.append({"role": "user", "content": h["question"]})
            messages.append({"role": "assistant", "content": h["sql"]})
        messages.append({"role": "user", "content": question})
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0,
            max_tokens=600,
        )
        sql = resp.choices[0].message.content.strip()
        # Strip markdown fences if present
        sql = re.sub(r"^```sql\s*", "", sql)
        sql = re.sub(r"\s*```$", "", sql)
        return sql.strip()
    except Exception as e:
        return f"-- OpenAI error: {e}"


# ── Local fallback NLP ────────────────────────────────────────────────────────

_PATTERNS = [
    # conversion
    (r"(conversion|convert|converted).*(campaign|vertical|month)",
     "SELECT name AS campaign, vertical, ROUND(conversion_rate*100,2) AS conv_pct, "
     "total_calls, total_converted FROM gold_campaign_kpis ORDER BY conv_pct DESC LIMIT 20;"),

    (r"(top|best|highest).*(agent|agents)",
     "SELECT first_name||' '||last_name AS agent, performance_tier, "
     "ROUND(avg_conversion_rate*100,2) AS conv_pct, total_calls "
     "FROM gold_agent_performance ORDER BY conv_pct DESC LIMIT 10;"),

    (r"(worst|lowest|poor).*(agent|agents)",
     "SELECT first_name||' '||last_name AS agent, performance_tier, "
     "ROUND(avg_conversion_rate*100,2) AS conv_pct, days_below_threshold "
     "FROM gold_agent_performance ORDER BY conv_pct ASC LIMIT 10;"),

    (r"compliance|flag|violation|risk",
     "SELECT vertical, call_month, SUM(compliance_flags) AS flags, "
     "ROUND(AVG(compliance_flag_rate)*100,3) AS flag_rate_pct "
     "FROM gold_compliance_summary GROUP BY vertical, call_month "
     "ORDER BY flags DESC LIMIT 20;"),

    (r"abandon|fdcpa",
     "SELECT vertical, dialing_mode, ROUND(AVG(abandon_rate)*100,2) AS avg_abandon_pct, "
     "SUM(CAST(above_fdcpa_abandon_threshold AS INT)) AS fdcpa_violations "
     "FROM gold_dialer_performance GROUP BY vertical, dialing_mode "
     "ORDER BY avg_abandon_pct DESC;"),

    (r"(ar|debt|recovery|collect|arrangement|settlement)",
     "SELECT call_month, SUM(total_arrangements) AS arrangements, "
     "ROUND(SUM(total_settlement_amount),0) AS recovered, "
     "ROUND(AVG(recovery_rate)*100,2) AS recovery_pct "
     "FROM gold_ar_kpis GROUP BY call_month ORDER BY call_month;"),

    (r"(healthcare|appointment|appt|schedule)",
     "SELECT call_month, SUM(total_calls) AS calls, "
     "SUM(total_appointments_scheduled) AS appointments, "
     "ROUND(AVG(appointment_rate)*100,2) AS appt_rate_pct "
     "FROM gold_healthcare_kpis GROUP BY call_month ORDER BY call_month;"),

    (r"(insurance|aca|eligib)",
     "SELECT call_month, SUM(total_calls) AS calls, "
     "SUM(aca_eligible_count) AS aca_eligible, "
     "ROUND(AVG(aca_eligible_rate)*100,2) AS aca_rate_pct "
     "FROM gold_insurance_kpis GROUP BY call_month ORDER BY call_month;"),

    (r"(real.?estate|property|buyer|seller|budget)",
     "SELECT call_month, SUM(lead_type_buyer) AS buyers, "
     "SUM(lead_type_seller) AS sellers, SUM(total_qualified) AS qualified, "
     "ROUND(AVG(qualification_rate)*100,2) AS qual_pct "
     "FROM gold_realestate_kpis GROUP BY call_month ORDER BY call_month;"),

    (r"(ml|model|score|predict|propensity)",
     "SELECT vertical, ROUND(AVG(predicted_score),1) AS avg_predicted_score, "
     "ROUND(AVG(CAST(converted AS DOUBLE))*100,2) AS actual_conv_pct, "
     "COUNT(*) AS leads "
     "FROM gold_ml_feature_store WHERE predicted_score IS NOT NULL "
     "GROUP BY vertical ORDER BY avg_predicted_score DESC;"),

    (r"(qa|quality|review|rubric|score)",
     "SELECT a.first_name||' '||a.last_name AS agent, "
     "q.total_reviews, ROUND(q.avg_qa_score,2) AS qa_score, "
     "a.performance_tier "
     "FROM gold_qa_agent_scores q "
     "JOIN gold_agent_performance a USING(agent_id) "
     "ORDER BY qa_score DESC LIMIT 20;"),

    (r"(trend|over.?time|monthly|month)",
     "SELECT STRFTIME(CAST(call_date AS DATE),'%Y-%m') AS month, "
     "SUM(total_dials) AS dials, SUM(answered) AS answered, "
     "ROUND(AVG(answer_rate)*100,2) AS answer_pct "
     "FROM gold_dialer_performance GROUP BY month ORDER BY month;"),

    (r"(dialer|dial|predictive|progressive|preview)",
     "SELECT dialing_mode, COUNT(*) AS days, "
     "SUM(total_dials) AS dials, ROUND(AVG(answer_rate)*100,2) AS avg_answer_pct, "
     "ROUND(AVG(abandon_rate)*100,2) AS avg_abandon_pct "
     "FROM gold_dialer_performance GROUP BY dialing_mode;"),

    (r"(sentiment|feeling|mood|emotion)",
     "SELECT vertical, call_month, ROUND(AVG(avg_sentiment),4) AS avg_sentiment "
     "FROM (SELECT 'Insurance' AS vertical, call_month, avg_sentiment FROM gold_insurance_kpis "
     "UNION ALL SELECT 'Healthcare', call_month, avg_sentiment FROM gold_healthcare_kpis "
     "UNION ALL SELECT 'RealEstate', call_month, avg_sentiment FROM gold_realestate_kpis "
     "UNION ALL SELECT 'AR', call_month, avg_sentiment FROM gold_ar_kpis) t "
     "GROUP BY vertical, call_month ORDER BY vertical, call_month;"),

    (r"(campaign|campaigns).*(status|active|closed)",
     "SELECT name, vertical, status, total_calls, "
     "ROUND(conversion_rate*100,2) AS conv_pct "
     "FROM gold_campaign_kpis ORDER BY status, conv_pct DESC;"),

    # fallback
    (r".*",
     "SELECT name AS campaign, vertical, total_calls, "
     "ROUND(conversion_rate*100,2) AS conv_pct, "
     "compliance_flags, ROUND(avg_sentiment,3) AS sentiment "
     "FROM gold_campaign_kpis ORDER BY conv_pct DESC;"),
]


def generate_sql_local(question: str) -> str:
    """Keyword/regex-based NLP fallback — no API key needed."""
    q = question.lower()
    for pattern, sql in _PATTERNS:
        if re.search(pattern, q):
            return f"-- Auto-generated (local NLP)\n{sql}"
    return ("SELECT name, vertical, total_calls, "
            "ROUND(conversion_rate*100,2) AS conv_pct "
            "FROM gold_campaign_kpis ORDER BY conv_pct DESC LIMIT 20;")


def generate_sql(question: str, history: list[dict] | None = None) -> str:
    """Generate SQL from natural language — OpenAI if available, else local."""
    if os.environ.get("OPENAI_API_KEY"):
        return generate_sql_openai(question, history or [])
    return generate_sql_local(question)


def answer_question(question: str, result_df, sql: str) -> str:
    """Generate a natural language answer from query results."""
    if result_df is None or len(result_df) == 0:
        return "The query returned no results."

    n = len(result_df)
    cols = list(result_df.columns)

    # Try OpenAI for rich answer
    if os.environ.get("OPENAI_API_KEY"):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
            sample = result_df.head(10).to_string(index=False)
            prompt = (f"Question: {question}\n\nSQL used:\n{sql}\n\n"
                      f"Results ({n} rows, sample):\n{sample}\n\n"
                      "Provide a concise 2-4 sentence business insight. "
                      "Mention specific numbers. No markdown.")
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3, max_tokens=200,
            )
            return resp.choices[0].message.content.strip()
        except Exception:
            pass

    # Local fallback — template answer
    row = result_df.iloc[0]
    summary_parts = [f"Query returned **{n} row(s)** with columns: {', '.join(cols[:5])}."]
    # Find numeric cols and report top value
    for col in cols:
        if result_df[col].dtype in ("float64", "int64", "Int64"):
            try:
                top_val = result_df[col].max()
                summary_parts.append(f"Highest **{col}**: **{top_val}**.")
                break
            except Exception:
                pass
    return " ".join(summary_parts)
