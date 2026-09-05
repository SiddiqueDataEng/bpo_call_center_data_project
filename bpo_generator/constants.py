"""
Domain constants — all USA-context, vertically accurate.
"""

# ---------------------------------------------------------------------------
# Geography
# ---------------------------------------------------------------------------
US_STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
]

# FDCPA: state → IANA timezone
STATE_TIMEZONES = {
    "AL": "America/Chicago",  "AK": "America/Anchorage", "AZ": "America/Phoenix",
    "AR": "America/Chicago",  "CA": "America/Los_Angeles", "CO": "America/Denver",
    "CT": "America/New_York", "DE": "America/New_York", "FL": "America/New_York",
    "GA": "America/New_York", "HI": "Pacific/Honolulu", "ID": "America/Denver",
    "IL": "America/Chicago",  "IN": "America/Indiana/Indianapolis",
    "IA": "America/Chicago",  "KS": "America/Chicago",  "KY": "America/New_York",
    "LA": "America/Chicago",  "ME": "America/New_York", "MD": "America/New_York",
    "MA": "America/New_York", "MI": "America/Detroit",  "MN": "America/Chicago",
    "MS": "America/Chicago",  "MO": "America/Chicago",  "MT": "America/Denver",
    "NE": "America/Chicago",  "NV": "America/Los_Angeles", "NH": "America/New_York",
    "NJ": "America/New_York", "NM": "America/Denver",   "NY": "America/New_York",
    "NC": "America/New_York", "ND": "America/Chicago",  "OH": "America/New_York",
    "OK": "America/Chicago",  "OR": "America/Los_Angeles", "PA": "America/New_York",
    "RI": "America/New_York", "SC": "America/New_York", "SD": "America/Chicago",
    "TN": "America/Chicago",  "TX": "America/Chicago",  "UT": "America/Denver",
    "VT": "America/New_York", "VA": "America/New_York", "WA": "America/Los_Angeles",
    "WV": "America/New_York", "WI": "America/Chicago",  "WY": "America/Denver",
}

# AR: state → statute of limitations on debt (years)
STATE_SOL = {
    "AL": 6, "AK": 3, "AZ": 6, "AR": 5, "CA": 4, "CO": 6, "CT": 6,
    "DE": 3, "FL": 5, "GA": 6, "HI": 6, "ID": 5, "IL": 5, "IN": 6,
    "IA": 5, "KS": 5, "KY": 5, "LA": 3, "ME": 6, "MD": 3, "MA": 6,
    "MI": 6, "MN": 6, "MS": 3, "MO": 5, "MT": 5, "NE": 5, "NV": 6,
    "NH": 3, "NJ": 6, "NM": 6, "NY": 6, "NC": 3, "ND": 6, "OH": 6,
    "OK": 5, "OR": 6, "PA": 4, "RI": 10, "SC": 3, "SD": 6, "TN": 6,
    "TX": 4, "UT": 6, "VT": 6, "VA": 5, "WA": 6, "WV": 10, "WI": 6,
    "WY": 8,
}

# ---------------------------------------------------------------------------
# Verticals & Campaigns
# ---------------------------------------------------------------------------
VERTICALS = ["Insurance", "Healthcare", "RealEstate", "AR"]

DIALING_MODES = ["Preview", "Progressive", "Predictive"]

LEAD_STATUSES = ["New", "Dialing", "Contacted", "Dispositioned", "Recycled", "Closed"]

DISPOSITIONS = [
    "Interested", "NotInterested", "Callback", "DNC",
    "Transfer", "NoAnswer", "Voicemail",
]

# Realistic disposition weight distribution per vertical
DISPOSITION_WEIGHTS = {
    "Insurance":   [0.12, 0.35, 0.18, 0.03, 0.10, 0.14, 0.08],
    "Healthcare":  [0.18, 0.28, 0.20, 0.02, 0.08, 0.15, 0.09],
    "RealEstate":  [0.10, 0.38, 0.22, 0.02, 0.06, 0.14, 0.08],
    "AR":          [0.15, 0.30, 0.20, 0.08, 0.04, 0.16, 0.07],
}

# ---------------------------------------------------------------------------
# Agent Roles
# ---------------------------------------------------------------------------
AGENT_ROLES = [
    "Agent", "Team Lead", "Supervisor", "QA Manager",
    "Campaign Manager", "Data Engineer", "Data Scientist", "Admin",
]

AGENT_ROLE_WEIGHTS = [0.55, 0.12, 0.10, 0.08, 0.07, 0.04, 0.03, 0.01]

# ---------------------------------------------------------------------------
# Insurance Domain
# ---------------------------------------------------------------------------
INSURANCE_PRODUCT_TYPES = ["health", "life", "auto", "home"]

COVERAGE_TYPES = {
    "health": ["HMO", "PPO", "EPO", "HDHP", "Medicare Supplement", "Medicaid", "None"],
    "life":   ["Term", "Whole", "Universal", "Variable", "None"],
    "auto":   ["Liability Only", "Full Coverage", "Comprehensive", "Collision", "None"],
    "home":   ["HO-3", "HO-5", "Renters", "Condo", "None"],
}

# ACA FPL brackets for eligibility (simplified)
ACA_FPL_THRESHOLDS = {
    1: 14580, 2: 19720, 3: 24860, 4: 30000,
    5: 35140, 6: 40280, 7: 45420, 8: 50560,
}

INSURANCE_LEAD_SOURCES = [
    "Web Form", "Direct Mail", "Social Media",
    "Referral", "Radio Ad", "TV Ad", "Aged List",
]

# ---------------------------------------------------------------------------
# Healthcare Domain
# ---------------------------------------------------------------------------
HEALTHCARE_SPECIALTIES = [
    "Primary Care", "Cardiology", "Orthopedics", "Dermatology",
    "Neurology", "Oncology", "Endocrinology", "Gastroenterology",
    "Pulmonology", "Mental Health",
]

PAYER_IDS = [
    "BCBS001", "AETNA002", "CIGNA003", "UHC004", "HUMANA005",
    "MOLINA006", "CENTENE007", "KAISER008", "ANTHEM009", "MAGELLAN010",
]

HEALTHCARE_FACILITIES = [
    "Sunrise Medical Center", "Valley Health Clinic", "Metro General Hospital",
    "Coastal Care Associates", "Highland Family Practice", "Riverside Specialty Group",
    "Midwest Diagnostic Center", "Summit Wellness Institute",
    "Clearwater Health Partners", "Pinnacle Medical Group",
]

HEALTHCARE_LEAD_SOURCES = [
    "Online Inquiry", "Insurance Referral", "Hospital Discharge",
    "Physician Referral", "Direct Mail", "Community Outreach",
]

# ---------------------------------------------------------------------------
# Real Estate Domain
# ---------------------------------------------------------------------------
PROPERTY_TYPES = ["Single Family", "Condo", "Townhouse", "Multi-Family", "Land", "Commercial"]

PRICE_RANGES = [
    (100_000, 250_000), (250_000, 400_000), (400_000, 600_000),
    (600_000, 900_000), (900_000, 1_500_000), (1_500_000, 5_000_000),
]

SELL_REASONS = [
    "Upsizing", "Downsizing", "Relocation", "Divorce", "Estate Sale",
    "Investment", "Job Change", "Financial Hardship",
]

RE_LEAD_SOURCES = [
    "Zillow", "Realtor.com", "Direct Mail", "Facebook Ad",
    "Google Ad", "Open House", "Referral", "Cold List",
]

# ---------------------------------------------------------------------------
# AR Domain
# ---------------------------------------------------------------------------
ORIGINAL_CREDITORS = [
    "Chase Bank", "Bank of America", "Capital One", "Synchrony Bank",
    "Citibank", "Wells Fargo", "Discover Financial", "American Express",
    "Ally Financial", "Navient Student Loans", "Sallie Mae",
    "LVNV Funding", "Portfolio Recovery Associates", "Midland Credit",
]

DEBT_TYPES = [
    "Credit Card", "Personal Loan", "Medical Debt", "Student Loan",
    "Auto Loan", "Utility Bill", "Payday Loan", "Mortgage Deficiency",
]

PAYMENT_METHODS = ["ACH", "Credit Card", "Debit Card", "Money Order", "Check"]

PAYMENT_SCHEDULES = [
    "Lump Sum", "2 Payments", "3 Payments", "6 Payments", "12 Payments", "24 Payments",
]

AR_LEAD_SOURCES = [
    "Purchased Portfolio", "Client Transfer", "Skip Trace", "Credit Bureau Data",
]

# ---------------------------------------------------------------------------
# Call & QA Domain
# ---------------------------------------------------------------------------
# Realistic call duration ranges (seconds) by disposition
CALL_DURATION_RANGES = {
    "Interested":    (180, 900),
    "NotInterested": (30,  180),
    "Callback":      (60,  300),
    "DNC":           (10,   60),
    "Transfer":      (120, 600),
    "NoAnswer":      (5,    30),
    "Voicemail":     (20,   90),
}

QA_RUBRIC_CATEGORIES = [
    "Opening & Introduction",
    "Script Compliance",
    "Product Knowledge",
    "Objection Handling",
    "Compliance Adherence",
    "Closing Technique",
    "Professionalism",
]

# Compliance keywords that trigger NLP flagging
COMPLIANCE_KEYWORDS = [
    "sue", "lawsuit", "attorney", "legal action", "report you",
    "credit bureau", "garnish", "arrest", "jail", "criminal",
    "harass", "threaten", "cease and desist", "cease-and-desist",
    "do not call", "remove me", "stop calling",
]

# Realistic transcript fragments for synthetic call transcripts
TRANSCRIPT_TEMPLATES = {
    "Interested": [
        "Hello, this is {agent} calling from {campaign}. Am I speaking with {name}?",
        "Great, {name}. I'm reaching out today regarding your {product} inquiry.",
        "Based on what you've shared, you'd qualify for coverage starting as low as {price} per month.",
        "That sounds great. Let me go ahead and get that set up for you.",
        "Perfect. Can you confirm your date of birth and zip code for verification?",
    ],
    "NotInterested": [
        "Hello, this is {agent} calling from {campaign}. Am I speaking with {name}?",
        "I'm calling about {product} options available in your area.",
        "I'm not interested, thank you.",
        "I understand completely. If you change your mind, please don't hesitate to reach out.",
        "Thank you for your time, {name}. Have a great day.",
    ],
    "DNC": [
        "Hello, is this {name}?",
        "Please remove me from your list. Do not call me again.",
        "I apologize for the interruption. I'll remove your number right away.",
        "You're now removed. Have a good day.",
    ],
    "Voicemail": [
        "Hi, this message is for {name}. My name is {agent} calling from {campaign}.",
        "I'm reaching out regarding {product} options that may be available to you.",
        "Please call us back at your earliest convenience. Thank you.",
    ],
}
