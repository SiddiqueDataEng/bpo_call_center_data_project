"""
Core entity generators — produces all BPO platform entities with
realistic distributions, relational integrity, and vertical context.
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from typing import Any

from faker import Faker

from .constants import (
    AGENT_ROLE_WEIGHTS, AGENT_ROLES, ACA_FPL_THRESHOLDS,
    AR_LEAD_SOURCES, CALL_DURATION_RANGES, COMPLIANCE_KEYWORDS,
    COVERAGE_TYPES, DEBT_TYPES, DIALING_MODES, DISPOSITIONS,
    DISPOSITION_WEIGHTS, HEALTHCARE_FACILITIES, HEALTHCARE_LEAD_SOURCES,
    HEALTHCARE_SPECIALTIES, INSURANCE_LEAD_SOURCES, INSURANCE_PRODUCT_TYPES,
    ORIGINAL_CREDITORS, PAYER_IDS, PAYMENT_METHODS, PAYMENT_SCHEDULES,
    PRICE_RANGES, PROPERTY_TYPES, QA_RUBRIC_CATEGORIES, RE_LEAD_SOURCES,
    SELL_REASONS, STATE_SOL, US_STATES, VERTICALS,
)
from .utils import (
    build_transcript, clamp, new_id, normalize_e164,
    random_annual_income, random_date, random_dob,
    random_e164_us, random_zip, sentiment_from_disposition,
    weighted_choice,
)

fake = Faker("en_US")
Faker.seed(42)
random.seed(42)


# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------

def generate_clients(n: int = 8) -> list[dict]:
    industries = ["Insurance", "Healthcare", "Real Estate", "Debt Collection"]
    clients = []
    for _ in range(n):
        clients.append({
            "client_id": new_id(),
            "company_name": fake.company(),
            "industry": random.choice(industries),
            "contact_name": fake.name(),
            "contact_email": fake.company_email(),
            "contact_phone": normalize_e164(fake.numerify("+1##########")),
            "state": random.choice(US_STATES),
            "created_at": fake.date_time_between(start_date="-2y", end_date="-6M").isoformat(),
        })
    return clients


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------

def generate_agents(n: int = 60) -> list[dict]:
    agents = []
    for _ in range(n):
        role = weighted_choice(AGENT_ROLES, AGENT_ROLE_WEIGHTS)
        # performance profile drives conversion rates in call generation
        perf_tier = random.choices(["high", "mid", "low"], weights=[0.25, 0.50, 0.25])[0]
        base_conversion = {"high": 0.22, "mid": 0.13, "low": 0.07}[perf_tier]
        agents.append({
            "agent_id": new_id(),
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": fake.email(),
            "role": role,
            "vertical_specialization": random.choice(VERTICALS),
            "performance_tier": perf_tier,
            "base_conversion_rate": round(base_conversion + random.gauss(0, 0.02), 4),
            "hire_date": fake.date_between(start_date="-3y", end_date="-1M").isoformat(),
            "is_active": random.random() > 0.08,
            "team_lead_id": None,  # filled in post-generation
        })
    # assign team leads
    leads = [a["agent_id"] for a in agents if a["role"] == "Team Lead"]
    if leads:
        for a in agents:
            if a["role"] == "Agent":
                a["team_lead_id"] = random.choice(leads)
    return agents


# ---------------------------------------------------------------------------
# Campaigns
# ---------------------------------------------------------------------------

def generate_campaigns(clients: list[dict], n_per_vertical: int = 3,
                        start: datetime = None, end: datetime = None) -> list[dict]:
    if start is None:
        start = datetime.utcnow() - timedelta(days=180)
    if end is None:
        end = datetime.utcnow()

    campaigns = []
    for vertical in VERTICALS:
        vertical_clients = [c for c in clients] or clients
        for i in range(n_per_vertical):
            c_start = random_date(start, end - timedelta(days=30))
            c_end_chance = random.random()
            c_closed = c_start + timedelta(days=random.randint(14, 90)) if c_end_chance > 0.4 else None
            status = "Closed" if c_closed and c_closed < datetime.utcnow() else "Active"
            campaigns.append({
                "campaign_id": new_id(),
                "name": f"{vertical} Campaign {i + 1} — {fake.bs().title()[:40]}",
                "vertical": vertical,
                "client_id": random.choice(vertical_clients)["client_id"],
                "dialing_mode": weighted_choice(DIALING_MODES, [0.20, 0.35, 0.45]),
                "status": status,
                "target_abandon_rate": 0.03,
                "dial_ratio": round(random.uniform(1.5, 4.0), 2),
                "conversion_threshold": round(random.uniform(0.08, 0.15), 3),
                "created_at": c_start.isoformat(),
                "closed_at": c_closed.isoformat() if c_closed else None,
            })
    return campaigns


# ---------------------------------------------------------------------------
# DNC List
# ---------------------------------------------------------------------------

def generate_dnc_list(n: int = 200) -> list[dict]:
    return [
        {
            "phone_e164": normalize_e164(random_e164_us()),
            "source": random.choice(["National Registry", "Internal", "Cease-and-Desist"]),
            "added_at": fake.date_time_between(start_date="-2y", end_date="now").isoformat(),
        }
        for _ in range(n)
    ]


# ---------------------------------------------------------------------------
# Leads
# ---------------------------------------------------------------------------

def _insurance_vertical_data() -> dict:
    product = random.choice(INSURANCE_PRODUCT_TYPES)
    cov_list = COVERAGE_TYPES[product]
    dob = random_dob(22, 72)
    household_size = random.randint(1, 6)
    income = random_annual_income()
    fpl = ACA_FPL_THRESHOLDS.get(min(household_size, 8), 50000)
    aca_eligible = income <= fpl * 4.0
    return {
        "product_type": product,
        "coverage_type": random.choice(cov_list),
        "date_of_birth": dob,
        "household_size": household_size,
        "annual_income": income,
        "zip_code": random_zip(),
        "aca_eligible": aca_eligible,
        "aca_subsidy_eligible": income <= fpl * 2.5,
        "tobacco_user": random.random() < 0.18,
        "lead_source": random.choice(INSURANCE_LEAD_SOURCES),
        "consent_method": random.choice(["Web Form", "Verbal", "SMS"]),
    }


def _healthcare_vertical_data() -> dict:
    return {
        "specialty": random.choice(HEALTHCARE_SPECIALTIES),
        "payer_id": random.choice(PAYER_IDS),
        "member_id": fake.bothify("MBR-########"),
        "date_of_birth": random_dob(18, 85),
        "insurance_plan": fake.bothify("PLAN-???-####"),
        "group_number": fake.bothify("GRP-######"),
        "facility_preference": random.choice(HEALTHCARE_FACILITIES),
        "primary_complaint": random.choice([
            "Annual checkup", "Follow-up", "New symptoms",
            "Prescription refill", "Specialist referral",
        ]),
        "preferred_appointment_time": random.choice([
            "Morning", "Afternoon", "Evening", "Any",
        ]),
        "lead_source": random.choice(HEALTHCARE_LEAD_SOURCES),
        "consent_method": random.choice(["Web Form", "Verbal"]),
    }


def _realestate_vertical_data() -> dict:
    interest = random.choice(["buyer", "seller"])
    price_range = random.choice(PRICE_RANGES)
    data: dict[str, Any] = {
        "interest_type": interest,
        "target_state": random.choice(US_STATES),
        "target_city": fake.city(),
        "budget_min": price_range[0],
        "budget_max": price_range[1],
        "timeline_months": random.choice([1, 3, 6, 12, 24]),
        "lead_source": random.choice(RE_LEAD_SOURCES),
    }
    if interest == "buyer":
        data.update({
            "pre_approval_status": random.choice(["Approved", "In Progress", "Not Started"]),
            "desired_property_type": random.choice(PROPERTY_TYPES),
            "move_in_timeline": random.choice(["ASAP", "1-3 months", "3-6 months", "6-12 months"]),
            "first_time_buyer": random.random() < 0.35,
            "down_payment_pct": round(random.uniform(3.5, 25.0), 1),
        })
    else:
        data.update({
            "property_address": fake.address().replace("\n", ", "),
            "estimated_value": random.randint(price_range[0], price_range[1]),
            "reason_for_selling": random.choice(SELL_REASONS),
            "listing_timeline": random.choice(["Within 30 days", "1-3 months", "3-6 months", "Not sure"]),
            "current_mortgage_balance": random.randint(50_000, price_range[1] - 20_000),
            "agent_already_listed": random.random() < 0.12,
        })
    return data


def _ar_vertical_data(state: str) -> dict:
    debt_type = random.choice(DEBT_TYPES)
    original_balance = round(random.uniform(500, 45_000), 2)
    account_age_days = random.randint(90, 3650)
    sol_years = STATE_SOL.get(state, 6)
    sol_expired = account_age_days > sol_years * 365
    return {
        "debt_type": debt_type,
        "original_creditor": random.choice(ORIGINAL_CREDITORS),
        "original_balance": original_balance,
        "current_balance": round(original_balance * random.uniform(0.85, 1.15), 2),
        "account_age_days": account_age_days,
        "last_payment_date": (
            datetime.utcnow() - timedelta(days=account_age_days)
        ).date().isoformat(),
        "statute_of_limitations_years": sol_years,
        "sol_expired": sol_expired,
        "lead_source": random.choice(AR_LEAD_SOURCES),
        "ssn_last4": fake.numerify("####"),
        "date_of_birth": random_dob(22, 70),
    }


def generate_leads(campaigns: list[dict], dnc_phones: set[str],
                   n: int = 500, start: datetime = None) -> list[dict]:
    if start is None:
        start = datetime.utcnow() - timedelta(days=180)
    end = datetime.utcnow()

    leads = []
    for _ in range(n):
        campaign = random.choice(campaigns)
        vertical = campaign["vertical"]
        state = random.choice(US_STATES)
        phone = normalize_e164(random_e164_us())
        dnc_flagged = phone in dnc_phones or random.random() < 0.03

        # Vertical-specific data
        if vertical == "Insurance":
            vdata = _insurance_vertical_data()
            consent_ts = fake.date_time_between(start_date="-1y", end_date="now").isoformat()
        elif vertical == "Healthcare":
            vdata = _healthcare_vertical_data()
            consent_ts = fake.date_time_between(start_date="-1y", end_date="now").isoformat()
        elif vertical == "RealEstate":
            vdata = _realestate_vertical_data()
            consent_ts = None
        else:  # AR
            vdata = _ar_vertical_data(state)
            consent_ts = None

        status = "Closed" if dnc_flagged else weighted_choice(
            ["New", "Dialing", "Contacted", "Dispositioned", "Recycled", "Closed"],
            [0.15, 0.10, 0.20, 0.40, 0.10, 0.05],
        )

        created_at = random_date(start, end)
        leads.append({
            "lead_id": new_id(),
            "campaign_id": campaign["campaign_id"],
            "vertical": vertical,
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": fake.email(),
            "phone_e164": phone,
            "state": state,
            "city": fake.city(),
            "zip_code": random_zip(state),
            "status": status,
            "dnc_flagged": dnc_flagged,
            "dnc_flagged_at": created_at.isoformat() if dnc_flagged else None,
            "lead_score": random.randint(0, 100) if random.random() > 0.1 else None,
            "consent_timestamp": consent_ts,
            "consent_method": vdata.get("consent_method"),
            "vertical_data": json.dumps(vdata),
            "created_at": created_at.isoformat(),
            "updated_at": (created_at + timedelta(hours=random.randint(0, 48))).isoformat(),
        })
    return leads


# ---------------------------------------------------------------------------
# Calls
# ---------------------------------------------------------------------------

def generate_calls(leads: list[dict], agents: list[dict],
                   n: int = 2000, start: datetime = None) -> list[dict]:
    if start is None:
        start = datetime.utcnow() - timedelta(days=180)
    end = datetime.utcnow()

    dialable = [l for l in leads if not l["dnc_flagged"]
                and l["status"] in ("Contacted", "Dispositioned", "Recycled", "Closed")]
    if not dialable:
        dialable = leads[:max(1, len(leads) // 2)]

    active_agents = [a for a in agents if a["is_active"] and a["role"] == "Agent"]
    if not active_agents:
        active_agents = agents

    calls = []
    for _ in range(n):
        lead = random.choice(dialable)
        agent = random.choice(active_agents)
        vertical = lead["vertical"]

        # Disposition weighted by vertical with agent performance influence
        weights = list(DISPOSITION_WEIGHTS[vertical])
        # high-perf agents slightly more likely to get Interested/Transfer
        if agent["performance_tier"] == "high":
            weights[0] = min(weights[0] * 1.5, 0.30)
            weights[4] = min(weights[4] * 1.4, 0.18)
        elif agent["performance_tier"] == "low":
            weights[0] = max(weights[0] * 0.6, 0.04)

        disposition = weighted_choice(DISPOSITIONS, weights)
        dur_range = CALL_DURATION_RANGES[disposition]
        duration = random.randint(*dur_range)

        started_at = random_date(start, end)
        ended_at = started_at + timedelta(seconds=duration)

        # Transcript and NLP
        vdata = json.loads(lead.get("vertical_data") or "{}")
        product = vdata.get("product_type") or vdata.get("specialty") or vertical
        agent_name = f"{agent['first_name']} {agent['last_name']}"
        lead_name = f"{lead['first_name']} {lead['last_name']}"
        transcript = build_transcript(
            disposition, agent_name, lead_name,
            f"{vertical} Solutions", product,
        )

        # NLP compliance flag
        compliance_flagged = any(kw in transcript.lower() for kw in COMPLIANCE_KEYWORDS)
        compliance_phrase = None
        compliance_position = None
        if compliance_flagged:
            for kw in COMPLIANCE_KEYWORDS:
                pos = transcript.lower().find(kw)
                if pos >= 0:
                    compliance_phrase = kw
                    compliance_position = pos
                    break

        sentiment = sentiment_from_disposition(disposition)
        transfer_agent_id = None
        if disposition == "Transfer":
            others = [a["agent_id"] for a in active_agents if a["agent_id"] != agent["agent_id"]]
            transfer_agent_id = random.choice(others) if others else None

        calls.append({
            "call_id": new_id(),
            "lead_id": lead["lead_id"],
            "agent_id": agent["agent_id"],
            "campaign_id": lead["campaign_id"],
            "vertical": vertical,
            "started_at": started_at.isoformat(),
            "ended_at": ended_at.isoformat(),
            "duration_seconds": duration,
            "disposition": disposition,
            "recording_blob_key": f"recordings/{lead['campaign_id']}/{new_id()}.wav"
                if disposition not in ("NoAnswer",) else None,
            "transcript": transcript,
            "sentiment_score": sentiment,
            "compliance_flagged": compliance_flagged,
            "compliance_phrase": compliance_phrase,
            "compliance_phrase_position": compliance_position,
            "transfer_agent_id": transfer_agent_id,
            "created_at": started_at.isoformat(),
        })
    return calls


# ---------------------------------------------------------------------------
# QA Reviews
# ---------------------------------------------------------------------------

def generate_qa_reviews(calls: list[dict], agents: list[dict],
                        sample_rate: float = 0.15) -> list[dict]:
    qa_agents = [a for a in agents if a["role"] in ("QA Manager", "Supervisor")]
    if not qa_agents:
        qa_agents = agents[:3]

    reviewable = [c for c in calls if c["disposition"] not in ("NoAnswer",)
                  and c["duration_seconds"] and c["duration_seconds"] > 30]
    sampled = random.sample(reviewable, k=int(len(reviewable) * sample_rate))

    reviews = []
    for call in sampled:
        reviewer = random.choice(qa_agents)
        scores = {cat: round(random.uniform(1.0, 5.0), 1) for cat in QA_RUBRIC_CATEGORIES}
        total = round(sum(scores.values()) / len(scores), 2)
        reviews.append({
            "qa_review_id": new_id(),
            "call_id": call["call_id"],
            "agent_id": call["agent_id"],
            "reviewer_id": reviewer["agent_id"],
            "scores": json.dumps(scores),
            "total_score": total,
            "feedback": fake.sentence(nb_words=random.randint(10, 30)),
            "reviewed_at": (
                datetime.fromisoformat(call["ended_at"]) +
                timedelta(hours=random.randint(1, 72))
            ).isoformat(),
        })
    return reviews


# ---------------------------------------------------------------------------
# Vertical-specific outcome tables
# ---------------------------------------------------------------------------

def generate_insurance_qualifications(calls: list[dict],
                                       leads: list[dict]) -> list[dict]:
    lead_map = {l["lead_id"]: l for l in leads}
    qualified_calls = [
        c for c in calls
        if c["vertical"] == "Insurance"
        and c["disposition"] in ("Interested", "Transfer", "Callback")
    ]
    records = []
    for call in qualified_calls:
        lead = lead_map.get(call["lead_id"], {})
        vdata = json.loads(lead.get("vertical_data") or "{}")
        records.append({
            "qualification_id": new_id(),
            "call_id": call["call_id"],
            "lead_id": call["lead_id"],
            "product_type": vdata.get("product_type", "health"),
            "coverage_type": vdata.get("coverage_type", "PPO"),
            "date_of_birth": vdata.get("date_of_birth"),
            "zip_code": vdata.get("zip_code", lead.get("zip_code")),
            "current_coverage_status": vdata.get("coverage_type", "None"),
            "household_size": vdata.get("household_size", 1),
            "annual_income": vdata.get("annual_income"),
            "aca_eligible": vdata.get("aca_eligible", False),
            "aca_subsidy_eligible": vdata.get("aca_subsidy_eligible", False),
            "transfer_completed": call["disposition"] == "Transfer",
            "transfer_agent_id": call.get("transfer_agent_id"),
            "created_at": call["started_at"],
        })
    return records


def generate_appointments(calls: list[dict], leads: list[dict]) -> list[dict]:
    lead_map = {l["lead_id"]: l for l in leads}
    appt_calls = [
        c for c in calls
        if c["vertical"] == "Healthcare"
        and c["disposition"] in ("Interested", "Callback")
    ]
    records = []
    for call in appt_calls:
        lead = lead_map.get(call["lead_id"], {})
        vdata = json.loads(lead.get("vertical_data") or "{}")
        appt_dt = (
            datetime.fromisoformat(call["ended_at"]) +
            timedelta(days=random.randint(1, 30))
        )
        records.append({
            "appointment_id": new_id(),
            "call_id": call["call_id"],
            "lead_id": call["lead_id"],
            "patient_name": f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip(),
            "appointment_date": appt_dt.date().isoformat(),
            "appointment_time": f"{random.randint(8, 16):02d}:{random.choice(['00','15','30','45'])}",
            "provider_name": fake.name_nonbinary(),
            "facility": vdata.get("facility_preference", random.choice(HEALTHCARE_FACILITIES)),
            "specialty": vdata.get("specialty", random.choice(HEALTHCARE_SPECIALTIES)),
            "payer_id": vdata.get("payer_id"),
            "member_id": vdata.get("member_id"),
            "insurance_plan": vdata.get("insurance_plan"),
            "webhook_sent": random.random() > 0.05,
            "confirmation_email_sent": random.random() > 0.08,
            "created_at": call["ended_at"],
        })
    return records


def generate_realestate_qualifications(calls: list[dict],
                                        leads: list[dict]) -> list[dict]:
    lead_map = {l["lead_id"]: l for l in leads}
    re_calls = [
        c for c in calls
        if c["vertical"] == "RealEstate"
        and c["disposition"] in ("Interested", "Transfer", "Callback")
    ]
    records = []
    for call in re_calls:
        lead = lead_map.get(call["lead_id"], {})
        vdata = json.loads(lead.get("vertical_data") or "{}")
        interest = vdata.get("interest_type", "buyer")
        records.append({
            "qualification_id": new_id(),
            "call_id": call["call_id"],
            "lead_id": call["lead_id"],
            "interest_type": interest,
            "target_state": vdata.get("target_state", lead.get("state")),
            "target_city": vdata.get("target_city", lead.get("city")),
            "budget_min": vdata.get("budget_min"),
            "budget_max": vdata.get("budget_max"),
            "timeline_months": vdata.get("timeline_months"),
            "pre_approval_status": vdata.get("pre_approval_status") if interest == "buyer" else None,
            "desired_property_type": vdata.get("desired_property_type") if interest == "buyer" else None,
            "move_in_timeline": vdata.get("move_in_timeline") if interest == "buyer" else None,
            "property_address": vdata.get("property_address") if interest == "seller" else None,
            "estimated_value": vdata.get("estimated_value") if interest == "seller" else None,
            "reason_for_selling": vdata.get("reason_for_selling") if interest == "seller" else None,
            "listing_timeline": vdata.get("listing_timeline") if interest == "seller" else None,
            "agent_matched": random.random() > 0.15,
            "created_at": call["started_at"],
        })
    return records


def generate_payment_arrangements(calls: list[dict],
                                   leads: list[dict]) -> list[dict]:
    lead_map = {l["lead_id"]: l for l in leads}
    ar_calls = [
        c for c in calls
        if c["vertical"] == "AR"
        and c["disposition"] in ("Interested", "Callback")
    ]
    records = []
    for call in ar_calls:
        lead = lead_map.get(call["lead_id"], {})
        vdata = json.loads(lead.get("vertical_data") or "{}")
        original = vdata.get("current_balance", random.uniform(500, 15000))
        settlement_pct = random.uniform(0.40, 0.95)
        settlement_amt = round(original * settlement_pct, 2)
        schedule = random.choice(PAYMENT_SCHEDULES)
        records.append({
            "arrangement_id": new_id(),
            "call_id": call["call_id"],
            "lead_id": call["lead_id"],
            "original_balance": original,
            "settlement_amount": settlement_amt,
            "settlement_pct": round(settlement_pct, 4),
            "payment_schedule": schedule,
            "payment_method": random.choice(PAYMENT_METHODS),
            "verbal_confirmation": True,
            "confirmation_email_sent": random.random() > 0.07,
            "debt_type": vdata.get("debt_type"),
            "original_creditor": vdata.get("original_creditor"),
            "sol_expired": vdata.get("sol_expired", False),
            "created_at": call["ended_at"],
        })
    return records


# ---------------------------------------------------------------------------
# Pipeline Events (Event Hubs / Kafka format)
# ---------------------------------------------------------------------------

def generate_pipeline_events(calls: list[dict]) -> list[dict]:
    events = []
    for call in calls:
        if call["disposition"] in ("NoAnswer",) and random.random() > 0.3:
            continue
        events.append({
            "event_id": new_id(),
            "event_type": "call.completed",
            "schema_version": "1.0",
            "source_call_id": call["call_id"],
            "emitted_at": call["ended_at"],
            "payload": {
                "call_id": call["call_id"],
                "lead_id": call["lead_id"],
                "agent_id": call["agent_id"],
                "campaign_id": call["campaign_id"],
                "vertical": call["vertical"],
                "disposition": call["disposition"],
                "duration_seconds": call["duration_seconds"],
                "sentiment_score": call["sentiment_score"],
                "compliance_flagged": call["compliance_flagged"],
                "started_at": call["started_at"],
                "ended_at": call["ended_at"],
            },
            "status": random.choices(
                ["Loaded", "Loaded", "Loaded", "Loaded", "Failed"],
                weights=[0.94, 0.94, 0.94, 0.94, 0.06],
            )[0],
        })
    return events


# ---------------------------------------------------------------------------
# Agent Daily Performance (for ML drift monitoring and retraining)
# ---------------------------------------------------------------------------

def generate_agent_daily_performance(agents: list[dict],
                                      calls: list[dict],
                                      days: int = 90) -> list[dict]:
    from collections import defaultdict

    agent_map = {a["agent_id"]: a for a in agents}
    # group calls by (agent_id, date)
    daily: dict[tuple, list] = defaultdict(list)
    for c in calls:
        if c["agent_id"] and c["started_at"]:
            date_str = c["started_at"][:10]
            daily[(c["agent_id"], date_str)].append(c)

    records = []
    end = datetime.utcnow().date()
    start = end - timedelta(days=days)
    cur = start
    while cur <= end:
        date_str = cur.isoformat()
        for agent in agents:
            if not agent["is_active"]:
                cur += timedelta(days=1)
                continue
            day_calls = daily.get((agent["agent_id"], date_str), [])
            if not day_calls and random.random() > 0.15:
                # No calls logged that day — skip
                cur_date = cur
                cur = cur_date  # avoid double increment
                break
            total = len(day_calls)
            if total == 0:
                cur += timedelta(days=1)
                continue
            interested = sum(1 for c in day_calls if c["disposition"] == "Interested")
            transferred = sum(1 for c in day_calls if c["disposition"] == "Transfer")
            talk_secs = sum(c["duration_seconds"] or 0 for c in day_calls)
            conversion_rate = round((interested + transferred) / total, 4) if total else 0.0
            records.append({
                "record_id": new_id(),
                "agent_id": agent["agent_id"],
                "date": date_str,
                "total_calls": total,
                "interested_count": interested,
                "transfer_count": transferred,
                "not_interested_count": sum(1 for c in day_calls if c["disposition"] == "NotInterested"),
                "dnc_count": sum(1 for c in day_calls if c["disposition"] == "DNC"),
                "talk_time_seconds": talk_secs,
                "avg_handle_time": round(talk_secs / total, 1) if total else 0,
                "conversion_rate": conversion_rate,
                "below_threshold": conversion_rate < agent_map.get(
                    agent["agent_id"], {}).get("base_conversion_rate", 0.10),
                "campaign_threshold": agent_map.get(
                    agent["agent_id"], {}).get("base_conversion_rate", 0.10),
            })
        cur += timedelta(days=1)
    return records


# ---------------------------------------------------------------------------
# ML Feature Matrix
# ---------------------------------------------------------------------------

def generate_ml_features(leads: list[dict], calls: list[dict]) -> list[dict]:
    """Flatten leads + call outcomes into a supervised ML feature matrix."""
    lead_calls: dict[str, list] = {}
    for c in calls:
        lead_calls.setdefault(c["lead_id"], []).append(c)

    records = []
    for lead in leads:
        lcalls = lead_calls.get(lead["lead_id"], [])
        vdata = json.loads(lead.get("vertical_data") or "{}")
        vertical = lead["vertical"]

        # Target: was the lead ever converted (Interested or Transfer)
        converted = any(c["disposition"] in ("Interested", "Transfer") for c in lcalls)
        n_calls = len(lcalls)
        avg_sentiment = (
            sum(c["sentiment_score"] or 0 for c in lcalls) / n_calls
            if n_calls else 0.0
        )

        record: dict[str, Any] = {
            "feature_row_id": new_id(),
            "lead_id": lead["lead_id"],
            "vertical": vertical,
            "state": lead["state"],
            "lead_score": lead.get("lead_score"),
            "dnc_flagged": int(lead["dnc_flagged"]),
            "n_call_attempts": n_calls,
            "avg_sentiment_score": round(avg_sentiment, 4),
            "has_consent": int(lead.get("consent_timestamp") is not None),
            # target
            "converted": int(converted),
        }

        # Vertical-specific features
        if vertical == "Insurance":
            record.update({
                "ins_product_type": vdata.get("product_type"),
                "ins_household_size": vdata.get("household_size"),
                "ins_annual_income": vdata.get("annual_income"),
                "ins_aca_eligible": int(vdata.get("aca_eligible", False)),
                "ins_tobacco_user": int(vdata.get("tobacco_user", False)),
            })
        elif vertical == "Healthcare":
            record.update({
                "hc_specialty": vdata.get("specialty"),
                "hc_payer_id": vdata.get("payer_id"),
            })
        elif vertical == "RealEstate":
            record.update({
                "re_interest_type": vdata.get("interest_type"),
                "re_budget_min": vdata.get("budget_min"),
                "re_budget_max": vdata.get("budget_max"),
                "re_timeline_months": vdata.get("timeline_months"),
                "re_pre_approval": vdata.get("pre_approval_status"),
            })
        elif vertical == "AR":
            record.update({
                "ar_original_balance": vdata.get("original_balance"),
                "ar_current_balance": vdata.get("current_balance"),
                "ar_account_age_days": vdata.get("account_age_days"),
                "ar_sol_expired": int(vdata.get("sol_expired", False)),
                "ar_debt_type": vdata.get("debt_type"),
            })

        records.append(record)
    return records
