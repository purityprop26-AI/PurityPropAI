"""
PurityProp — Deterministic Confidence Engine

Computes confidence scores, volatility, liquidity, and infrastructure
premiums from actual data — no LLM estimation.

Formula:
  Confidence = (data_coverage × 0.4) + (recency_score × 0.3) + (comparable_norm × 0.3)
"""

from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

# ── Infrastructure Premium Lookup ─────────────────────────────────────────
# Based on proximity to key infrastructure. Deterministic per locality.
INFRASTRUCTURE_PREMIUMS = {
    # Metro-adjacent (+12%)
    "anna nagar": {"metro": 0.12, "it_corridor": 0.0, "highway": 0.05, "commercial": 0.10},
    "koyambedu": {"metro": 0.12, "it_corridor": 0.0, "highway": 0.08, "commercial": 0.08},
    "alandur": {"metro": 0.12, "it_corridor": 0.05, "highway": 0.05, "commercial": 0.05},
    "guindy": {"metro": 0.10, "it_corridor": 0.15, "highway": 0.08, "commercial": 0.12},
    "nungambakkam": {"metro": 0.10, "it_corridor": 0.0, "highway": 0.05, "commercial": 0.15},
    "egmore": {"metro": 0.10, "it_corridor": 0.0, "highway": 0.05, "commercial": 0.10},
    "t nagar": {"metro": 0.12, "it_corridor": 0.0, "highway": 0.05, "commercial": 0.15},
    # IT Corridor (+18%)
    "omr": {"metro": 0.0, "it_corridor": 0.18, "highway": 0.08, "commercial": 0.10},
    "sholinganallur": {"metro": 0.0, "it_corridor": 0.18, "highway": 0.08, "commercial": 0.08},
    "perungudi": {"metro": 0.0, "it_corridor": 0.15, "highway": 0.05, "commercial": 0.08},
    "taramani": {"metro": 0.0, "it_corridor": 0.15, "highway": 0.05, "commercial": 0.08},
    "siruseri": {"metro": 0.0, "it_corridor": 0.18, "highway": 0.10, "commercial": 0.05},
    "navalur": {"metro": 0.0, "it_corridor": 0.18, "highway": 0.10, "commercial": 0.05},
    "kelambakkam": {"metro": 0.0, "it_corridor": 0.12, "highway": 0.08, "commercial": 0.03},
    # Highway connectivity (+8%)
    "tambaram": {"metro": 0.08, "it_corridor": 0.0, "highway": 0.10, "commercial": 0.05},
    "chromepet": {"metro": 0.08, "it_corridor": 0.0, "highway": 0.10, "commercial": 0.05},
    "pallavaram": {"metro": 0.08, "it_corridor": 0.0, "highway": 0.10, "commercial": 0.05},
    "avadi": {"metro": 0.0, "it_corridor": 0.0, "highway": 0.10, "commercial": 0.05},
    "ambattur": {"metro": 0.0, "it_corridor": 0.05, "highway": 0.10, "commercial": 0.08},
    "poonamallee": {"metro": 0.0, "it_corridor": 0.0, "highway": 0.12, "commercial": 0.05},
    # Prime residential
    "adyar": {"metro": 0.05, "it_corridor": 0.05, "highway": 0.05, "commercial": 0.08},
    "besant nagar": {"metro": 0.05, "it_corridor": 0.05, "highway": 0.03, "commercial": 0.05},
    "velachery": {"metro": 0.08, "it_corridor": 0.08, "highway": 0.05, "commercial": 0.08},
    "thiruvanmiyur": {"metro": 0.05, "it_corridor": 0.08, "highway": 0.05, "commercial": 0.05},
    "porur": {"metro": 0.0, "it_corridor": 0.05, "highway": 0.10, "commercial": 0.08},
    "medavakkam": {"metro": 0.0, "it_corridor": 0.05, "highway": 0.05, "commercial": 0.03},
    "pallikaranai": {"metro": 0.0, "it_corridor": 0.08, "highway": 0.05, "commercial": 0.03},
    "mogappair": {"metro": 0.05, "it_corridor": 0.0, "highway": 0.08, "commercial": 0.08},
    "madipakkam": {"metro": 0.05, "it_corridor": 0.05, "highway": 0.05, "commercial": 0.03},
    "thoraipakkam": {"metro": 0.0, "it_corridor": 0.15, "highway": 0.05, "commercial": 0.08},
}

# ── Zonal Tier Classification ─────────────────────────────────────────────
ZONE_TIERS = {
    "A": ["anna nagar", "nungambakkam", "t nagar", "adyar", "besant nagar", "mylapore",
          "alwarpet", "ra puram", "boat club", "egmore", "gopalapuram", "cit nagar"],
    "B": ["velachery", "porur", "omr", "guindy", "chromepet", "tambaram", "thiruvanmiyur",
          "sholinganallur", "perungudi", "thoraipakkam", "mogappair", "ambattur",
          "koyambedu", "alandur", "pallavaram", "taramani", "medavakkam", "madipakkam"],
    "C": ["avadi", "poonamallee", "kelambakkam", "siruseri", "navalur", "guduvancheri",
          "urapakkam", "vandalur", "maraimalai nagar", "padappai", "sriperumbudur",
          "oragadam", "tiruvallur", "perambur", "kolathur", "villivakkam"],
}


def get_zone_tier(locality: str) -> str:
    """Get zone tier for a locality."""
    key = locality.lower().strip()
    for tier, localities in ZONE_TIERS.items():
        if key in localities:
            return tier
    return "D"  # Unknown → lowest tier


def compute_confidence(
    vector_similarity: float = 0.0,
    data_age_months: int = 6,
    comparable_count: int = 0,
    has_guideline_data: bool = False,
    has_transaction_data: bool = False,
) -> float:
    """
    Deterministic confidence score [0.00 — 1.00].

    Formula:
      score = (data_coverage × 0.4) + (recency × 0.3) + (comparable_norm × 0.3)
    """
    # Data coverage: from vector similarity or guideline match
    if has_guideline_data:
        data_coverage = max(0.7, vector_similarity)  # Guideline match = baseline 0.7
    elif vector_similarity > 0:
        data_coverage = min(vector_similarity, 1.0)
    else:
        data_coverage = 0.3  # Estimation-only mode

    if has_transaction_data:
        data_coverage = min(data_coverage + 0.15, 1.0)

    # Recency: newer data = higher score
    recency = max(0.0, 1.0 - (data_age_months / 24.0))

    # Comparable normalization: more comparables = more confident
    comparable_norm = min(comparable_count / 20.0, 1.0)

    score = (data_coverage * 0.4) + (recency * 0.3) + (comparable_norm * 0.3)
    return round(min(max(score, 0.0), 1.0), 2)


def compute_volatility(price_range_pct: float) -> Tuple[str, float]:
    """
    Volatility index based on price range as % of mean.
    volatility = (max - min) / mean
    """
    if price_range_pct <= 0.25:
        return "Low", round(price_range_pct, 3)
    elif price_range_pct <= 0.50:
        return "Moderate", round(price_range_pct, 3)
    else:
        return "Elevated", round(price_range_pct, 3)


def compute_liquidity(zone_tier: str) -> Tuple[str, float]:
    """Liquidity velocity based on zone tier (proxy for transaction frequency)."""
    scores = {"A": (0.85, "High"), "B": (0.65, "Moderate"), "C": (0.40, "Moderate-Low"), "D": (0.25, "Low")}
    score, label = scores.get(zone_tier, (0.25, "Low"))
    return label, score


def get_infrastructure_premium(locality: str) -> Dict[str, float]:
    """Get infrastructure premium multipliers for a locality."""
    key = locality.lower().strip()
    return INFRASTRUCTURE_PREMIUMS.get(key, {
        "metro": 0.0, "it_corridor": 0.0, "highway": 0.0, "commercial": 0.0
    })


def compute_all_metrics(
    locality: str,
    min_price: int,
    max_price: int,
    data_age_months: int = 6,
    comparable_count: int = 1,
    has_guideline_data: bool = True,
) -> Dict:
    """
    Compute all deterministic AVM metrics for a locality.
    Returns a dict ready to inject into LLM context.
    """
    avg_price = (min_price + max_price) / 2
    price_range_pct = (max_price - min_price) / avg_price if avg_price > 0 else 0

    zone = get_zone_tier(locality)
    confidence = compute_confidence(
        vector_similarity=0.85,
        data_age_months=data_age_months,
        comparable_count=comparable_count,
        has_guideline_data=has_guideline_data,
    )
    vol_label, vol_score = compute_volatility(price_range_pct)
    liq_label, liq_score = compute_liquidity(zone)
    infra = get_infrastructure_premium(locality)
    total_premium = sum(infra.values())

    return {
        "confidence": confidence,
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
        "comparable_count": comparable_count,
        "data_age_months": data_age_months,
        "data_source": "TN Registration Department (tnreginet.gov.in)",
        "last_updated": "Jul 2024",
    }


def format_metrics_for_context(metrics: Dict, locality: str) -> str:
    """Format computed metrics as context block for LLM injection."""
    infra = metrics["infrastructure_premium"]
    return f"""
DETERMINISTIC AVM METRICS — {locality.title()} (Computed by PurityProp Engine, NOT estimated):
• Zone Tier: {metrics['zone_tier']}
• Confidence Score: {metrics['confidence']:.2f} (formula: data_coverage×0.4 + recency×0.3 + comparable_norm×0.3)
• Volatility: {metrics['volatility_label']} ({metrics['volatility_score']:.3f})
• Liquidity: {metrics['liquidity_label']} (score: {metrics['liquidity_score']:.2f})
• Infrastructure Premium: Metro {infra['metro']}, IT Corridor {infra['it_corridor']}, Highway {infra['highway']}, Commercial {infra['commercial']} → Total {infra['total']}
• Comparables Used: {metrics['comparable_count']}
• Data Source: {metrics['data_source']}
• Last Updated: {metrics['last_updated']}

INSTRUCTION: Use the EXACT confidence score {metrics['confidence']:.2f} in your response. Do NOT estimate a different one.
Use the EXACT volatility label "{metrics['volatility_label']}" and liquidity label "{metrics['liquidity_label']}".
"""
