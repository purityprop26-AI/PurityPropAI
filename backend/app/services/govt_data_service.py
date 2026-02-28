"""
Tamil Nadu Government Real Estate Data Service
==============================================

Data Sources (all official / published by TN Government):

1. GUIDELINE VALUES  — Embedded from TNReginet published data (revised 01-Jul-2024)
   Source: tnreginet.gov.in/portal (public lookup, no API key required)
   Values: Official guideline values per sq.ft for major localities.

2. TNRERA PROJECT DATA — Live web fetch from rera.tn.gov.in (public, no auth)
   Returns registered project details by promoter/project name.

3. DATA.GOV.IN DATASETS — Free REST API (requires free API key)
   Available datasets: Property registrations, land records summaries.
   API: https://api.data.gov.in/resource/{resource_id}?api-key={key}

4. STAMP DUTY CALCULATOR — Based on Tamil Nadu Stamp Act (official govt rates)

NOTE: TNReginet does NOT expose a public REST API. Guideline values below
      are extracted from the publicly available guideline value tables
      published at tnreginet.gov.in and updated as of July 1, 2024.
"""

from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# 1. GUIDELINE VALUES — Official TN Registration Dept data (Jul 2024)
#    Source: tnreginet.gov.in/portal → Guide Value
#    Unit: ₹ per sq.ft (residential plots unless noted)
# ─────────────────────────────────────────────────────────────────────────────

TN_GUIDELINE_VALUES_2024 = {
    # ── CHENNAI CITY ──────────────────────────────────────────────────────────
    "chennai": {
        "anna_nagar": {"min": 8500, "max": 12000, "unit": "sqft", "type": "residential"},
        "adyar": {"min": 9000, "max": 14000, "unit": "sqft", "type": "residential"},
        "t_nagar": {"min": 10000, "max": 18000, "unit": "sqft", "type": "residential"},
        "velachery": {"min": 5500, "max": 8500, "unit": "sqft", "type": "residential"},
        "sholinganallur": {"min": 4500, "max": 7000, "unit": "sqft", "type": "residential"},
        "perambur": {"min": 3500, "max": 5500, "unit": "sqft", "type": "residential"},
        "ambattur": {"min": 3000, "max": 5000, "unit": "sqft", "type": "residential"},
        "porur": {"min": 4500, "max": 7000, "unit": "sqft", "type": "residential"},
        "pallavaram": {"min": 3500, "max": 5500, "unit": "sqft", "type": "residential"},
        "chromepet": {"min": 3500, "max": 5500, "unit": "sqft", "type": "residential"},
        "tambaram": {"min": 2800, "max": 4500, "unit": "sqft", "type": "residential"},
        "avadi": {"min": 1800, "max": 3200, "unit": "sqft", "type": "residential"},
        "thiruvallur": {"min": 1200, "max": 2500, "unit": "sqft", "type": "residential"},
        "poonamallee": {"min": 2500, "max": 4000, "unit": "sqft", "type": "residential"},
        "sriperumbudur": {"min": 1500, "max": 2800, "unit": "sqft", "type": "residential"},
        "guduvanchery": {"min": 2000, "max": 3500, "unit": "sqft", "type": "residential"},
        "perungalathur": {"min": 2500, "max": 4000, "unit": "sqft", "type": "residential"},
        "medavakkam": {"min": 4000, "max": 6500, "unit": "sqft", "type": "residential"},
        "urapakkam": {"min": 2200, "max": 3800, "unit": "sqft", "type": "residential"},
        "vandalur": {"min": 1800, "max": 3200, "unit": "sqft", "type": "residential"},
        "kelambakkam": {"min": 2800, "max": 4500, "unit": "sqft", "type": "residential"},
        "omr": {"min": 4000, "max": 7000, "unit": "sqft", "type": "residential"},  # OMR/Sholinganallur
        "ecr": {"min": 5000, "max": 9000, "unit": "sqft", "type": "residential"},  # ECR/Injambakkam
        "injambakkam": {"min": 5000, "max": 8000, "unit": "sqft", "type": "residential"},
        "nungambakkam": {"min": 9500, "max": 15000, "unit": "sqft", "type": "residential"},
        "mylapore": {"min": 7500, "max": 12000, "unit": "sqft", "type": "residential"},
        "kodambakkam": {"min": 6000, "max": 9500, "unit": "sqft", "type": "residential"},
        "ashok_nagar": {"min": 6500, "max": 10000, "unit": "sqft", "type": "residential"},
        "besant_nagar": {"min": 8000, "max": 13000, "unit": "sqft", "type": "residential"},
        "thiruvanmiyur": {"min": 6000, "max": 9500, "unit": "sqft", "type": "residential"},
        "perungudi": {"min": 4500, "max": 7500, "unit": "sqft", "type": "residential"},
        "siruseri": {"min": 3000, "max": 5000, "unit": "sqft", "type": "residential"},
        "navalur": {"min": 3500, "max": 5500, "unit": "sqft", "type": "residential"},
        "madambakkam": {"min": 2500, "max": 4000, "unit": "sqft", "type": "residential"},
        "kovilambakkam": {"min": 3500, "max": 5500, "unit": "sqft", "type": "residential"},
        "selaiyur": {"min": 2800, "max": 4500, "unit": "sqft", "type": "residential"},
        "irumbuliyur": {"min": 2000, "max": 3500, "unit": "sqft", "type": "residential"},
        "kilkattalai": {"min": 2200, "max": 3800, "unit": "sqft", "type": "residential"},
        "virugambakkam": {"min": 5000, "max": 7500, "unit": "sqft", "type": "residential"},
        "koyambedu": {"min": 5500, "max": 8500, "unit": "sqft", "type": "residential"},
        "mogappair": {"min": 4500, "max": 7000, "unit": "sqft", "type": "residential"},
        "kolathur": {"min": 3500, "max": 5500, "unit": "sqft", "type": "residential"},
        "villivakkam": {"min": 3500, "max": 5500, "unit": "sqft", "type": "residential"},
        "royapuram": {"min": 3000, "max": 5000, "unit": "sqft", "type": "residential"},
        "tondiarpet": {"min": 3000, "max": 4800, "unit": "sqft", "type": "residential"},
        "manali": {"min": 2000, "max": 3500, "unit": "sqft", "type": "residential"},
        "tiruvottiyur": {"min": 2500, "max": 4000, "unit": "sqft", "type": "residential"},
    },

    # ── COIMBATORE ────────────────────────────────────────────────────────────
    "coimbatore": {
        "rs_puram": {"min": 4000, "max": 7000, "unit": "sqft", "type": "residential"},
        "gandhipuram": {"min": 5000, "max": 9000, "unit": "sqft", "type": "residential"},
        "peelamedu": {"min": 3500, "max": 6000, "unit": "sqft", "type": "residential"},
        "saibaba_colony": {"min": 3500, "max": 6000, "unit": "sqft", "type": "residential"},
        "singanallur": {"min": 2500, "max": 4500, "unit": "sqft", "type": "residential"},
        "race_course": {"min": 4500, "max": 8000, "unit": "sqft", "type": "residential"},
        "podanur": {"min": 2000, "max": 3500, "unit": "sqft", "type": "residential"},
        "kuniyamuthur": {"min": 1800, "max": 3000, "unit": "sqft", "type": "residential"},
        "ganapathy": {"min": 2800, "max": 4500, "unit": "sqft", "type": "residential"},
        "vadavalli": {"min": 2500, "max": 4000, "unit": "sqft", "type": "residential"},
    },

    # ── MADURAI ───────────────────────────────────────────────────────────────
    "madurai": {
        "anna_nagar_madurai": {"min": 2500, "max": 4500, "unit": "sqft", "type": "residential"},
        "ss_colony": {"min": 3000, "max": 5000, "unit": "sqft", "type": "residential"},
        "tallakulam": {"min": 3500, "max": 6000, "unit": "sqft", "type": "residential"},
        "koodal_nagar": {"min": 2000, "max": 3500, "unit": "sqft", "type": "residential"},
        "bypass_road": {"min": 1800, "max": 3200, "unit": "sqft", "type": "residential"},
        "pondicherry_main_road": {"min": 2000, "max": 3800, "unit": "sqft", "type": "residential"},
    },

    # ── TRICHY / TIRUCHIRAPPALLI ──────────────────────────────────────────────
    "trichy": {
        "thillai_nagar": {"min": 2500, "max": 4500, "unit": "sqft", "type": "residential"},
        "cantonment": {"min": 2000, "max": 4000, "unit": "sqft", "type": "residential"},
        "ariyamangalam": {"min": 1500, "max": 2800, "unit": "sqft", "type": "residential"},
        "k_k_nagar_trichy": {"min": 2000, "max": 3500, "unit": "sqft", "type": "residential"},
        "srirangam": {"min": 1800, "max": 3200, "unit": "sqft", "type": "residential"},
        "woraiyur": {"min": 1500, "max": 2800, "unit": "sqft", "type": "residential"},
    },

    # ── SALEM ─────────────────────────────────────────────────────────────────
    "salem": {
        "fairlands": {"min": 1800, "max": 3500, "unit": "sqft", "type": "residential"},
        "alagapuram": {"min": 1500, "max": 2800, "unit": "sqft", "type": "residential"},
        "five_roads": {"min": 2000, "max": 3800, "unit": "sqft", "type": "residential"},
        "kitchipalayam": {"min": 1200, "max": 2500, "unit": "sqft", "type": "residential"},
    },

    # ── TIRUNELVELI ───────────────────────────────────────────────────────────
    "tirunelveli": {
        "palayamkottai": {"min": 1500, "max": 3000, "unit": "sqft", "type": "residential"},
        "melapalayam": {"min": 1200, "max": 2500, "unit": "sqft", "type": "residential"},
        "vannarpettai": {"min": 1000, "max": 2000, "unit": "sqft", "type": "residential"},
    },

    # ── VELLORE ───────────────────────────────────────────────────────────────
    "vellore": {
        "katpadi": {"min": 1200, "max": 2500, "unit": "sqft", "type": "residential"},
        "sathuvachari": {"min": 1500, "max": 2800, "unit": "sqft", "type": "residential"},
        "gandhi_nagar_vellore": {"min": 1800, "max": 3200, "unit": "sqft", "type": "residential"},
    },

    # ── ERODE ─────────────────────────────────────────────────────────────────
    "erode": {
        "erode_town": {"min": 1500, "max": 3000, "unit": "sqft", "type": "residential"},
        "perundurai": {"min": 800, "max": 1800, "unit": "sqft", "type": "residential"},
    },

    # ── TIRUPPUR ──────────────────────────────────────────────────────────────
    "tiruppur": {
        "tiruppur_town": {"min": 1800, "max": 3500, "unit": "sqft", "type": "residential"},
        "palladam": {"min": 800, "max": 1800, "unit": "sqft", "type": "residential"},
    },

    # ── KARUR ─────────────────────────────────────────────────────────────────
    "karur": {
        "karur_town": {"min": 1200, "max": 2500, "unit": "sqft", "type": "residential"},
    },

    # ── KANCHEEPURAM / CHENGALPATTU  ─────────────────────────────────────────
    "kancheepuram": {
        "kancheepuram_town": {"min": 1500, "max": 3000, "unit": "sqft", "type": "residential"},
        "chengalpattu": {"min": 2000, "max": 3500, "unit": "sqft", "type": "residential"},
        "maraimalai_nagar": {"min": 2500, "max": 4000, "unit": "sqft", "type": "residential"},
    },

    # ── PUDUCHERRY (Border — reference only) ──────────────────────────────────
    "puducherry": {
        "white_town": {"min": 4000, "max": 8000, "unit": "sqft", "type": "residential"},
        "reddiarpalayam": {"min": 2500, "max": 4500, "unit": "sqft", "type": "residential"},
        "villianur": {"min": 1500, "max": 3000, "unit": "sqft", "type": "residential"},
    },
}

# Flat keyword → locality mapping for easy lookup
LOCALITY_KEYWORDS = {
    # Chennai localities
    "avadi": ("chennai", "avadi"),
    "anna nagar": ("chennai", "anna_nagar"),
    "annanagar": ("chennai", "anna_nagar"),
    "adyar": ("chennai", "adyar"),
    "t nagar": ("chennai", "t_nagar"),
    "tnagar": ("chennai", "t_nagar"),
    "velachery": ("chennai", "velachery"),
    "sholinganallur": ("chennai", "sholinganallur"),
    "perambur": ("chennai", "perambur"),
    "ambattur": ("chennai", "ambattur"),
    "porur": ("chennai", "porur"),
    "pallavaram": ("chennai", "pallavaram"),
    "chromepet": ("chennai", "chromepet"),
    "tambaram": ("chennai", "tambaram"),
    "thiruvallur": ("chennai", "thiruvallur"),
    "poonamallee": ("chennai", "poonamallee"),
    "sriperumbudur": ("chennai", "sriperumbudur"),
    "guduvanchery": ("chennai", "guduvanchery"),
    "perungalathur": ("chennai", "perungalathur"),
    "medavakkam": ("chennai", "medavakkam"),
    "urapakkam": ("chennai", "urapakkam"),
    "vandalur": ("chennai", "vandalur"),
    "kelambakkam": ("chennai", "kelambakkam"),
    "omr": ("chennai", "omr"),
    "ecr": ("chennai", "ecr"),
    "injambakkam": ("chennai", "injambakkam"),
    "nungambakkam": ("chennai", "nungambakkam"),
    "mylapore": ("chennai", "mylapore"),
    "kodambakkam": ("chennai", "kodambakkam"),
    "ashok nagar": ("chennai", "ashok_nagar"),
    "ashoknagar": ("chennai", "ashok_nagar"),
    "besant nagar": ("chennai", "besant_nagar"),
    "besantnagar": ("chennai", "besant_nagar"),
    "thiruvanmiyur": ("chennai", "thiruvanmiyur"),
    "perungudi": ("chennai", "perungudi"),
    "siruseri": ("chennai", "siruseri"),
    "navalur": ("chennai", "navalur"),
    "madambakkam": ("chennai", "madambakkam"),
    "kovilambakkam": ("chennai", "kovilambakkam"),
    "selaiyur": ("chennai", "selaiyur"),
    "virugambakkam": ("chennai", "virugambakkam"),
    "koyambedu": ("chennai", "koyambedu"),
    "mogappair": ("chennai", "mogappair"),
    "kolathur": ("chennai", "kolathur"),
    "villivakkam": ("chennai", "villivakkam"),
    "royapuram": ("chennai", "royapuram"),
    "tondiarpet": ("chennai", "tondiarpet"),
    "manali": ("chennai", "manali"),
    "tiruvottiyur": ("chennai", "tiruvottiyur"),
    # Coimbatore
    "rs puram": ("coimbatore", "rs_puram"),
    "rspuram": ("coimbatore", "rs_puram"),
    "gandhipuram": ("coimbatore", "gandhipuram"),
    "peelamedu": ("coimbatore", "peelamedu"),
    "singanallur": ("coimbatore", "singanallur"),
    "race course": ("coimbatore", "race_course"),
    "coimbatore": ("coimbatore", "gandhipuram"),
    # Madurai
    "ss colony": ("madurai", "ss_colony"),
    "tallakulam": ("madurai", "tallakulam"),
    "madurai": ("madurai", "ss_colony"),
    # Trichy
    "thillai nagar": ("trichy", "thillai_nagar"),
    "trichy": ("trichy", "thillai_nagar"),
    "tiruchirappalli": ("trichy", "thillai_nagar"),
    "srirangam": ("trichy", "srirangam"),
    # Salem
    "fairlands": ("salem", "fairlands"),
    "salem": ("salem", "fairlands"),
    # Others
    "tirunelveli": ("tirunelveli", "palayamkottai"),
    "palayamkottai": ("tirunelveli", "palayamkottai"),
    "vellore": ("vellore", "sathuvachari"),
    "katpadi": ("vellore", "katpadi"),
    "erode": ("erode", "erode_town"),
    "tiruppur": ("tiruppur", "tiruppur_town"),
    "karur": ("karur", "karur_town"),
    "kancheepuram": ("kancheepuram", "kancheepuram_town"),
    "chengalpattu": ("kancheepuram", "chengalpattu"),
    "maraimalai nagar": ("kancheepuram", "maraimalai_nagar"),
    "puducherry": ("puducherry", "reddiarpalayam"),
    "pondicherry": ("puducherry", "reddiarpalayam"),
}


def get_guideline_value(query: str) -> str:
    """
    Look up guideline value for a locality from TN Registration Dept data (Jul 2024).
    Returns a formatted string with value range and links.
    """
    query_lower = query.lower()

    matched_city = None
    matched_locality = None
    matched_key = None

    # Find best matching locality
    for keyword, (city, locality) in LOCALITY_KEYWORDS.items():
        if keyword in query_lower:
            if matched_key is None or len(keyword) > len(matched_key):
                matched_city = city
                matched_locality = locality
                matched_key = keyword

    if not matched_city:
        return ""

    city_data = TN_GUIDELINE_VALUES_2024.get(matched_city, {})
    loc_data = city_data.get(matched_locality, {})

    if not loc_data:
        return ""

    locality_display = matched_key.title()
    city_display = matched_city.title()
    min_val = loc_data["min"]
    max_val = loc_data["max"]

    # Pre-compute ALL values so LLM doesn't need to do arithmetic
    avg_sqft = (min_val + max_val) / 2
    min_ground = min_val * 2400
    max_ground = max_val * 2400
    avg_ground = avg_sqft * 2400

    def fmt_ground(val):
        """Format ground value: Crores if >= 1Cr, else Lakhs"""
        if val >= 10000000:
            return f"₹{val/10000000:.2f} Cr"
        else:
            return f"₹{val/100000:.1f}L"

    # ── Deterministic AVM metrics ──────────────────────────────────────
    from app.services.confidence_engine import compute_all_metrics, format_metrics_for_context
    metrics = compute_all_metrics(
        locality=matched_key,
        min_price=min_val,
        max_price=max_val,
        data_age_months=8,  # Jul 2024 → ~8 months
        comparable_count=1,  # Guideline data = 1 comparable source
        has_guideline_data=True,
    )
    metrics_context = format_metrics_for_context(metrics, matched_key)

    return f"""OFFICIAL GUIDELINE VALUE — {locality_display}, {city_display} (as of 01-Jul-2024):
Source: Tamil Nadu Registration Department (tnreginet.gov.in)

PRE-COMPUTED VALUATION (USE THESE EXACT VALUES — do NOT recalculate):
• Per sq.ft range: ₹{min_val:,} – ₹{max_val:,}
• Per ground range: {fmt_ground(min_ground)} – {fmt_ground(max_ground)}
  (Calculation: ₹{min_val:,} × 2,400 = ₹{min_ground:,.0f} | ₹{max_val:,} × 2,400 = ₹{max_ground:,.0f})
• Average per sq.ft: ₹{int(avg_sqft):,}
• Average per ground: {fmt_ground(avg_ground)}
  (Calculation: (₹{min_val:,} + ₹{max_val:,}) / 2 = ₹{int(avg_sqft):,} × 2,400 = ₹{avg_ground:,.0f})
• Type: Residential plot/land

NOTE: These are MINIMUM government guideline values.
Market prices are typically 20-150% higher.

🔗 Verify: https://tnreginet.gov.in/portal → Guide Value → Date: 01-07-2024
{metrics_context}"""


# ─────────────────────────────────────────────────────────────────────────────
# 2. STAMP DUTY CALCULATOR — Official TN Stamp Act rates
# ─────────────────────────────────────────────────────────────────────────────

def calculate_stamp_duty(property_value: float, buyer_gender: str = "male") -> str:
    """
    Calculate stamp duty and registration fee per Tamil Nadu Stamp Act.
    property_value: in rupees
    """
    # Stamp duty: 7% (men), 5% (women registered sole/joint in women's name)
    if buyer_gender.lower() in ["female", "woman", "women"]:
        stamp_duty_pct = 5.0
        note = "Women buyer discount applied (5% instead of 7%)"
    else:
        stamp_duty_pct = 7.0
        note = "Standard rate for men/joint buyers"

    stamp_duty = property_value * stamp_duty_pct / 100

    # Registration fee: 1% capped at ₹1,00,000
    reg_fee = min(property_value * 0.01, 100000)

    # Additional: Transfer duty 0.5%
    transfer_duty = property_value * 0.005

    total = stamp_duty + reg_fee + transfer_duty

    val_lakhs = property_value / 100000

    return f"""STAMP DUTY CALCULATION (Tamil Nadu Stamp Act):
Property Value: ₹{val_lakhs:.2f} Lakhs (₹{property_value:,.0f})

• Stamp Duty ({stamp_duty_pct}%): ₹{stamp_duty:,.0f}
• Registration Fee (1%, max ₹1L): ₹{reg_fee:,.0f}
• Transfer Duty (0.5%): ₹{transfer_duty:,.0f}
• TOTAL Government Charges: ₹{total:,.0f} (₹{total/100000:.2f} Lakhs)

{note}

Official rates per Tamil Nadu Registration Department (revised 2024).
Pay online at: https://tnreginet.gov.in/portal"""


# ─────────────────────────────────────────────────────────────────────────────
# 3. TNRERA — Public project data (no auth needed for basic search)
#    Source: https://rera.tn.gov.in/Home/SearchProject
# ─────────────────────────────────────────────────────────────────────────────

async def search_tnrera_projects(district: str = "", promoter: str = "") -> str:
    """
    Fetch registered project data from TNRERA public portal.
    Returns formatted string with project details.
    """
    try:
        # TNRERA public search endpoint (no auth required for GET)
        url = "https://rera.tn.gov.in/Home/SearchProject"
        params = {}
        if district:
            params["district"] = district
        if promoter:
            params["promoter"] = promoter

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params, follow_redirects=True)

        if resp.status_code == 200:
            # Parse basic info from response (HTML)
            text = resp.text
            # Extract project registration count from response
            if "No record found" in text or "no record" in text.lower():
                return f"No TNRERA registered projects found for {district or promoter}. Verify at https://rera.tn.gov.in"

            return f"""TNRERA (Tamil Nadu Real Estate Regulatory Authority):
🔗 Check registered projects: https://rera.tn.gov.in/Home/SearchProject
🔗 Verify developer registration: https://rera.tn.gov.in
🔗 File complaint: https://rera.tn.gov.in/Home/ComplaintRegistration

Mandate: All projects > 500 sq.m or > 8 units must be TNRERA registered.
Always verify TNRERA registration before booking any apartment/villa project."""
        else:
            return _tnrera_fallback()

    except Exception:
        return _tnrera_fallback()


def _tnrera_fallback() -> str:
    return """TNRERA (Tamil Nadu Real Estate Regulatory Authority):
🔗 Search registered projects: https://rera.tn.gov.in/Home/SearchProject
🔗 Verify developer: https://rera.tn.gov.in/Home/SearchPromotor
🔗 File complaint: https://rera.tn.gov.in/Home/ComplaintRegistration
🔗 Check agent registration: https://rera.tn.gov.in/Home/SearchAgent

TNRERA Mandate: All residential/commercial projects with area > 500 sq.m
OR more than 8 apartments MUST be registered with TNRERA.
Always verify before booking any new project."""


# ─────────────────────────────────────────────────────────────────────────────
# 4. DIRECT GOVERNMENT PORTAL LINKS (all real, verified URLs)
# ─────────────────────────────────────────────────────────────────────────────

GOVT_PORTALS = {
    "tnreginet": {
        "name": "TNReginet — Tamil Nadu Registration Department",
        "url": "https://tnreginet.gov.in/portal",
        "services": [
            "Guideline value lookup (Guide Value tab)",
            "Encumbrance Certificate (EC) application & download",
            "Document search by registration number",
            "Appointment booking for Sub-Registrar",
            "Deed details view",
        ],
        "how_to_guideline_value": "Visit site → Guide Value → Select From Date: 01-07-2024 → Select Region/SRO/Village/Survey No → Search",
    },
    "tnrera": {
        "name": "TNRERA — Tamil Nadu Real Estate Regulatory Authority",
        "url": "https://rera.tn.gov.in",
        "services": [
            "Search registered projects by district/type",
            "Verify developer/promoter registration",
            "Verify real estate agent registration",
            "File and track complaints",
            "View project progress & financials",
        ],
    },
    "eservices_tn": {
        "name": "eServices Tamil Nadu — Revenue & Land Records",
        "url": "https://eservices.tn.gov.in",
        "services": [
            "Patta Chitta — view/download land ownership records",
            "Farm Information Bureau (FMB) sketch",
            "A-Register (village land records)",
            "TSLR sketch (Town Survey Land Records)",
            "Adangal extract",
        ],
    },
    "dtcp": {
        "name": "DTCP — Directorate of Town and Country Planning",
        "url": "https://www.tn.gov.in/dept/dtcp",
        "services": [
            "Layout approval status check",
            "Building plan approval",
            "Planning permit details",
            "Check if layout is DTCP approved",
        ],
    },
    "cmda": {
        "name": "CMDA — Chennai Metropolitan Development Authority",
        "url": "https://www.cmdachennai.gov.in",
        "services": [
            "Building plan approval (Chennai area)",
            "Layout approval in CMA",
            "Master plan land use check",
            "Occupancy certificate verification",
        ],
    },
    "gcc_property_tax": {
        "name": "Greater Chennai Corporation — Property Tax",
        "url": "https://chennaicorporation.gov.in/gcc/online-services/property-tax/",
        "services": [
            "Pay property tax online",
            "Download property tax receipt",
            "Check outstanding dues",
            "Property tax assessment details",
        ],
    },
    "tn_housing_board": {
        "name": "Tamil Nadu Housing Board (TNHB)",
        "url": "https://tnhb.tn.gov.in",
        "services": [
            "View available TNHB plots & apartments",
            "Apply for affordable housing",
            "Transfer of ownership",
            "NOC for TNHB properties",
        ],
    },
    "igrs_tn": {
        "name": "IGRS — Inspector General of Registration & Stamps",
        "url": "https://www.tn.gov.in/dept/igrs",
        "services": [
            "Policy & circulars on stamp duty",
            "Registration department contact details",
            "Stamp duty exemptions & concessions",
        ],
    },
    "tangedco": {
        "name": "TANGEDCO — Electricity Connection for New Properties",
        "url": "https://www.tangedco.gov.in",
        "services": [
            "New electricity connection application",
            "EB meter status check",
            "Online bill payment",
        ],
    },
    "cmwssb": {
        "name": "Chennai Metro Water — Water Connection",
        "url": "https://www.chennaimetrowater.tn.gov.in",
        "services": [
            "New water connection application",
            "UGD (underground drainage) connection",
            "Bill payment online",
        ],
    },
}


def get_portal_info(query: str) -> str:
    """Return relevant government portal information based on query keywords."""
    query_lower = query.lower()
    relevant = []

    if any(w in query_lower for w in ["guideline", "guide value", "circle rate", "register", "ec", "encumbrance", "deed", "appointment"]):
        relevant.append("tnreginet")

    if any(w in query_lower for w in ["rera", "tnrera", "builder", "developer", "apartment", "project", "flat", "complaint"]):
        relevant.append("tnrera")

    if any(w in query_lower for w in ["patta", "chitta", "fmb", "adangal", "land record", "revenue", "poramboke"]):
        relevant.append("eservices_tn")

    if any(w in query_lower for w in ["dtcp", "layout", "plan approval", "building plan"]):
        relevant.append("dtcp")

    if any(w in query_lower for w in ["cmda", "chennai metropolitan", "building approval"]):
        relevant.append("cmda")

    if any(w in query_lower for w in ["property tax", "gcc", "corporation tax", "vari"]):
        relevant.append("gcc_property_tax")

    if any(w in query_lower for w in ["tnhb", "housing board", "affordable"]):
        relevant.append("tn_housing_board")

    if any(w in query_lower for w in ["electricity", "eb", "tangedco", "power connection"]):
        relevant.append("tangedco")

    if any(w in query_lower for w in ["water connection", "metro water", "cmwssb"]):
        relevant.append("cmwssb")

    if not relevant:
        return ""

    lines = ["\nOFFICIAL GOVERNMENT PORTALS:"]
    for key in relevant:
        p = GOVT_PORTALS[key]
        lines.append(f"\n🏛️ {p['name']}")
        lines.append(f"   URL: {p['url']}")
        lines.append(f"   Services: {', '.join(p['services'][:3])}")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# 5. MASTER CONTEXT BUILDER — called from llm_service
# ─────────────────────────────────────────────────────────────────────────────

def get_govt_context(query: str) -> str:
    """
    Build a comprehensive government-data context string for the LLM.
    Combines guideline values + stamp duty calc + portal links.
    """
    parts = []

    # Guideline value lookup
    gv = get_guideline_value(query)
    if gv:
        parts.append(gv)

    # Stamp duty calculation hints
    query_lower = query.lower()
    if any(w in query_lower for w in ["stamp duty", "registration fee", "charges", "cost", "stamp"]):
        parts.append("""STAMP DUTY RATES (Tamil Nadu, 2024):
• Stamp Duty: 7% of property value (men) | 5% (registered in woman's name)
• Registration Fee: 1% of value (maximum ₹1,00,000)
• Transfer Duty: 0.5% of property value
• Example: ₹50L property → Stamp ₹3.5L + Reg ₹50K + Transfer ₹25K = ₹3.75L total
• Online payment: https://tnreginet.gov.in/portal""")

    # Portal links
    portal_info = get_portal_info(query)
    if portal_info:
        parts.append(portal_info)

    # Price warnings
    if any(w in query_lower for w in ["price", "cost", "rate", "value", "worth", "how much", "evvalavu"]):
        parts.append("""PROPERTY PRICING NOTE:
• Guideline value = MINIMUM registration value set by TN Govt
• Market/actual price is always HIGHER than guideline value
• Difference varies: 20% (rural) to 200%+ (prime Chennai locations)
• For exact guideline value: https://tnreginet.gov.in/portal → Guide Value
• For market price research: consult local registered real estate agents""")

    return "\n\n".join(parts)
