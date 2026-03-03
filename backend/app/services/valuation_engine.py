"""
PurityProp — Deterministic Valuation Engine (Database-Backed)
==============================================================

Replaces confidence_engine.py's hardcoded logic with DB-driven computation.
All numeric outputs are deterministic — LLM never computes prices.

Inputs: RAG retrieval result from rag_retrieval.rag_retrieve()
Outputs: Structured JSON with all valuation metrics.
"""

from __future__ import annotations

import math
import structlog
from typing import Any, Dict, Optional
from datetime import date

logger = structlog.get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────
# CONFIDENCE CAPS (from 9/10 spec — immutable)
# ─────────────────────────────────────────────────────────────────────
CONFIDENCE_CAPS = {
    1: 0.35,
    2: 0.45,
    4: 0.60,
    9: 0.75,
    999: 0.90,  # 10+
}

METRICS_TIERS = {
    2: "minimal",     # 1-2 comps: raw price only
    4: "basic",       # 3-4 comps: min/max/median
    9: "intermediate", # 5-9 comps: + IQR, StdDev, CoV
    999: "full",       # 10+ comps: everything
}


def _get_cap(count: int) -> float:
    for threshold, cap in sorted(CONFIDENCE_CAPS.items()):
        if count <= threshold:
            return cap
    return 0.90


def _get_tier(count: int) -> str:
    for threshold, tier in sorted(METRICS_TIERS.items()):
        if count <= threshold:
            return tier
    return "full"


# ─────────────────────────────────────────────────────────────────────
# MAIN VALUATION FUNCTION
# ─────────────────────────────────────────────────────────────────────

def compute_valuation(rag_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute deterministic valuation from RAG retrieval result.

    Input: output of rag_retrieval.rag_retrieve()
    Output: structured JSON with all metrics for LLM formatting.

    The LLM receives this JSON — it formats, never computes.
    """
    if not rag_result.get("has_data"):
        return {
            "has_data": False,
            "locality": rag_result.get("locality", "unknown"),
            "message": rag_result.get("message", "No data available"),
        }

    locality = rag_result["locality"]
    asset_type = rag_result["asset_type"]
    data_source = rag_result["data_source"]
    comparable_count = rag_result["comparable_count"]
    data_age_months = rag_result.get("data_age_months", 24)

    price_min = rag_result["price_min"]
    price_max = rag_result["price_max"]
    price_median = rag_result["price_median"]

    stats = rag_result.get("stats")
    metadata = rag_result.get("metadata", {})
    guideline = rag_result.get("guideline")

    # ── Metrics Tier ────────────────────────────────────────────────
    metrics_tier = _get_tier(comparable_count)

    # ── Ground calculations ─────────────────────────────────────────
    SQFT_PER_GROUND = 2400
    min_per_ground = price_min * SQFT_PER_GROUND
    max_per_ground = price_max * SQFT_PER_GROUND
    median_per_ground = price_median * SQFT_PER_GROUND

    # ── Statistical metrics (conditional on tier) ───────────────────
    statistical = {}
    if stats and metrics_tier in ("intermediate", "full"):
        statistical["q1_price"] = stats.get("q1_price", 0)
        statistical["q3_price"] = stats.get("q3_price", 0)
        statistical["iqr"] = statistical["q3_price"] - statistical["q1_price"]
        statistical["std_dev"] = stats.get("std_dev", 0)
        statistical["cov"] = stats.get("cov", 0)
    if stats and metrics_tier == "full":
        # Liquidity = transactions per month (requires date range)
        if stats.get("earliest_date") and stats.get("latest_date"):
            try:
                d1 = date.fromisoformat(stats["earliest_date"])
                d2 = date.fromisoformat(stats["latest_date"])
                span_months = max(1, (d2 - d1).days / 30)
                statistical["liquidity_txn_per_month"] = round(comparable_count / span_months, 2)
            except (ValueError, TypeError):
                pass

    # ── Zone & Infrastructure ───────────────────────────────────────
    zone_tier = metadata.get("zone_tier", "C")
    features = metadata.get("features", [])
    infra_premium = metadata.get("infra_premium", {})

    # ── Confidence Score (5-factor formula) ──────────────────────────
    # Factor 1: Transaction density (30%)
    density_score = min(comparable_count / 20.0, 1.0)

    # Factor 2: Recency (25%)
    recency_score = max(0.0, 1.0 - (data_age_months / 24.0))

    # Factor 3: Variance stability (15%)
    if price_median > 0 and price_max > price_min:
        spread = (price_max - price_min) / price_median
        variance_score = max(0.0, 1.0 - spread)
    else:
        variance_score = 0.5

    # Factor 4: Micro-market match (15%)
    micro_match = 1.0  # Exact locality match from DB

    # Factor 5: Data coverage (15%)
    coverage = 0.0
    if guideline:
        coverage += 0.40
    if rag_result.get("has_registry_data"):
        coverage += 0.35
    if comparable_count >= 5:
        coverage += 0.25

    # Weighted sum
    confidence_raw = (
        density_score * 0.30 +
        recency_score * 0.25 +
        variance_score * 0.15 +
        micro_match * 0.15 +
        coverage * 0.15
    )
    confidence_raw = round(min(max(confidence_raw, 0.0), 1.0), 2)

    # Apply hard cap
    cap = _get_cap(comparable_count)
    confidence = min(confidence_raw, cap)

    # Confidence band
    if confidence < 0.40:
        confidence_band = "Low"
    elif confidence < 0.65:
        confidence_band = "Moderate"
    elif confidence < 0.80:
        confidence_band = "High"
    else:
        confidence_band = "Very High"

    # ── Volatility ──────────────────────────────────────────────────
    if price_median > 0:
        volatility_score = round((price_max - price_min) / price_median, 3)
    else:
        volatility_score = 0.0
    if volatility_score < 0.20:
        volatility_label = "Low"
    elif volatility_score < 0.40:
        volatility_label = "Moderate"
    else:
        volatility_label = "Elevated"

    # ── Risk Disclosures ────────────────────────────────────────────
    risks = []
    if comparable_count <= 2:
        risks.append("⚠️ Low transaction density — statistical modeling limited")
    if comparable_count == 1:
        risks.append("⚠️ Single data point — no range modeling performed")
    if data_age_months > 12:
        risks.append(f"⚠️ Data older than 12 months ({data_age_months}mo) — values may not reflect current conditions")
    if data_source == "guideline_values":
        risks.append("⚠️ Derived from government guideline values only — no actual transactions in database")
    if volatility_label == "Elevated":
        risks.append("⚠️ Elevated price variance detected in this micro-market")

    # ── Build final result ──────────────────────────────────────────
    result = {
        "has_data": True,
        "locality": locality,
        "asset_type": asset_type,
        "data_source": data_source,
        "metrics_tier": metrics_tier,

        # Pricing
        "comparable_count": comparable_count,
        "price_per_sqft": {
            "min": round(price_min, 2),
            "max": round(price_max, 2),
            "median": round(price_median, 2),
        },
        "price_per_ground": {
            "min": round(min_per_ground, 0),
            "max": round(max_per_ground, 0),
            "median": round(median_per_ground, 0),
        },

        # Confidence
        "confidence": {
            "score": confidence,
            "band": confidence_band,
            "cap_applied": cap,
            "breakdown": {
                "density": round(density_score, 3),
                "recency": round(recency_score, 3),
                "variance_stability": round(variance_score, 3),
                "micro_match": round(micro_match, 3),
                "coverage": round(coverage, 3),
            },
        },

        # Zone
        "zone_tier": zone_tier,
        "features": features,
        "infra_premium": infra_premium,

        # Volatility
        "volatility": {
            "score": volatility_score,
            "label": volatility_label,
        },

        # Data metadata
        "data_age_months": data_age_months,
        "date_range": {
            "earliest": stats.get("earliest_date") if stats else None,
            "latest": stats.get("latest_date") if stats else None,
        },

        # Guideline reference
        "guideline_value": {
            "min": guideline["min_per_sqft"] if guideline else None,
            "max": guideline["max_per_sqft"] if guideline else None,
            "effective_date": guideline.get("effective_date") if guideline else None,
        } if guideline else None,

        # Risk disclosures
        "risks": risks,

        # Source verification
        "verification_url": "https://tnreginet.gov.in/portal",
    }

    # Add statistical metrics conditionally
    if statistical:
        result["statistical"] = statistical

    # Alias keys for audit/simplifier compatibility
    result["pricing"] = {
        "min_sqft": price_min,
        "max_sqft": price_max,
        "median_sqft": price_median,
        "std_dev": statistical.get("std_dev"),
        "q1": statistical.get("q1_price"),
        "q3": statistical.get("q3_price"),
        "iqr": statistical.get("iqr"),
        "cov": statistical.get("cov"),
    }
    result["price_min"] = price_min
    result["price_max"] = price_max
    result["price_median"] = price_median

    logger.info(
        "valuation_computed",
        locality=locality,
        comparable_count=comparable_count,
        confidence=confidence,
        tier=metrics_tier,
        source=data_source,
    )

    return result


# ─────────────────────────────────────────────────────────────────────
# FORMAT FOR LLM CONTEXT INJECTION
# ─────────────────────────────────────────────────────────────────────

def format_valuation_for_llm(valuation: Dict[str, Any]) -> str:
    """
    Convert structured valuation JSON into a text block for LLM context.
    The LLM reads this and formats it — it does NOT compute.
    """
    if not valuation.get("has_data"):
        return f"NO DATA AVAILABLE for {valuation.get('locality', 'unknown')}. {valuation.get('message', '')}"

    v = valuation
    price = v["price_per_sqft"]
    ground = v["price_per_ground"]
    conf = v["confidence"]
    tier = v["metrics_tier"]

    lines = [
        "═══ REGISTRY-BACKED VALUATION DATA (PRE-COMPUTED) ═══",
        f"Locality: {v['locality']}",
        f"District: {v.get('zone_tier', 'N/A')} Zone | Asset: {v['asset_type']}",
        f"Data Source: {v['data_source']}",
        f"Comparable Count: {v['comparable_count']}",
        f"Metrics Tier: {tier.upper()}",
        "",
        f"Price/sqft: ₹{price['min']:,.0f} – ₹{price['max']:,.0f} (Median: ₹{price['median']:,.0f})",
        f"Price/ground: ₹{ground['min']:,.0f} – ₹{ground['max']:,.0f} (Median: ₹{ground['median']:,.0f})",
        f"(1 Ground = 2,400 sq.ft)",
    ]

    # Guideline reference
    gv = v.get("guideline_value")
    if gv and gv.get("min"):
        lines.append(f"Guideline Value: ₹{gv['min']:,.0f} – ₹{gv['max']:,.0f}/sqft (effective: {gv.get('effective_date', 'N/A')})")

    # Statistical metrics (conditional)
    stat = v.get("statistical", {})
    if tier in ("intermediate", "full") and stat:
        lines.append("")
        lines.append("Statistical Metrics:")
        if stat.get("q1_price") is not None:
            lines.append(f"  IQR Band: ₹{stat['q1_price']:,.0f} – ₹{stat['q3_price']:,.0f}")
        if stat.get("std_dev"):
            lines.append(f"  Std Dev: ₹{stat['std_dev']:,.0f}")
        if stat.get("cov"):
            lines.append(f"  CoV: {stat['cov']:.3f}")
        if stat.get("liquidity_txn_per_month"):
            lines.append(f"  Liquidity: {stat['liquidity_txn_per_month']} txn/month")

    # Confidence
    lines.extend([
        "",
        f"Confidence: {conf['score']} ({conf['band']}) [cap: {conf['cap_applied']}]",
        f"  Density: {conf['breakdown']['density']:.3f} × 0.30",
        f"  Recency: {conf['breakdown']['recency']:.3f} × 0.25",
        f"  Variance: {conf['breakdown']['variance_stability']:.3f} × 0.15",
        f"  Match: {conf['breakdown']['micro_match']:.3f} × 0.15",
        f"  Coverage: {conf['breakdown']['coverage']:.3f} × 0.15",
    ])

    # Volatility
    vol = v.get("volatility", {})
    lines.append(f"Volatility: {vol.get('label', 'N/A')} ({vol.get('score', 0):.3f})")

    # Features
    if v.get("features"):
        lines.append(f"Locality Features: {', '.join(v['features'])}")

    # Infrastructure premiums
    if v.get("infra_premium"):
        premiums = [f"{k}: +{int(val*100)}%" for k, val in v["infra_premium"].items() if val > 0]
        if premiums:
            lines.append(f"Infrastructure Premiums: {', '.join(premiums)}")

    # Risks
    if v.get("risks"):
        lines.append("")
        lines.append("Risk Disclosures:")
        for r in v["risks"]:
            lines.append(f"  {r}")

    # Tier instructions for LLM
    lines.extend([
        "",
        "═══ LLM FORMATTING INSTRUCTIONS ═══",
        f"Metrics Tier: {tier.upper()}",
    ])
    if tier == "minimal":
        lines.append("SHOW: Observed price, per-ground calculation, density warning")
        lines.append("HIDE: Range modeling, IQR, StdDev, CoV, CAGR, Liquidity")
    elif tier == "basic":
        lines.append("SHOW: Min, Max, Median, per-ground calculations")
        lines.append("HIDE: IQR, StdDev, CoV, CAGR, Liquidity")
    elif tier == "intermediate":
        lines.append("SHOW: All basic + IQR, StdDev, CoV")
        lines.append("HIDE: CAGR, Liquidity")
    else:
        lines.append("SHOW: All metrics including CAGR, Liquidity")

    lines.append("RULE: Use EXACT values above. Do NOT generate new numbers.")
    lines.append(f"Verify: {v.get('verification_url', 'https://tnreginet.gov.in/portal')}")

    return "\n".join(lines)
