"""SQL query catalog — Basic to Advanced, Window Functions, CTEs, Analytics."""

QUERIES = {}

# ── BASIC ─────────────────────────────────────────────────────────────────────

QUERIES["B1 – Campaign Overview"] = {
    "level": "Basic",
    "description": "Total calls, conversions, and conversion rate per campaign.",
    "sql": """
SELECT
    name                                    AS campaign,
    vertical,
    dialing_mode,
    status,
    total_calls,
    total_converted,
    ROUND(conversion_rate * 100, 2)         AS conv_rate_pct,
    ROUND(avg_duration_seconds / 60.0, 1)   AS avg_duration_min,
    compliance_flags
FROM gold_campaign_kpis
ORDER BY conv_rate_pct DESC;
""".strip(),
}

QUERIES["B2 – Top 10 Agents by Conversion"] = {
    "level": "Basic",
    "description": "Rank agents by average conversion rate.",
    "sql": """
SELECT
    first_name || ' ' || last_name          AS agent_name,
    role,
    performance_tier,
    total_calls,
    ROUND(avg_conversion_rate * 100, 2)     AS avg_conv_pct,
    ROUND(total_talk_hours, 1)              AS talk_hours,
    consecutive_below_threshold_flag        AS needs_qa_review
FROM gold_agent_performance
ORDER BY avg_conv_pct DESC
LIMIT 10;
""".strip(),
}

QUERIES["B3 – Monthly Call Volume"] = {
    "level": "Basic",
    "description": "Total dials and answered calls by month.",
    "sql": """
SELECT
    STRFTIME(CAST(call_date AS DATE), '%Y-%m')    AS month,
    SUM(total_dials)                AS total_dials,
    SUM(answered)                   AS answered,
    SUM(abandoned)                  AS abandoned,
    ROUND(AVG(answer_rate)*100, 2)  AS avg_answer_rate_pct
FROM gold_dialer_performance
GROUP BY month
ORDER BY month;
""".strip(),
}

QUERIES["B4 – DNC & Compliance Summary"] = {
    "level": "Basic",
    "description": "Compliance flag counts and rates by vertical.",
    "sql": """
SELECT
    vertical,
    SUM(total_calls)                        AS total_calls,
    SUM(compliance_flags)                   AS total_flags,
    ROUND(AVG(compliance_flag_rate)*100,2)  AS avg_flag_rate_pct
FROM gold_compliance_summary
GROUP BY vertical
ORDER BY total_flags DESC;
""".strip(),
}

QUERIES["B5 – AR Recovery Summary"] = {
    "level": "Basic",
    "description": "Debt recovery totals across AR campaigns.",
    "sql": """
SELECT
    call_month,
    SUM(total_calls)                            AS calls,
    SUM(total_arrangements)                     AS arrangements,
    ROUND(SUM(total_original_balance),2)        AS original_balance,
    ROUND(SUM(total_settlement_amount),2)       AS recovered,
    ROUND(AVG(avg_settlement_pct)*100,2)        AS avg_settlement_pct,
    ROUND(AVG(recovery_rate)*100,2)             AS recovery_rate_pct
FROM gold_ar_kpis
GROUP BY call_month
ORDER BY call_month;
""".strip(),
}

# ── INTERMEDIATE ──────────────────────────────────────────────────────────────

QUERIES["I1 – Vertical Performance Comparison"] = {
    "level": "Intermediate",
    "description": "Side-by-side KPI comparison across all four verticals.",
    "sql": """
SELECT
    vertical,
    SUM(total_calls)                        AS total_calls,
    SUM(total_converted)                    AS converted,
    ROUND(SUM(total_converted)*100.0
          / NULLIF(SUM(total_calls),0), 2)  AS conv_rate_pct,
    ROUND(AVG(avg_sentiment),4)             AS avg_sentiment,
    SUM(compliance_flags)                   AS compliance_flags,
    ROUND(AVG(avg_duration_seconds)/60,1)   AS avg_duration_min
FROM gold_campaign_kpis
GROUP BY vertical
ORDER BY conv_rate_pct DESC;
""".strip(),
}

QUERIES["I2 – Healthcare Appointment Funnel"] = {
    "level": "Intermediate",
    "description": "Calls → appointments → webhooks sent funnel.",
    "sql": """
SELECT
    call_month,
    SUM(total_calls)                            AS calls,
    SUM(total_appointments_scheduled)           AS appointments,
    SUM(webhook_sent_count)                     AS webhooks_sent,
    SUM(confirmation_email_count)               AS confirmations,
    ROUND(SUM(total_appointments_scheduled)*100.0
          / NULLIF(SUM(total_calls),0),2)       AS appt_rate_pct,
    ROUND(SUM(webhook_sent_count)*100.0
          / NULLIF(SUM(total_appointments_scheduled),0),2) AS webhook_success_pct
FROM gold_healthcare_kpis
GROUP BY call_month
ORDER BY call_month;
""".strip(),
}

QUERIES["I3 – Insurance ACA Eligibility Breakdown"] = {
    "level": "Intermediate",
    "description": "ACA eligible vs subsidy eligible vs total leads by month.",
    "sql": """
SELECT
    call_month,
    SUM(total_calls)                                        AS calls,
    SUM(aca_eligible_count)                                 AS aca_eligible,
    SUM(aca_subsidy_count)                                  AS subsidy_eligible,
    ROUND(SUM(aca_eligible_count)*100.0
          / NULLIF(SUM(total_calls),0),2)                   AS aca_rate_pct,
    ROUND(SUM(aca_subsidy_count)*100.0
          / NULLIF(SUM(aca_eligible_count),0),2)            AS subsidy_of_aca_pct,
    ROUND(AVG(avg_annual_income),0)                         AS avg_income,
    ROUND(AVG(avg_household_size),1)                        AS avg_household_size
FROM gold_insurance_kpis
GROUP BY call_month
ORDER BY call_month;
""".strip(),
}

QUERIES["I4 – Dialer FDCPA Violation Days"] = {
    "level": "Intermediate",
    "description": "Days where abandon rate exceeded the 3% FDCPA threshold per campaign.",
    "sql": """
SELECT
    campaign_id,
    vertical,
    dialing_mode,
    COUNT(*)                                        AS total_days,
    SUM(CAST(above_fdcpa_abandon_threshold AS INT))  AS violation_days,
    ROUND(SUM(CAST(above_fdcpa_abandon_threshold AS INT))*100.0
          / COUNT(*), 2)                            AS violation_rate_pct,
    ROUND(AVG(abandon_rate)*100,2)                  AS avg_abandon_pct,
    MAX(abandon_rate)*100                           AS peak_abandon_pct
FROM gold_dialer_performance
GROUP BY campaign_id, vertical, dialing_mode
ORDER BY violation_days DESC;
""".strip(),
}

QUERIES["I5 – Real Estate Budget Segments"] = {
    "level": "Intermediate",
    "description": "Buyer vs seller lead distribution and budget by month.",
    "sql": """
SELECT
    call_month,
    SUM(lead_type_buyer)                                AS buyers,
    SUM(lead_type_seller)                               AS sellers,
    SUM(total_qualified)                                AS qualified,
    SUM(total_agent_matched)                            AS agent_matched,
    ROUND(AVG(avg_budget_min)/1000,0)                   AS avg_budget_min_k,
    ROUND(AVG(avg_budget_max)/1000,0)                   AS avg_budget_max_k,
    ROUND(SUM(total_qualified)*100.0
          / NULLIF(SUM(total_calls),0),2)               AS qualification_rate_pct
FROM gold_realestate_kpis
GROUP BY call_month
ORDER BY call_month;
""".strip(),
}

# ── WINDOW FUNCTIONS ──────────────────────────────────────────────────────────

QUERIES["W1 – Running Conversion Rate (Campaign)"] = {
    "level": "Window Functions",
    "description": "Cumulative running conversion rate over time per campaign using SUM OVER.",
    "sql": """
SELECT
    campaign_id,
    call_month,
    total_calls,
    total_converted,
    ROUND(conversion_rate * 100, 2)                 AS monthly_conv_pct,
    SUM(total_calls)
        OVER (PARTITION BY campaign_id
              ORDER BY call_month
              ROWS UNBOUNDED PRECEDING)             AS running_calls,
    SUM(total_converted)
        OVER (PARTITION BY campaign_id
              ORDER BY call_month
              ROWS UNBOUNDED PRECEDING)             AS running_converted,
    ROUND(
        SUM(total_converted)
            OVER (PARTITION BY campaign_id
                  ORDER BY call_month
                  ROWS UNBOUNDED PRECEDING) * 100.0
        / NULLIF(SUM(total_calls)
            OVER (PARTITION BY campaign_id
                  ORDER BY call_month
                  ROWS UNBOUNDED PRECEDING), 0)
    , 2)                                            AS running_conv_pct
FROM gold_insurance_kpis
ORDER BY campaign_id, call_month;
""".strip(),
}

QUERIES["W2 – Agent Conversion Rank by Tier"] = {
    "level": "Window Functions",
    "description": "Rank agents within each performance tier using RANK() OVER.",
    "sql": """
SELECT
    first_name || ' ' || last_name              AS agent_name,
    performance_tier,
    vertical_specialization,
    ROUND(avg_conversion_rate * 100, 2)         AS conv_pct,
    RANK() OVER (
        PARTITION BY performance_tier
        ORDER BY avg_conversion_rate DESC
    )                                           AS tier_rank,
    ROUND(avg_conversion_rate * 100, 2)
        - ROUND(AVG(avg_conversion_rate)
            OVER (PARTITION BY performance_tier) * 100, 2)
                                                AS vs_tier_avg_pct
FROM gold_agent_performance
ORDER BY performance_tier, tier_rank;
""".strip(),
}

QUERIES["W3 – Month-over-Month Call Volume Change"] = {
    "level": "Window Functions",
    "description": "LAG() to compute MoM dial volume change per vertical.",
    "sql": """
WITH monthly AS (
    SELECT
        vertical,
        STRFTIME(CAST(call_date AS DATE), '%Y-%m')    AS month,
        SUM(total_dials)                AS dials
    FROM gold_dialer_performance
    GROUP BY vertical, month
)
SELECT
    vertical,
    month,
    dials,
    LAG(dials) OVER (
        PARTITION BY vertical
        ORDER BY month
    )                                           AS prev_month_dials,
    ROUND(
        (dials - LAG(dials) OVER (
            PARTITION BY vertical ORDER BY month
        )) * 100.0
        / NULLIF(LAG(dials) OVER (
            PARTITION BY vertical ORDER BY month
        ), 0)
    , 2)                                        AS mom_change_pct
FROM monthly
ORDER BY vertical, month;
""".strip(),
}

QUERIES["W4 – 3-Month Rolling Avg Abandon Rate"] = {
    "level": "Window Functions",
    "description": "Rolling 3-month average abandon rate per dialing mode.",
    "sql": """
WITH monthly_mode AS (
    SELECT
        dialing_mode,
        STRFTIME(CAST(call_date AS DATE), '%Y-%m')    AS month,
        ROUND(AVG(abandon_rate)*100,4)  AS avg_abandon_pct
    FROM gold_dialer_performance
    GROUP BY dialing_mode, month
)
SELECT
    dialing_mode,
    month,
    avg_abandon_pct,
    ROUND(AVG(avg_abandon_pct) OVER (
        PARTITION BY dialing_mode
        ORDER BY month
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ), 4)                               AS rolling_3m_avg,
    MIN(avg_abandon_pct) OVER (
        PARTITION BY dialing_mode
    )                                   AS all_time_min,
    MAX(avg_abandon_pct) OVER (
        PARTITION BY dialing_mode
    )                                   AS all_time_max
FROM monthly_mode
ORDER BY dialing_mode, month;
""".strip(),
}

QUERIES["W5 – AR Recovery Rate Percentile"] = {
    "level": "Window Functions",
    "description": "NTILE and PERCENT_RANK to bucket campaigns by recovery rate.",
    "sql": """
SELECT
    campaign_id,
    call_month,
    ROUND(recovery_rate * 100, 2)       AS recovery_pct,
    NTILE(4) OVER (
        ORDER BY recovery_rate
    )                                   AS quartile,
    ROUND(PERCENT_RANK() OVER (
        ORDER BY recovery_rate
    ) * 100, 1)                         AS percentile,
    ROUND(recovery_rate * 100, 2)
        - ROUND(AVG(recovery_rate) OVER () * 100, 2)
                                        AS vs_overall_avg
FROM gold_ar_kpis
WHERE recovery_rate IS NOT NULL
ORDER BY recovery_pct DESC;
""".strip(),
}

# ── CTEs ──────────────────────────────────────────────────────────────────────

QUERIES["C1 – Campaign Performance Tiers (CTE)"] = {
    "level": "CTEs",
    "description": "Multi-step CTE: compute stats → bucket campaigns into tiers.",
    "sql": """
WITH campaign_stats AS (
    SELECT
        name,
        vertical,
        dialing_mode,
        total_calls,
        total_converted,
        ROUND(conversion_rate * 100, 2)     AS conv_pct,
        compliance_flags,
        avg_sentiment
    FROM gold_campaign_kpis
),
tier_thresholds AS (
    SELECT
        PERCENTILE_CONT(0.67) WITHIN GROUP
            (ORDER BY conv_pct)             AS p67,
        PERCENTILE_CONT(0.33) WITHIN GROUP
            (ORDER BY conv_pct)             AS p33
    FROM campaign_stats
),
tiered AS (
    SELECT
        cs.*,
        CASE
            WHEN cs.conv_pct >= tt.p67 THEN 'Top Tier'
            WHEN cs.conv_pct >= tt.p33 THEN 'Mid Tier'
            ELSE 'Needs Improvement'
        END                                 AS performance_tier
    FROM campaign_stats cs
    CROSS JOIN tier_thresholds tt
)
SELECT
    performance_tier,
    COUNT(*)                                AS campaigns,
    ROUND(AVG(conv_pct),2)                  AS avg_conv_pct,
    ROUND(AVG(avg_sentiment),4)             AS avg_sentiment,
    SUM(compliance_flags)                   AS total_flags
FROM tiered
GROUP BY performance_tier
ORDER BY avg_conv_pct DESC;
""".strip(),
}

QUERIES["C2 – Agent Below-Threshold Streak Analysis (CTE)"] = {
    "level": "CTEs",
    "description": "Find agents flagged with consecutive below-threshold days, enriched with QA scores.",
    "sql": """
WITH flagged_agents AS (
    SELECT
        agent_id,
        first_name || ' ' || last_name      AS agent_name,
        performance_tier,
        days_below_threshold,
        avg_conversion_rate,
        consecutive_below_threshold_flag
    FROM gold_agent_performance
    WHERE consecutive_below_threshold_flag = TRUE
),
qa_scores AS (
    SELECT
        agent_id,
        ROUND(avg_qa_score, 2)              AS qa_score,
        total_reviews
    FROM gold_qa_agent_scores
),
enriched AS (
    SELECT
        fa.*,
        COALESCE(qs.qa_score, 0)            AS latest_qa_score,
        COALESCE(qs.total_reviews, 0)       AS qa_review_count,
        CASE
            WHEN COALESCE(qs.qa_score, 0) < 2.5 THEN 'Critical'
            WHEN COALESCE(qs.qa_score, 0) < 3.5 THEN 'At Risk'
            ELSE 'Monitor'
        END                                 AS risk_level
    FROM flagged_agents fa
    LEFT JOIN qa_scores qs USING (agent_id)
)
SELECT * FROM enriched
ORDER BY risk_level, latest_qa_score ASC;
""".strip(),
}

QUERIES["C3 – Vertical Revenue Potential (CTE)"] = {
    "level": "CTEs",
    "description": "Estimate revenue potential per vertical using conversion and volume.",
    "sql": """
WITH vertical_totals AS (
    SELECT
        vertical,
        SUM(total_calls)                            AS calls,
        SUM(total_converted)                        AS converted,
        ROUND(SUM(total_converted)*100.0
              / NULLIF(SUM(total_calls),0),2)       AS conv_pct,
        ROUND(AVG(avg_duration_seconds)/60,1)       AS avg_duration_min
    FROM gold_campaign_kpis
    GROUP BY vertical
),
ar_revenue AS (
    SELECT
        'AR'                                        AS vertical,
        ROUND(SUM(total_settlement_amount),0)       AS recovered_usd
    FROM gold_ar_kpis
),
combined AS (
    SELECT
        vt.vertical,
        vt.calls,
        vt.converted,
        vt.conv_pct,
        vt.avg_duration_min,
        COALESCE(ar.recovered_usd, 0)               AS direct_revenue_usd,
        ROUND(vt.converted * CASE vt.vertical
            WHEN 'Insurance'  THEN 185
            WHEN 'Healthcare' THEN 120
            WHEN 'RealEstate' THEN 450
            ELSE 0
        END, 0)                                     AS estimated_referral_value
    FROM vertical_totals vt
    LEFT JOIN ar_revenue ar ON vt.vertical = ar.vertical
)
SELECT
    vertical,
    calls,
    converted,
    conv_pct,
    direct_revenue_usd,
    estimated_referral_value,
    direct_revenue_usd + estimated_referral_value   AS total_revenue_estimate
FROM combined
ORDER BY total_revenue_estimate DESC;
""".strip(),
}

QUERIES["C4 – Monthly Compliance Risk Score (CTE)"] = {
    "level": "CTEs",
    "description": "Composite risk score combining compliance flags, abandon rate, and DNC rate.",
    "sql": """
WITH compliance_monthly AS (
    SELECT
        vertical,
        call_month,
        ROUND(AVG(compliance_flag_rate)*100, 4)     AS flag_rate_pct
    FROM gold_compliance_summary
    GROUP BY vertical, call_month
),
dialer_monthly AS (
    SELECT
        vertical,
        STRFTIME(CAST(call_date AS DATE),'%Y-%m')  AS call_month,
        ROUND(AVG(abandon_rate)*100, 4)              AS abandon_rate_pct,
        ROUND(SUM(CAST(above_fdcpa_abandon_threshold AS INT))*100.0
              / COUNT(*), 2)                         AS fdcpa_violation_pct
    FROM gold_dialer_performance
    GROUP BY vertical, STRFTIME(CAST(call_date AS DATE),'%Y-%m')
),
dnc_summary AS (
    SELECT vertical, ROUND(AVG(dnc_rate)*100, 4) AS dnc_rate_pct
    FROM gold_campaign_kpis
    GROUP BY vertical
),
risk_score AS (
    SELECT
        cm.vertical,
        cm.call_month,
        cm.flag_rate_pct,
        COALESCE(dm.abandon_rate_pct, 0)            AS abandon_rate_pct,
        COALESCE(dm.fdcpa_violation_pct, 0)         AS fdcpa_pct,
        COALESCE(dn.dnc_rate_pct, 0)                AS dnc_rate_pct,
        ROUND(
            cm.flag_rate_pct * 0.35
            + COALESCE(dm.fdcpa_violation_pct, 0) * 0.30
            + COALESCE(dn.dnc_rate_pct, 0) * 0.20
            + COALESCE(dm.abandon_rate_pct, 0) * 0.15
        , 4)                                        AS composite_risk_score
    FROM compliance_monthly cm
    LEFT JOIN dialer_monthly dm
        ON cm.vertical = dm.vertical AND cm.call_month = dm.call_month
    LEFT JOIN dnc_summary dn ON cm.vertical = dn.vertical
)
SELECT *,
    CASE
        WHEN composite_risk_score > 10 THEN 'HIGH'
        WHEN composite_risk_score > 4  THEN 'MEDIUM'
        ELSE 'LOW'
    END AS risk_level
FROM risk_score
ORDER BY composite_risk_score DESC;
""".strip(),
}

QUERIES["A1 – Full Campaign Performance Matrix"] = {
    "level": "Advanced",
    "description": "Join all KPI tables into one executive matrix with vertical-specific metrics.",
    "sql": """
WITH base AS (
    SELECT
        c.name                              AS campaign,
        c.vertical,
        c.dialing_mode,
        c.status,
        c.total_calls,
        ROUND(c.conversion_rate*100,2)      AS conv_pct,
        ROUND(c.avg_sentiment,3)            AS sentiment,
        c.compliance_flags,
        ROUND(c.total_talk_minutes/60,1)    AS talk_hours
    FROM gold_campaign_kpis c
),
ins_agg AS (
    SELECT campaign_id,
        ROUND(AVG(aca_eligible_rate)*100,2) AS aca_eligible_pct
    FROM gold_insurance_kpis GROUP BY campaign_id
),
hc_agg AS (
    SELECT campaign_id,
        ROUND(AVG(appointment_rate)*100,2)  AS appt_rate_pct
    FROM gold_healthcare_kpis GROUP BY campaign_id
),
re_agg AS (
    SELECT campaign_id,
        ROUND(AVG(qualification_rate)*100,2) AS qual_rate_pct
    FROM gold_realestate_kpis GROUP BY campaign_id
),
ar_agg AS (
    SELECT campaign_id,
        ROUND(AVG(recovery_rate)*100,2)     AS recovery_pct,
        ROUND(SUM(total_settlement_amount),0) AS total_recovered
    FROM gold_ar_kpis GROUP BY campaign_id
)
SELECT
    b.*,
    COALESCE(i.aca_eligible_pct,  NULL)     AS ins_aca_pct,
    COALESCE(h.appt_rate_pct, NULL)                 AS hc_appt_pct,
    COALESCE(r.qual_rate_pct, NULL)                 AS re_qual_pct,
    COALESCE(a.recovery_pct, NULL)                  AS ar_recovery_pct,
    COALESCE(a.total_recovered, 0)          AS ar_recovered_usd
FROM base b
LEFT JOIN gold_campaign_kpis ck ON b.campaign = ck.name
LEFT JOIN ins_agg i ON ck.campaign_id = i.campaign_id
LEFT JOIN hc_agg  h ON ck.campaign_id = h.campaign_id
LEFT JOIN re_agg  r ON ck.campaign_id = r.campaign_id
LEFT JOIN ar_agg  a ON ck.campaign_id = a.campaign_id
ORDER BY b.conv_pct DESC;
""".strip(),
}

QUERIES["A2 – Agent Cohort Analysis by Hire Quarter"] = {
    "level": "Advanced",
    "description": "Group agents by hire quarter and compare cohort conversion performance.",
    "sql": """
SELECT
    STRFTIME(hire_date, '%Y') || '-Q'
        || CAST(CAST(STRFTIME(hire_date,'%m') AS INT)/4 + 1 AS VARCHAR)
                                                AS hire_cohort,
    COUNT(*)                                    AS agents,
    ROUND(AVG(avg_conversion_rate)*100, 2)      AS avg_conv_pct,
    ROUND(AVG(total_talk_hours), 1)             AS avg_talk_hours,
    ROUND(AVG(CAST(tenure_days AS DOUBLE)), 0)  AS avg_tenure_days,
    SUM(CAST(consecutive_below_threshold_flag AS INT)) AS flagged_count,
    ROUND(AVG(days_below_threshold),1)          AS avg_below_threshold_days,
    STRING_AGG(DISTINCT performance_tier, ', ') AS tiers_in_cohort
FROM gold_agent_performance
WHERE hire_date IS NOT NULL
GROUP BY hire_cohort
ORDER BY hire_cohort;
""".strip(),
}

QUERIES["A3 – Predictive Score Lift Analysis"] = {
    "level": "Advanced",
    "description": "Compare actual conversion rates across ML score deciles to measure model lift.",
    "sql": """
WITH scored AS (
    SELECT
        lead_id,
        vertical,
        converted,
        COALESCE(predicted_score, global_predicted_score) AS score
    FROM gold_ml_feature_store
    WHERE COALESCE(predicted_score, global_predicted_score) IS NOT NULL
),
deciled AS (
    SELECT *,
        NTILE(10) OVER (ORDER BY score DESC)    AS decile
    FROM scored
),
decile_stats AS (
    SELECT
        decile,
        COUNT(*)                                AS leads,
        SUM(converted)                          AS conversions,
        ROUND(AVG(score), 1)                    AS avg_score,
        ROUND(SUM(converted)*100.0
              / COUNT(*), 2)                    AS conv_rate_pct
    FROM deciled
    GROUP BY decile
),
baseline AS (
    SELECT ROUND(SUM(converted)*100.0 / COUNT(*), 4) AS base_rate
    FROM scored
)
SELECT
    d.decile,
    d.leads,
    d.conversions,
    d.avg_score,
    d.conv_rate_pct,
    ROUND(d.conv_rate_pct / b.base_rate, 2)    AS lift_over_baseline,
    SUM(d.leads) OVER (ORDER BY d.decile)       AS cumulative_leads,
    SUM(d.conversions) OVER (ORDER BY d.decile) AS cumulative_conversions
FROM decile_stats d
CROSS JOIN baseline b
ORDER BY d.decile;
""".strip(),
}

QUERIES["A4 – Multi-Vertical Sentiment Heatmap"] = {
    "level": "Advanced",
    "description": "Sentiment by vertical and month side-by-side — negative signals needing attention.",
    "sql": """
WITH sentiment_monthly AS (
    SELECT 'Insurance'  AS vertical, call_month, avg_sentiment FROM gold_insurance_kpis
    UNION ALL
    SELECT 'Healthcare', call_month, avg_sentiment FROM gold_healthcare_kpis
    UNION ALL
    SELECT 'RealEstate', call_month, avg_sentiment FROM gold_realestate_kpis
    UNION ALL
    SELECT 'AR',         call_month, avg_sentiment FROM gold_ar_kpis
)
SELECT
    call_month,
    ROUND(AVG(CASE WHEN vertical='Insurance'  THEN avg_sentiment END), 4) AS insurance_sentiment,
    ROUND(AVG(CASE WHEN vertical='Healthcare' THEN avg_sentiment END), 4) AS healthcare_sentiment,
    ROUND(AVG(CASE WHEN vertical='RealEstate' THEN avg_sentiment END), 4) AS realestate_sentiment,
    ROUND(AVG(CASE WHEN vertical='AR'         THEN avg_sentiment END), 4) AS ar_sentiment,
    ROUND(AVG(avg_sentiment), 4)                                           AS overall_avg
FROM sentiment_monthly
GROUP BY call_month
ORDER BY call_month;
""".strip(),
}

QUERIES["A5 – Compound Funnel with Statistical Summary"] = {
    "level": "Advanced",
    "description": "Full BPO funnel with stddev, percentiles, and anomaly detection per vertical.",
    "sql": """
WITH raw AS (
    SELECT vertical,
        total_calls, total_converted,
        conversion_rate, avg_sentiment,
        compliance_flags
    FROM gold_campaign_kpis
),
stats AS (
    SELECT
        vertical,
        COUNT(*)                                        AS campaigns,
        SUM(total_calls)                                AS total_calls,
        SUM(total_converted)                            AS total_converted,
        ROUND(AVG(conversion_rate)*100, 3)              AS mean_conv_pct,
        ROUND(STDDEV(conversion_rate)*100, 3)           AS stddev_conv_pct,
        ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP
              (ORDER BY conversion_rate)*100, 3)        AS p25_conv,
        ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP
              (ORDER BY conversion_rate)*100, 3)        AS median_conv,
        ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP
              (ORDER BY conversion_rate)*100, 3)        AS p75_conv,
        ROUND(AVG(avg_sentiment), 4)                    AS mean_sentiment,
        ROUND(STDDEV(avg_sentiment), 4)                 AS stddev_sentiment,
        SUM(compliance_flags)                           AS total_compliance_flags
    FROM raw
    GROUP BY vertical
),
anomalies AS (
    SELECT r.vertical,
        COUNT(*) FILTER (
            WHERE ABS((r.conversion_rate*100 - s.mean_conv_pct)
                      / NULLIF(s.stddev_conv_pct, 0)) > 2
        )                                               AS anomaly_campaigns
    FROM raw r
    JOIN stats s USING (vertical)
    GROUP BY r.vertical
)
SELECT
    s.*,
    a.anomaly_campaigns
FROM stats s
JOIN anomalies a USING (vertical)
ORDER BY s.mean_conv_pct DESC;
""".strip(),
}
