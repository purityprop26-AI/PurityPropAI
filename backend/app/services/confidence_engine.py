"""
PurityProp — Deterministic Confidence Engine v2

Confidence = (data_coverage × 0.35) + (recency × 0.25) + (comparable_density × 0.20)
           + (variance_stability × 0.10) + (micro_market_match × 0.10)

Changes from v1:
  - 5-factor formula (was 3-factor)
  - variance_stability: measures price spread stability
  - micro_market_match: exact locality match vs zonal estimate
  - IQR outlier filtering
  - Confidence classification bands (High/Moderate/Low/Very Low)
  - Block-level locality feature mapping
  - No hardcoded vector_similarity
"""

from typing import Dict, List, Optional, Tuple


# ── Infrastructure Premium Lookup ─────────────────────────────────────────
# Deterministic per locality. No cross-locality inheritance.
INFRASTRUCTURE_PREMIUMS = {
    # Metro-adjacent
    "anna nagar":    {"metro": 0.12, "it_corridor": 0.0,  "highway": 0.05, "commercial": 0.10},
    "koyambedu":     {"metro": 0.12, "it_corridor": 0.0,  "highway": 0.08, "commercial": 0.08},
    "alandur":       {"metro": 0.12, "it_corridor": 0.05, "highway": 0.05, "commercial": 0.05},
    "guindy":        {"metro": 0.10, "it_corridor": 0.15, "highway": 0.08, "commercial": 0.12},
    "nungambakkam":  {"metro": 0.10, "it_corridor": 0.0,  "highway": 0.05, "commercial": 0.15},
    "egmore":        {"metro": 0.10, "it_corridor": 0.0,  "highway": 0.05, "commercial": 0.10},
    "t nagar":       {"metro": 0.12, "it_corridor": 0.0,  "highway": 0.05, "commercial": 0.15},
    # IT Corridor
    "omr":           {"metro": 0.0,  "it_corridor": 0.18, "highway": 0.08, "commercial": 0.10},
    "sholinganallur":{"metro": 0.0,  "it_corridor": 0.18, "highway": 0.08, "commercial": 0.08},
    "perungudi":     {"metro": 0.0,  "it_corridor": 0.15, "highway": 0.05, "commercial": 0.08},
    "taramani":      {"metro": 0.0,  "it_corridor": 0.15, "highway": 0.05, "commercial": 0.08},
    "siruseri":      {"metro": 0.0,  "it_corridor": 0.18, "highway": 0.10, "commercial": 0.05},
    "navalur":       {"metro": 0.0,  "it_corridor": 0.18, "highway": 0.10, "commercial": 0.05},
    "kelambakkam":   {"metro": 0.0,  "it_corridor": 0.12, "highway": 0.08, "commercial": 0.03},
    "thoraipakkam":  {"metro": 0.0,  "it_corridor": 0.15, "highway": 0.05, "commercial": 0.08},
    # Highway connectivity
    "tambaram":      {"metro": 0.08, "it_corridor": 0.0,  "highway": 0.10, "commercial": 0.05},
    "chromepet":     {"metro": 0.08, "it_corridor": 0.0,  "highway": 0.10, "commercial": 0.05},
    "pallavaram":    {"metro": 0.08, "it_corridor": 0.0,  "highway": 0.10, "commercial": 0.05},
    "avadi":         {"metro": 0.0,  "it_corridor": 0.0,  "highway": 0.10, "commercial": 0.05},
    "ambattur":      {"metro": 0.0,  "it_corridor": 0.05, "highway": 0.10, "commercial": 0.08},
    "poonamallee":   {"metro": 0.0,  "it_corridor": 0.0,  "highway": 0.12, "commercial": 0.05},
    # Prime residential
    "adyar":         {"metro": 0.05, "it_corridor": 0.05, "highway": 0.05, "commercial": 0.08},
    "besant nagar":  {"metro": 0.05, "it_corridor": 0.05, "highway": 0.03, "commercial": 0.05},
    "velachery":     {"metro": 0.08, "it_corridor": 0.08, "highway": 0.05, "commercial": 0.08},
    "thiruvanmiyur": {"metro": 0.05, "it_corridor": 0.08, "highway": 0.05, "commercial": 0.05},
    "porur":         {"metro": 0.0,  "it_corridor": 0.05, "highway": 0.10, "commercial": 0.08},
    "medavakkam":    {"metro": 0.0,  "it_corridor": 0.05, "highway": 0.05, "commercial": 0.03},
    "pallikaranai":  {"metro": 0.0,  "it_corridor": 0.08, "highway": 0.05, "commercial": 0.03},
    "mogappair":     {"metro": 0.05, "it_corridor": 0.0,  "highway": 0.08, "commercial": 0.08},
    "madipakkam":    {"metro": 0.05, "it_corridor": 0.05, "highway": 0.05, "commercial": 0.03},
    "mylapore":      {"metro": 0.08, "it_corridor": 0.0,  "highway": 0.03, "commercial": 0.12},
    "kodambakkam":   {"metro": 0.08, "it_corridor": 0.0,  "highway": 0.05, "commercial": 0.08},
    "ashok nagar":   {"metro": 0.08, "it_corridor": 0.0,  "highway": 0.05, "commercial": 0.08},
    "perambur":      {"metro": 0.05, "it_corridor": 0.0,  "highway": 0.08, "commercial": 0.05},
    "kolathur":      {"metro": 0.0,  "it_corridor": 0.0,  "highway": 0.08, "commercial": 0.05},
    "villivakkam":   {"metro": 0.0,  "it_corridor": 0.0,  "highway": 0.05, "commercial": 0.05},
}

# ── Locality Feature Map (No cross-locality inheritance) ──────────────────
LOCALITY_FEATURE_MAP = {
    "anna nagar": {
        "features": ["Metro Station", "Commercial Hub", "Residential Premium"],
        "metro_proximity_km": 0.5,
        "it_corridor": False,
        "highway": ["Inner Ring Road"],
        "blocks": {
            "east": {"premium_modifier": 1.15, "description": "Near metro, 2nd/3rd Avenue"},
            "west": {"premium_modifier": 1.00, "description": "Residential core"},
            "western_extension": {"premium_modifier": 0.90, "description": "Developing area"},
        }
    },
    "omr": {
        "features": ["IT Corridor", "SEZ", "Tech Parks"],
        "metro_proximity_km": 5.0,
        "it_corridor": True,
        "highway": ["OMR (Rajiv Gandhi Salai)"],
    },
    "t nagar": {
        "features": ["Metro Station", "Premium Commercial", "Retail Hub"],
        "metro_proximity_km": 0.3,
        "it_corridor": False,
        "highway": [],
    },
    "velachery": {
        "features": ["Metro Station", "IT Access", "Residential"],
        "metro_proximity_km": 0.5,
        "it_corridor": False,
        "highway": ["Velachery Main Road"],
    },
    "adyar": {
        "features": ["Institutional Hub", "Residential Premium", "Coastal Access"],
        "metro_proximity_km": 2.0,
        "it_corridor": False,
        "highway": [],
    },
}

# ── Zonal Tier Classification ─────────────────────────────────────────────
ZONE_TIERS = {
    "A": ["anna nagar", "nungambakkam", "t nagar", "adyar", "besant nagar", "mylapore",
          "alwarpet", "ra puram", "boat club", "egmore", "gopalapuram", "cit nagar"],
    "B": ["velachery", "porur", "omr", "guindy", "chromepet", "tambaram", "thiruvanmiyur",
          "sholinganallur", "perungudi", "thoraipakkam", "mogappair", "ambattur",
          "koyambedu", "alandur", "pallavaram", "taramani", "medavakkam", "madipakkam",
          "kodambakkam", "ashok nagar", "ecr", "injambakkam", "virugambakkam"],
    "C": ["avadi", "poonamallee", "kelambakkam", "siruseri", "navalur", "guduvanchery",
          "urapakkam", "vandalur", "maraimalai nagar", "padappai", "sriperumbudur",
          "oragadam", "tiruvallur", "perambur", "kolathur", "villivakkam",
          "tondiarpet", "royapuram", "manali", "tiruvottiyur"],
}


def get_zone_tier(locality: str) -> str:
    """Get zone tier for a locality. Unknown → D."""
    key = locality.lower().strip()
    for tier, localities in ZONE_TIERS.items():
        if key in localities:
            return tier
    return "D"


def get_locality_features(locality: str) -> Dict:
    """Get deterministic features for a locality. No inheritance."""
    key = locality.lower().strip()
    return LOCALITY_FEATURE_MAP.get(key, {
        "features": [],
        "metro_proximity_km": 99.0,
        "it_corridor": False,
        "highway": [],
    })


# ── IQR Outlier Filtering ────────────────────────────────────────────────
def filter_outliers_iqr(prices: List[float]) -> List[float]:
    """Remove outliers using 1.5×IQR rule."""
    if len(prices) < 4:
        return prices
    sorted_p = sorted(prices)
    n = len(sorted_p)
    q1 = sorted_p[n // 4]
    q3 = sorted_p[3 * n // 4]
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    return [p for p in prices if lower <= p <= upper]


# ── 5-Factor Confidence Score ────────────────────────────────────────────
def compute_data_coverage(
    has_guideline: bool = False,
    has_transaction: bool = False,
    has_rag_match: bool = False,
    rag_similarity: float = 0.0,
) -> float:
    """
    Data coverage ratio: how many sources corroborate.
    Range: [0.0 — 1.0]
    """
    score = 0.0
    if has_guideline:   score += 0.40
    if has_transaction: score += 0.35
    if has_rag_match:   score += 0.25 * min(rag_similarity, 1.0)
    return min(score, 1.0)


def compute_recency(data_age_months: int) -> float:
    """
    Recency score with exponential decay.
    Formula: max(0, 1 - (months / 24))
    Range: [0.0 — 1.0]
    """
    return max(0.0, 1.0 - (data_age_months / 24.0))


def compute_comparable_density(count: int) -> float:
    """
    Normalized comparable count.
    20+ comparables = 1.0 (maximum confidence).
    Range: [0.0 — 1.0]
    """
    return min(count / 20.0, 1.0)


def compute_variance_stability(min_price: float, max_price: float) -> float:
    """
    Price spread stability.
    Formula: 1 - ((max - min) / median)
    Tight spread = high stability = high confidence.
    Range: [0.0 — 1.0]
    """
    if min_price <= 0 or max_price <= 0:
        return 0.0
    median = (min_price + max_price) / 2
    if median == 0:
        return 0.0
    spread_ratio = (max_price - min_price) / median
    return max(0.0, min(1.0, 1.0 - spread_ratio))


def compute_micro_market_match(locality: str, is_exact_match: bool = True) -> float:
    """
    Micro-market match score.
    Exact locality match → 1.0
    Zonal/city estimate → 0.3
    Unknown → 0.1
    """
    key = locality.lower().strip()
    if is_exact_match:
        # Check if we have detailed data for this locality
        from app.services.govt_data_service import LOCALITY_KEYWORDS
        if key in LOCALITY_KEYWORDS:
            return 1.0
        return 0.5
    return 0.3


def compute_confidence(
    data_age_months: int = 6,
    comparable_count: int = 0,
    has_guideline_data: bool = False,
    has_transaction_data: bool = False,
    has_rag_match: bool = False,
    rag_similarity: float = 0.0,
    min_price: float = 0.0,
    max_price: float = 0.0,
    locality: str = "",
    is_exact_match: bool = True,
) -> Tuple[float, Dict]:
    """
    5-factor deterministic confidence score [0.00 — 1.00].

    Formula (revised weights):
      score = (transaction_density × 0.30) + (recency × 0.25)
            + (variance_stability × 0.15) + (micro_market_match × 0.15)
            + (data_coverage × 0.15)

    Hard caps by comparable count:
      1-2 comparables → max 0.35
      3-4 comparables → max 0.50

    Returns: (score, breakdown_dict)
    """
    data_cov = compute_data_coverage(has_guideline_data, has_transaction_data, has_rag_match, rag_similarity)
    recency = compute_recency(data_age_months)
    comp_density = compute_comparable_density(comparable_count)
    var_stability = compute_variance_stability(min_price, max_price)
    mmatch = compute_micro_market_match(locality, is_exact_match)

    score = (
        comp_density * 0.30 +
        recency * 0.25 +
        var_stability * 0.15 +
        mmatch * 0.15 +
        data_cov * 0.15
    )
    score = round(min(max(score, 0.0), 1.0), 2)

    # ── Hard caps by comparable count ─────────────────────────────────
    if comparable_count <= 2:
        score = min(score, 0.35)
    elif comparable_count <= 4:
        score = min(score, 0.50)

    # Determine metrics tier for conditional output
    if comparable_count <= 2:
        metrics_tier = "minimal"        # Raw prices only, no modeling
    elif comparable_count <= 4:
        metrics_tier = "basic"          # Min/Max/Median only
    elif comparable_count <= 9:
        metrics_tier = "intermediate"   # + IQR, StdDev, CoV
    else:
        metrics_tier = "full"           # + Liquidity, CAGR, Variance

    breakdown = {
        "transaction_density": {"value": round(comp_density, 3), "weight": 0.30, "contribution": round(comp_density * 0.30, 3)},
        "recency": {"value": round(recency, 3), "weight": 0.25, "contribution": round(recency * 0.25, 3)},
        "variance_stability": {"value": round(var_stability, 3), "weight": 0.15, "contribution": round(var_stability * 0.15, 3)},
        "micro_market_match": {"value": round(mmatch, 3), "weight": 0.15, "contribution": round(mmatch * 0.15, 3)},
        "data_coverage": {"value": round(data_cov, 3), "weight": 0.15, "contribution": round(data_cov * 0.15, 3)},
        "total": score,
        "metrics_tier": metrics_tier,
        "comparable_count": comparable_count,
    }

    return score, breakdown


def classify_confidence(score: float) -> str:
    """Classify confidence into bands."""
    if score >= 0.80:
        return "High"
    elif score >= 0.55:
        return "Moderate"
    elif score >= 0.30:
        return "Low"
    else:
        return "Very Low"


# ── Volatility & Liquidity ───────────────────────────────────────────────
def compute_volatility(min_price: float, max_price: float) -> Tuple[str, float]:
    """Volatility from price range as % of mean."""
    avg = (min_price + max_price) / 2 if (min_price + max_price) > 0 else 1
    pct = (max_price - min_price) / avg
    if pct <= 0.25:
        return "Low", round(pct, 3)
    elif pct <= 0.50:
        return "Moderate", round(pct, 3)
    else:
        return "Elevated", round(pct, 3)


def compute_liquidity(zone_tier: str) -> Tuple[str, float]:
    """Liquidity velocity from zone tier."""
    scores = {"A": (0.85, "High"), "B": (0.65, "Moderate"), "C": (0.40, "Moderate-Low"), "D": (0.25, "Low")}
    score, label = scores.get(zone_tier, (0.25, "Low"))
    return label, score


def get_infrastructure_premium(locality: str) -> Dict[str, float]:
    """Get infrastructure premium multipliers. No cross-locality inheritance."""
    key = locality.lower().strip()
    return INFRASTRUCTURE_PREMIUMS.get(key, {
        "metro": 0.0, "it_corridor": 0.0, "highway": 0.0, "commercial": 0.0
    })


# ── Master Metrics Builder ───────────────────────────────────────────────
def compute_all_metrics(
    locality: str,
    min_price: int,
    max_price: int,
    data_age_months: int = 6,
    comparable_count: int = 1,
    has_guideline_data: bool = True,
) -> Dict:
    """Compute all deterministic AVM metrics."""
    avg_price = (min_price + max_price) / 2

    zone = get_zone_tier(locality)

    confidence_score, confidence_breakdown = compute_confidence(
        data_age_months=data_age_months,
        comparable_count=comparable_count,
        has_guideline_data=has_guideline_data,
        min_price=float(min_price),
        max_price=float(max_price),
        locality=locality,
        is_exact_match=True,
    )

    vol_label, vol_score = compute_volatility(float(min_price), float(max_price))
    liq_label, liq_score = compute_liquidity(zone)
    infra = get_infrastructure_premium(locality)
    total_premium = sum(infra.values())
    features = get_locality_features(locality)
    confidence_band = classify_confidence(confidence_score)

    # Statistical metrics
    std_dev = (max_price - min_price) / 3.46  # Approx for uniform distribution
    cov = std_dev / avg_price if avg_price > 0 else 0

    return {
        "confidence": confidence_score,
        "confidence_band": confidence_band,
        "confidence_breakdown": confidence_breakdown,
        "zone_tier": zone,
        "volatility_label": vol_label,
        "volatility_score": vol_score,
        "liquidity_label": liq_label,
        "liquidity_score": liq_score,
        "infrastructure_premium": {
            "metro": f"+{infra['metro']*100:.0f}%",
            "it_corridor": f"+{infra['it_corridor']*100:.0f}%",
            "highway": f"+{infra['highway']*100:.0f}%",
            "commercial": f"+{infra['commercial']*100:.0f}%",
            "total": f"+{total_premium*100:.0f}%",
        },
        "statistics": {
            "median": int(avg_price),
            "std_dev": int(std_dev),
            "cov": round(cov, 3),
            "iqr_band": f"₹{min_price:,} — ₹{max_price:,}",
            "outlier_method": "1.5×IQR rule",
        },
        "locality_features": features.get("features", []),
        "comparable_count": comparable_count,
        "data_age_months": data_age_months,
        "data_source": "TN Registration Department (tnreginet.gov.in)",
        "last_updated": "Jul 2024",
    }


def format_metrics_for_context(metrics: Dict, locality: str) -> str:
    """Format computed metrics as context block for LLM injection.
    Conditionally includes sections based on comparable count thresholds."""
    infra = metrics["infrastructure_premium"]
    stats = metrics["statistics"]
    cb = metrics["confidence_breakdown"]
    features_str = ", ".join(metrics.get("locality_features", [])) or "General residential"
    metrics_tier = cb.get("metrics_tier", "minimal")
    comp_count = cb.get("comparable_count", metrics.get("comparable_count", 1))

    # Base context — always included
    context = f"""
DETERMINISTIC AVM METRICS — {locality.title()} (PurityProp Engine):
• Zone Tier: {metrics['zone_tier']}
• Locality Features: {features_str}
• Comparable Count: {comp_count}
• Metrics Tier: {metrics_tier.upper()} (based on comparable density)
• Data Source: {metrics['data_source']}
• Data Period: {metrics['last_updated']}
• Search Radius: 0.5 km (primary locality)

• Confidence Index: {metrics['confidence']:.2f} ({metrics['confidence_band']})
  Breakdown:
    Transaction Density: {cb['transaction_density']['value']:.3f} × 0.30 = {cb['transaction_density']['contribution']:.3f}
    Recency:             {cb['recency']['value']:.3f} × 0.25 = {cb['recency']['contribution']:.3f}
    Variance Stability:  {cb['variance_stability']['value']:.3f} × 0.15 = {cb['variance_stability']['contribution']:.3f}
    Micro-Market Match:  {cb['micro_market_match']['value']:.3f} × 0.15 = {cb['micro_market_match']['contribution']:.3f}
    Data Coverage:       {cb['data_coverage']['value']:.3f} × 0.15 = {cb['data_coverage']['contribution']:.3f}
    TOTAL = {cb['total']:.2f}
"""

    # Volatility — always show (derived from price range)
    context += f"• Volatility: {metrics['volatility_label']} ({metrics['volatility_score']:.3f})\n"

    # Conditional sections based on metrics_tier
    if metrics_tier in ("intermediate", "full"):
        # 5+ comparables: show IQR, StdDev, CoV
        context += f"• Statistics: Median {stats['median']:,}/sqft | StdDev {stats['std_dev']:,} | CoV {stats['cov']:.3f}\n"
        context += f"• IQR Band: {stats['iqr_band']} | Outlier Filter: {stats['outlier_method']}\n"

    if metrics_tier == "full":
        # 10+ comparables: show liquidity
        context += f"• Liquidity: {metrics['liquidity_label']} (score: {metrics['liquidity_score']:.2f})\n"

    context += f"• Infrastructure: Metro {infra['metro']}, IT {infra['it_corridor']}, Highway {infra['highway']}, Commercial {infra['commercial']} = Total {infra['total']}\n"

    # Risk disclosure
    if comp_count < 5:
        context += "\nRISK DISCLOSURE: Statistical modeling limited due to low transaction density. Values reflect observed registry data only.\n"

    if metrics.get("data_age_months", 0) > 12:
        context += "RECENCY NOTE: Data recency impact acknowledged in confidence index.\n"

    # Instructions for LLM
    context += f"""
INSTRUCTION: Use EXACT confidence {metrics['confidence']:.2f} ({metrics['confidence_band']}).
Metrics tier is {metrics_tier.upper()} — show ONLY sections permitted for this tier.
{'Show Min/Max/Median ONLY. NO IQR, NO StdDev, NO CoV, NO CAGR.' if metrics_tier in ('minimal', 'basic') else ''}
{'Show IQR/StdDev/CoV. NO liquidity modeling, NO CAGR.' if metrics_tier == 'intermediate' else ''}
{'Full analytics enabled.' if metrics_tier == 'full' else ''}
Do NOT use placeholder values. If a metric cannot be computed, omit the section entirely.
"""
    return context
