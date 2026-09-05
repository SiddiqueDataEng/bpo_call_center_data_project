"""Utility helpers shared across generators."""

import random
import string
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import phonenumbers
import pytz

from .constants import STATE_TIMEZONES


def new_id() -> str:
    return str(uuid.uuid4())


def random_e164_us() -> str:
    """Generate a random valid US E.164 phone number."""
    area = random.randint(200, 999)
    exchange = random.randint(200, 999)
    subscriber = random.randint(1000, 9999)
    raw = f"+1{area}{exchange}{subscriber}"
    return raw


def normalize_e164(raw: str) -> str:
    """Normalize any phone string to E.164 using the phonenumbers library."""
    try:
        parsed = phonenumbers.parse(raw, "US")
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except Exception:
        return raw


def random_date(start: datetime, end: datetime) -> datetime:
    delta = end - start
    seconds = int(delta.total_seconds())
    return start + timedelta(seconds=random.randint(0, max(0, seconds)))


def random_dob(min_age: int = 18, max_age: int = 80) -> str:
    """Return ISO date string for a random date of birth."""
    today = datetime.utcnow().date()
    birth_year = today.year - random.randint(min_age, max_age)
    birth_month = random.randint(1, 12)
    birth_day = random.randint(1, 28)
    return f"{birth_year:04d}-{birth_month:02d}-{birth_day:02d}"


def random_ssn_last4() -> str:
    return "".join(random.choices(string.digits, k=4))


def random_zip(state: Optional[str] = None) -> str:
    """Return a realistic 5-digit US zip code."""
    # Simplified: random 5-digit starting with non-zero
    return f"{random.randint(10000, 99999)}"


def random_annual_income() -> int:
    """Return a realistic annual household income (USD)."""
    brackets = [
        (15_000, 30_000, 0.15),
        (30_000, 55_000, 0.25),
        (55_000, 85_000, 0.25),
        (85_000, 130_000, 0.20),
        (130_000, 250_000, 0.12),
        (250_000, 600_000, 0.03),
    ]
    bracket = random.choices(brackets, weights=[b[2] for b in brackets])[0]
    return random.randint(bracket[0], bracket[1])


def is_fdcpa_allowed(state: str, dt_utc: datetime) -> bool:
    """Return True if dt_utc falls within FDCPA allowed hours (8AM-9PM local)."""
    tz_name = STATE_TIMEZONES.get(state, "America/New_York")
    tz = pytz.timezone(tz_name)
    local_dt = dt_utc.replace(tzinfo=timezone.utc).astimezone(tz)
    hour = local_dt.hour
    return 8 <= hour < 21


def weighted_choice(options: list, weights: list):
    return random.choices(options, weights=weights, k=1)[0]


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def sentiment_from_disposition(disposition: str) -> float:
    """Return a plausible sentiment score for a given disposition."""
    base = {
        "Interested":    0.60,
        "Transfer":      0.50,
        "Callback":      0.20,
        "NotInterested": -0.30,
        "Voicemail":     0.00,
        "NoAnswer":      0.00,
        "DNC":           -0.70,
    }.get(disposition, 0.0)
    noise = random.gauss(0, 0.15)
    return round(clamp(base + noise, -1.0, 1.0), 4)


def build_transcript(disposition: str, agent_name: str, lead_name: str,
                     campaign_name: str, product: str) -> str:
    """Build a synthetic realistic call transcript."""
    from .constants import TRANSCRIPT_TEMPLATES, COMPLIANCE_KEYWORDS
    templates = TRANSCRIPT_TEMPLATES.get(disposition, TRANSCRIPT_TEMPLATES["NotInterested"])
    lines = []
    for t in templates:
        line = t.format(
            agent=agent_name,
            name=lead_name,
            campaign=campaign_name,
            product=product,
            price=f"${random.randint(89, 450):.0f}",
        )
        lines.append(line)

    # Randomly inject a compliance keyword for ~5% of calls
    if random.random() < 0.05:
        kw = random.choice(COMPLIANCE_KEYWORDS)
        lines.insert(random.randint(1, len(lines)), f"Customer said: '{kw}'.")

    return " ".join(lines)
