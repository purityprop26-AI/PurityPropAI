"""
SUPABASE-NATIVE REAL ESTATE INTELLIGENCE SYSTEM
Phase 5: Zero-Hallucination Enforcement Layer

This module ensures the LLM NEVER fabricates financial data.
All numeric claims in LLM output are cross-referenced against
deterministic tool outputs. Any mismatch triggers automatic
correction or rejection.
"""
from __future__ import annotations
import re
import json
import uuid
import time
import structlog
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


# ============================================
# SYSTEM PROMPTS — TOOL-FORCING CONSTRAINTS
# ============================================

SYSTEM_PROMPT_BASE = """You are PurityProp AI, a real estate intelligence assistant for Chennai, India.

ABSOLUTE RULES — VIOLATION IS UNACCEPTABLE:
1. NEVER fabricate, estimate, or hallucinate any numeric value (prices, CAGR, rates, scores, forecasts).
2. ALL numeric data MUST come from tool outputs or the retrieved database records. You may ONLY cite numbers that appear in tool_outputs or retrieved_data.
3. If data is unavailable, say "Data not available" — do NOT guess or approximate.
4. When presenting financial metrics, ALWAYS cite the source tool (e.g., "According to CAGR analysis...").
5. NEVER extrapolate beyond what the tools return. If forecast covers 6 months, do NOT predict month 7.
6. For spatial claims, ONLY use distances returned by PostGIS queries, not your own estimates.
7. ALWAYS include confidence scores when presenting forecasts.
8. If asked about areas/localities not in the database, state clearly: "I don't have data for this area."

RESPONSE FORMAT:
- Present data clearly with proper formatting
- Cite the computation source for every number
- Include disclaimers for forecasts and risk assessments
- Use INR (₹) for all prices
"""

SYSTEM_PROMPT_FINANCIAL = SYSTEM_PROMPT_BASE + """
ADDITIONAL FINANCIAL RULES:
- CAGR must come from the cagr_microservice tool
- Liquidity scores must come from the liquidity_microservice tool
- Absorption rates must come from the absorption_microservice tool
- Distance premiums must come from the distance_decay_microservice tool
- All forecasts must come from the forecast_microservice tool
- Risk assessments must come from the risk_microservice tool
- You MUST NOT perform any arithmetic yourself — use the tools
"""

SYSTEM_PROMPT_SEARCH = SYSTEM_PROMPT_BASE + """
ADDITIONAL SEARCH RULES:
- Property details MUST match the database records exactly
- Do NOT round prices differently than shown in results
- Do NOT add amenities or features not present in the data
- Location descriptions must match the database, not your training data
- If fewer results than expected, say so — do NOT pad with fabricated listings
"""


# ============================================
# NUMERIC EXTRACTION
# ============================================

# Patterns for extracting numeric claims from LLM output
NUMERIC_PATTERNS = [
    # Price patterns: ₹1,23,456 or Rs. 1,23,456 or INR 50,00,000
    (r'[₹][\s]*([\d,]+(?:\.\d+)?)', 'price'),
    (r'(?:Rs\.?|INR)\s*([\d,]+(?:\.\d+)?)', 'price'),
    # Crore/Lakh patterns
    (r'([\d.]+)\s*(?:crore|cr)', 'price_crore'),
    (r'([\d.]+)\s*(?:lakh|lac|L)', 'price_lakh'),
    # Percentage patterns
    (r'([\d.]+)\s*%', 'percentage'),
    # CAGR specific
    (r'CAGR[:\s]+of?\s*([\d.]+)\s*%', 'cagr'),
    # Sqft price
    (r'([\d,]+(?:\.\d+)?)\s*(?:per\s*sq\s*ft|/sq\s*ft|psf)', 'price_per_sqft'),
    # Distance
    (r'([\d.]+)\s*(?:km|kilometer)', 'distance_km'),
    (r'([\d.]+)\s*(?:m|meter)(?!\w)', 'distance_m'),
    # Score/Rating
    (r'(?:score|rating)[:\s]+([\d.]+)', 'score'),
    # BHK
    (r'(\d+)\s*BHK', 'bhk'),
    # Area
    (r'([\d,]+(?:\.\d+)?)\s*sq\s*ft', 'area_sqft'),
]


def extract_numeric_claims(text: str) -> List[Dict[str, Any]]:
    """Extract all numeric claims from LLM narrative output."""
    claims = []
    for pattern, claim_type in NUMERIC_PATTERNS:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            raw_value = match.group(1).replace(',', '')
            try:
                value = float(raw_value)
                claims.append({
                    "type": claim_type,
                    "value": value,
                    "raw": match.group(0),
                    "position": match.start(),
                })
            except ValueError:
                pass
    return claims


# ============================================
# TOOL OUTPUT REGISTRY
# ============================================

def extract_tool_values(tool_outputs: Dict[str, Any]) -> Dict[str, List[float]]:
    """Extract all numeric values from tool outputs for cross-referencing."""
    values: Dict[str, List[float]] = {}

    def _extract_recursive(obj: Any, prefix: str = ""):
        if isinstance(obj, (int, float)):
            key = prefix or "value"
            if key not in values:
                values[key] = []
            values[key].append(float(obj))
        elif isinstance(obj, dict):
            for k, v in obj.items():
                _extract_recursive(v, f"{prefix}.{k}" if prefix else k)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                _extract_recursive(v, f"{prefix}[{i}]")

    _extract_recursive(tool_outputs)
    return values


def flatten_tool_values(tool_outputs: Dict[str, Any]) -> set:
    """Get a flat set of all numeric values from tool outputs."""
    all_values = set()
    extracted = extract_tool_values(tool_outputs)
    for vals in extracted.values():
        for v in vals:
            all_values.add(v)
            # Also add common transformations
            if v != 0:
                all_values.add(round(v, 2))
                all_values.add(round(v, 4))
                all_values.add(round(v * 100, 2))  # percentage conversion
                all_values.add(round(v * 100, 4))
                all_values.add(round(v / 100000, 2))  # lakh conversion
                all_values.add(round(v / 10000000, 2))  # crore conversion
    return all_values


# ============================================
# HALLUCINATION JUDGE
# ============================================

class HallucinationVerdict(BaseModel):
    """Result of hallucination verification."""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    mismatch_detected: bool = False
    total_claims: int = 0
    verified_claims: int = 0
    unverified_claims: int = 0
    mismatches: List[Dict[str, Any]] = []
    verdict: str = "clean"  # clean, warning, hallucination
    action_taken: str = "none"  # none, flagged, corrected, rejected
    confidence: float = 1.0
    details: str = ""
    checked_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class HallucinationJudge:
    """
    Cross-references LLM narrative output against tool outputs.
    Detects fabricated numbers, unsupported claims, and data mismatches.
    """

    # Tolerance for floating point comparison
    TOLERANCE_ABSOLUTE = 0.01
    TOLERANCE_RELATIVE = 0.05  # 5%

    # Claims that are generally safe (don't need strict source verification)
    SAFE_CLAIM_TYPES = {"bhk"}

    def __init__(self):
        self._verification_count = 0
        self._mismatch_count = 0

    def _values_match(self, claimed: float, reference: float) -> bool:
        """Check if two values match within tolerance."""
        if reference == 0:
            return abs(claimed) < self.TOLERANCE_ABSOLUTE

        # Absolute tolerance
        if abs(claimed - reference) < self.TOLERANCE_ABSOLUTE:
            return True

        # Relative tolerance
        if abs(claimed - reference) / abs(reference) < self.TOLERANCE_RELATIVE:
            return True

        return False

    def _find_matching_source(
        self, claim_value: float, tool_values: set
    ) -> Optional[float]:
        """Find a matching value in tool outputs."""
        for ref_val in tool_values:
            if self._values_match(claim_value, ref_val):
                return ref_val
        return None

    def verify(
        self,
        narrative: str,
        tool_outputs: Dict[str, Any],
        retrieved_data: Optional[List[Dict[str, Any]]] = None,
    ) -> HallucinationVerdict:
        """
        Verify LLM narrative against tool outputs and retrieved data.

        Args:
            narrative: The LLM's text output
            tool_outputs: Dict of all tool results used in this response
            retrieved_data: Optional list of database records retrieved

        Returns:
            HallucinationVerdict with mismatch details
        """
        self._verification_count += 1
        start = time.perf_counter()

        verdict = HallucinationVerdict()

        # Extract claims from narrative
        claims = extract_numeric_claims(narrative)
        verdict.total_claims = len(claims)

        if not claims:
            verdict.verdict = "clean"
            verdict.details = "No numeric claims to verify"
            return verdict

        # Build reference value set
        all_reference_values = flatten_tool_values(tool_outputs)

        # Also extract values from retrieved database records
        if retrieved_data:
            for record in retrieved_data:
                db_values = flatten_tool_values(record)
                all_reference_values.update(db_values)

        # Check each claim
        for claim in claims:
            if claim["type"] in self.SAFE_CLAIM_TYPES:
                verdict.verified_claims += 1
                continue

            match = self._find_matching_source(
                claim["value"], all_reference_values
            )

            if match is not None:
                verdict.verified_claims += 1
            else:
                verdict.unverified_claims += 1
                verdict.mismatches.append({
                    "claimed_value": claim["value"],
                    "claim_type": claim["type"],
                    "raw_text": claim["raw"],
                    "position": claim["position"],
                    "closest_reference": self._find_closest(
                        claim["value"], all_reference_values
                    ),
                })

        # Determine verdict
        if verdict.unverified_claims == 0:
            verdict.verdict = "clean"
            verdict.mismatch_detected = False
            verdict.confidence = 1.0
        elif verdict.unverified_claims <= 1 and verdict.total_claims > 3:
            verdict.verdict = "warning"
            verdict.mismatch_detected = True
            verdict.action_taken = "flagged"
            verdict.confidence = 1.0 - (verdict.unverified_claims / verdict.total_claims)
        else:
            verdict.verdict = "hallucination"
            verdict.mismatch_detected = True
            verdict.action_taken = "rejected"
            verdict.confidence = max(0, 1.0 - (verdict.unverified_claims / max(verdict.total_claims, 1)))

        if verdict.mismatch_detected:
            self._mismatch_count += 1

        elapsed_ms = (time.perf_counter() - start) * 1000
        verdict.details = (
            f"Verified {verdict.verified_claims}/{verdict.total_claims} claims "
            f"in {elapsed_ms:.2f}ms. "
            f"{'All claims sourced.' if not verdict.mismatches else f'{len(verdict.mismatches)} unverified claims.'}"
        )

        logger.info(
            "hallucination_check",
            request_id=verdict.request_id,
            total_claims=verdict.total_claims,
            verified=verdict.verified_claims,
            unverified=verdict.unverified_claims,
            verdict=verdict.verdict,
            elapsed_ms=round(elapsed_ms, 3),
        )

        return verdict

    def _find_closest(self, value: float, reference_set: set) -> Optional[Dict]:
        """Find the closest reference value to a claimed value."""
        if not reference_set:
            return None

        closest = min(reference_set, key=lambda x: abs(x - value))
        diff_pct = abs(value - closest) / max(abs(closest), 0.01) * 100

        return {
            "value": closest,
            "difference_percent": round(diff_pct, 2),
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Return judge metrics."""
        return {
            "total_verifications": self._verification_count,
            "total_mismatches": self._mismatch_count,
            "mismatch_rate": (
                self._mismatch_count / self._verification_count
                if self._verification_count > 0
                else 0.0
            ),
        }


# ============================================
# RESPONSE SANITIZER
# ============================================

class ResponseSanitizer:
    """
    Sanitizes LLM responses by removing or flagging unverified claims.
    Used when the judge detects hallucinations.
    """

    DISCLAIMER = (
        "\n\n⚠️ *Some data points in this response could not be verified "
        "against our database. Please verify independently.*"
    )

    REJECTION_MESSAGE = (
        "I apologize, but I cannot provide a reliable response for this query. "
        "Some of the data I generated could not be verified against our records. "
        "Please try rephrasing your query or asking about a specific aspect."
    )

    @staticmethod
    def sanitize(
        narrative: str,
        verdict: HallucinationVerdict,
    ) -> str:
        """Sanitize the narrative based on the verdict."""
        if verdict.verdict == "clean":
            return narrative

        if verdict.verdict == "hallucination":
            # Full rejection — too many unverified claims
            return ResponseSanitizer.REJECTION_MESSAGE

        if verdict.verdict == "warning":
            # Flag but allow through with disclaimer
            flagged = narrative
            for mismatch in verdict.mismatches:
                raw = mismatch.get("raw_text", "")
                if raw:
                    flagged = flagged.replace(
                        raw, f"**[unverified]** {raw}"
                    )
            return flagged + ResponseSanitizer.DISCLAIMER

        return narrative


# ============================================
# TOOL DEFINITIONS FOR GROQ FUNCTION CALLING
# ============================================

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "compute_cagr",
            "description": "Compute Compound Annual Growth Rate. USE THIS for any CAGR calculation — do NOT compute yourself.",
            "parameters": {
                "type": "object",
                "properties": {
                    "beginning_value": {"type": "number", "description": "Starting price/value"},
                    "ending_value": {"type": "number", "description": "Ending price/value"},
                    "years": {"type": "number", "description": "Number of years"},
                },
                "required": ["beginning_value", "ending_value", "years"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compute_liquidity",
            "description": "Compute market liquidity score (0-1). USE THIS for any liquidity assessment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "total_listings": {"type": "integer", "description": "Total active listings"},
                    "total_sold": {"type": "integer", "description": "Total sold in period"},
                    "avg_days_on_market": {"type": "number", "description": "Average days on market"},
                    "price_volatility": {"type": "number", "description": "Price volatility 0-1"},
                },
                "required": ["total_listings", "total_sold", "avg_days_on_market", "price_volatility"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compute_absorption",
            "description": "Compute absorption rate and months of supply. USE THIS for supply/demand analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "total_sold": {"type": "integer"},
                    "period_months": {"type": "number"},
                    "active_inventory": {"type": "integer"},
                },
                "required": ["total_sold", "period_months", "active_inventory"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compute_distance_decay",
            "description": "Compute location premium based on distance to landmarks. USE THIS for price adjustments.",
            "parameters": {
                "type": "object",
                "properties": {
                    "base_price_per_sqft": {"type": "number"},
                    "distances_km": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "distance_km": {"type": "number"},
                                "weight": {"type": "number"},
                            },
                        },
                    },
                },
                "required": ["base_price_per_sqft", "distances_km"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compute_forecast",
            "description": "Compute price forecast using ensemble methods. USE THIS for any predictions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "historical_prices": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Historical price data points",
                    },
                    "periods": {"type": "integer", "description": "Number of periods to forecast"},
                },
                "required": ["historical_prices"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compute_risk",
            "description": "Synthesize risk assessment from multiple indicators. USE THIS for risk analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cagr": {"type": "number"},
                    "liquidity_score": {"type": "number"},
                    "absorption_rate": {"type": "number"},
                    "price_volatility": {"type": "number"},
                },
            },
        },
    },
]


# ============================================
# SINGLETON
# ============================================

_judge: Optional[HallucinationJudge] = None


def get_hallucination_judge() -> HallucinationJudge:
    """Get singleton hallucination judge."""
    global _judge
    if _judge is None:
        _judge = HallucinationJudge()
    return _judge
