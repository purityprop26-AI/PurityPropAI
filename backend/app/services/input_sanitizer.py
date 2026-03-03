"""
PurityProp — Input Sanitizer (Hallucination Guard Layer)
=========================================================

Strips user-injected price values, absurd claims, and prompt injection
attempts BEFORE they reach the RAG pipeline or LLM.

Rules:
  1. Strip any user-stated prices from the query
  2. Detect and reject absurd numeric claims
  3. Normalize query for downstream processing
  4. Block prompt injection patterns
"""

from __future__ import annotations

import re
import structlog
from typing import Tuple

logger = structlog.get_logger(__name__)

# ── Price patterns to strip ───────────────────────────────────────────
PRICE_PATTERNS = [
    r'(?:rs\.?|₹|inr)\s*[\d,]+(?:\.\d+)?\s*(?:per\s*(?:sqft|sq\.?ft|square\s*feet?|ground|cent|acre))?',
    r'[\d,]+\s*(?:lakh|lakhs|lac|crore|crores|cr)\s*(?:per\s*(?:sqft|sq\.?ft|ground))?',
    r'(?:price|rate|value|cost)\s+(?:is|was|should\s+be|must\s+be)\s+(?:rs\.?|₹|inr)?\s*[\d,]+',
    r'\b\d{4,}\s*(?:/|-|per)\s*(?:sqft|sq\.?ft|square|ground)',
]

# ── Prompt injection patterns ─────────────────────────────────────────
INJECTION_PATTERNS = [
    r'ignore\s+(?:previous|above|all)\s+instructions?',
    r'you\s+are\s+now\s+a',
    r'forget\s+(?:everything|all|your)',
    r'system\s*:\s*',
    r'<\s*(?:script|system|admin)',
    r'override\s+(?:rules|instructions|system)',
    r'pretend\s+(?:you\s+are|to\s+be)',
]

# ── Absurd price thresholds (TN market, per sqft) ─────────────────────
TN_PRICE_BOUNDS = {
    "land": {"min": 50, "max": 200000},        # Rs.50 - 2L/sqft
    "apartment": {"min": 1000, "max": 50000},   # Rs.1K - 50K/sqft
    "villa": {"min": 2000, "max": 100000},      # Rs.2K - 1L/sqft
    "commercial": {"min": 500, "max": 300000},  # Rs.500 - 3L/sqft
}


def sanitize_query(query: str) -> Tuple[str, list]:
    """
    Sanitize user query before RAG processing.

    Returns:
        (sanitized_query, warnings_list)
    """
    warnings = []
    sanitized = query

    # 1. Block prompt injection
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, query, re.IGNORECASE):
            logger.warning("prompt_injection_blocked", query=query[:50])
            warnings.append("Prompt injection attempt detected and blocked")
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)

    # 2. Strip user-stated prices (they must not influence valuation)
    for pattern in PRICE_PATTERNS:
        matches = re.findall(pattern, sanitized, re.IGNORECASE)
        if matches:
            logger.info("user_price_stripped", matches=matches[:3])
            warnings.append(f"User-stated price removed: {matches[0]}")
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)

    # 3. Clean up double spaces
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()

    # 4. Length guard
    if len(sanitized) > 500:
        sanitized = sanitized[:500]
        warnings.append("Query truncated to 500 chars")

    return sanitized, warnings


def validate_price_output(
    price: float, asset_type: str = "land"
) -> Tuple[bool, str]:
    """
    Validate that a computed price is within reasonable TN market bounds.
    Used as a post-computation sanity check.

    Returns:
        (is_valid, message)
    """
    bounds = TN_PRICE_BOUNDS.get(asset_type, TN_PRICE_BOUNDS["land"])

    if price <= 0:
        return False, "Price is zero or negative"

    if price < bounds["min"]:
        return False, f"Price Rs.{price:,.0f}/sqft below TN minimum (Rs.{bounds['min']})"

    if price > bounds["max"]:
        return False, f"Price Rs.{price:,.0f}/sqft exceeds TN maximum (Rs.{bounds['max']:,})"

    return True, "Price within valid range"


def extract_user_claimed_price(query: str) -> float:
    """
    Extract any price value the user claims in their query.
    Used to compare against DB-backed valuation — if they differ wildly,
    we flag it as potential misinformation.

    Returns: extracted price per sqft, or 0 if none found.
    """
    # Look for "X per sqft" or "Rs.X"
    patterns = [
        r'(?:rs\.?|₹)\s*([\d,]+)',
        r'([\d,]+)\s*(?:/|-|per)\s*(?:sqft|sq\.?ft)',
        r'([\d,]+)\s*(?:lakh|lakhs)\s*per\s*(?:ground)',
    ]
    for p in patterns:
        m = re.search(p, query, re.IGNORECASE)
        if m:
            try:
                val = float(m.group(1).replace(',', ''))
                # Convert lakh/ground to per sqft
                if 'lakh' in query.lower() and 'ground' in query.lower():
                    val = (val * 100000) / 2400
                return val
            except (ValueError, IndexError):
                pass
    return 0
