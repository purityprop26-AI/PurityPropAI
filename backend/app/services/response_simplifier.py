"""
PurityProp — Response Simplification Layer
=============================================

Dual output mode:
  - 'institutional': Technical, precise, for investors/analysts
  - 'simplified':    Plain English, for normal users

Implements English simplification rules:
  - "percentile" → "range"
  - "standard deviation" → removed
  - "liquidity score" → "Buying/selling activity is high/medium/low"
  - "confidence index" → "Data strength: Strong / Moderate / Limited"
"""

from __future__ import annotations
from typing import Any, Dict


def simplify_valuation_for_user(valuation: Dict[str, Any]) -> str:
    """
    Convert technical valuation JSON into plain English.
    Zero jargon. Zero formulas. No internal logic exposed.
    """
    if not valuation.get('has_data'):
        return (
            "Sorry, we don't have enough property data for this area yet. "
            "Try searching for a nearby well-known locality."
        )

    locality = valuation.get('locality', 'this area').replace('_', ' ').title()
    asset = valuation.get('asset_type', 'land')
    source = valuation.get('data_source', 'unknown')
    comps = valuation.get('comparable_count', 0)

    # Extract prices
    pricing = valuation.get('price_per_sqft', {})
    if isinstance(pricing, dict):
        p_min = pricing.get('min', 0)
        p_max = pricing.get('max', 0)
        p_med = pricing.get('median', 0)
    else:
        p_min = valuation.get('price_min', 0)
        p_max = valuation.get('price_max', 0)
        p_med = valuation.get('price_median', 0)

    # Ground price (for 2400 sqft standard plot)
    ground = valuation.get('price_per_ground', {})
    if isinstance(ground, dict):
        g_min = ground.get('min', 0)
        g_max = ground.get('max', 0)
    else:
        g_min = p_min * 2400 if p_min else 0
        g_max = p_max * 2400 if p_max else 0

    # Guideline value
    gv = valuation.get('guideline_value', {})
    if isinstance(gv, dict):
        gv_min = gv.get('min', 0)
        gv_max = gv.get('max', 0)
    else:
        gv_min = 0
        gv_max = 0

    # Confidence → plain English
    conf = valuation.get('confidence', {})
    conf_score = conf.get('score', 0) if isinstance(conf, dict) else 0
    if conf_score >= 0.8:
        data_strength = "Strong"
        data_note = "This is based on many recent property registrations."
    elif conf_score >= 0.5:
        data_strength = "Moderate"
        data_note = "This is based on a fair number of recent sales."
    else:
        data_strength = "Limited"
        data_note = "We have limited data for this area, so treat this as an estimate."

    # Build response
    lines = []

    # Source clarity — distinguish guideline-only from registry-backed
    is_guideline_only = (
        source in ('guideline', 'guideline_values')
        or comps <= 1
        and conf_score < 0.4
    )
    if is_guideline_only and 'registry' not in source:
        lines.append(
            f"⚠️ *Note: Limited registry data for {locality}. "
            f"Prices shown are based on government guideline values.*\n"
        )

    # Main price line
    if p_min and p_max and p_min != p_max:
        lines.append(
            f"**{asset.title()} prices in {locality}** are currently "
            f"between **Rs.{p_min:,.0f}** and **Rs.{p_max:,.0f} per sq.ft**."
        )
    elif p_med:
        lines.append(
            f"**{asset.title()} prices in {locality}** are around "
            f"**Rs.{p_med:,.0f} per sq.ft**."
        )

    # Fair average
    if p_med and p_med > 0:
        lines.append(
            f"Based on recent registrations, **Rs.{p_med:,.0f} per sq.ft** "
            f"is a fair average."
        )

    # Ground value (meaningful for land)
    if asset == 'land' and g_min and g_max:
        lines.append(
            f"\nFor a standard ground (2,400 sq.ft), that's roughly "
            f"**Rs.{g_min/100000:,.1f} lakh to Rs.{g_max/100000:,.1f} lakh**."
        )

    # Government guideline
    if gv_min and gv_max:
        lines.append(
            f"\nThe government guideline value is "
            f"Rs.{gv_min:,.0f} – Rs.{gv_max:,.0f} per sq.ft."
        )

    # Data strength (replaces "confidence index")
    lines.append(f"\n**Data strength:** {data_strength}. {data_note}")

    # Activity level (replaces "liquidity score")
    if comps >= 5:
        lines.append("Buying and selling activity is **high** in this area.")
    elif comps >= 3:
        lines.append("Buying and selling activity is **moderate** in this area.")
    else:
        lines.append("Buying and selling activity is **low** in this area.")

    # Risks — simplified and DEDUPLICATED
    risks = valuation.get('risks', [])
    if risks:
        seen_risks = set()
        simplified_risks = []
        for r in risks:
            r_lower = r.lower()
            if 'variance' in r_lower or 'volatile' in r_lower:
                msg = "Prices vary quite a bit in this area — negotiate carefully."
            elif 'older' in r_lower or 'data age' in r_lower:
                msg = "Our data is a few months old, so current prices may differ slightly."
            elif 'guideline' in r_lower:
                msg = "This estimate is based on government values, not actual sales."
            elif 'single' in r_lower or 'low' in r_lower or 'insufficient' in r_lower:
                msg = "Very few sales recorded — get a local broker's opinion too."
            else:
                continue
            # Deduplicate
            if msg not in seen_risks:
                seen_risks.add(msg)
                simplified_risks.append(msg)
        if simplified_risks:
            lines.append("\n**Things to keep in mind:**")
            for sr in simplified_risks:
                lines.append(f"• {sr}")

    return "\n".join(lines)



def format_institutional(valuation: Dict[str, Any]) -> str:
    """
    Technical/institutional output for analysts and investors.
    Includes confidence scores, percentiles, CoV, etc.
    """
    if not valuation.get('has_data'):
        return "No comparable data available for this locality."

    locality = valuation.get('locality', 'unknown')
    asset = valuation.get('asset_type', 'land')
    source = valuation.get('data_source', 'unknown')
    comps = valuation.get('comparable_count', 0)
    tier = valuation.get('metrics_tier', 'unknown')

    pricing = valuation.get('price_per_sqft', {})
    conf = valuation.get('confidence', {})

    lines = [
        f"═══ INSTITUTIONAL VALUATION REPORT ═══",
        f"Locality: {locality} | Asset: {asset} | Source: {source}",
        f"Comparable Count: {comps} | Metrics Tier: {tier}",
        "",
    ]

    if isinstance(pricing, dict):
        lines.append(f"Price/sqft: Min ₹{pricing.get('min', 0):,.0f} | "
                     f"Median ₹{pricing.get('median', 0):,.0f} | "
                     f"Max ₹{pricing.get('max', 0):,.0f}")

    if isinstance(conf, dict):
        lines.append(f"Confidence: {conf.get('score', 0):.2f} ({conf.get('band', 'N/A')})")

    volatility = valuation.get('volatility', 'N/A')
    lines.append(f"Volatility: {volatility}")

    gv = valuation.get('guideline_value', {})
    if isinstance(gv, dict) and gv.get('min'):
        lines.append(f"Guideline: ₹{gv.get('min', 0):,.0f} – ₹{gv.get('max', 0):,.0f}/sqft")

    date_range = valuation.get('date_range', {})
    if isinstance(date_range, dict):
        lines.append(f"Date range: {date_range.get('from', 'N/A')} to {date_range.get('to', 'N/A')}")

    risks = valuation.get('risks', [])
    if risks:
        lines.append("\nRisk Flags:")
        for r in risks:
            lines.append(f"  {r}")

    return "\n".join(lines)


def format_response(valuation: Dict[str, Any], mode: str = "simplified") -> str:
    """
    Dual-mode response formatter.

    Args:
        valuation: Output from compute_valuation()
        mode: 'simplified' (default for retail users) or 'institutional'

    Returns:
        Formatted string response
    """
    if mode == "institutional":
        return format_institutional(valuation)
    return simplify_valuation_for_user(valuation)
