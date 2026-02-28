"""
HallucinationGuard — Production-Connected Adapter

FIX [CRIT-G1]: This is the missing bridge between the intelligence /query endpoint
and the existing HallucinationJudge in hallucination_guard.py.

Previously, HallucinationJudge existed but was NEVER called from any production route.
This adapter provides the verify() interface used by api/routes.py, converting
the simple source_data list (list of property dicts) into the format that
HallucinationJudge.verify() expects (tool_outputs dict, retrieved_data list).

Design:
  - Property price data becomes "tool_outputs" (the authoritative ground-truth)
  - Returned summary text is checked for fabricated numbers
  - Verdict determines whether summary is passed through, flagged, or replaced
"""

from typing import Any, Dict, List, Optional, Tuple
from app.core.hallucination_guard import HallucinationJudge, ResponseSanitizer


class HallucinationGuard:
    """
    Production-facing adapter over HallucinationJudge.

    Used by: app/api/routes.py — /query endpoint AI summary path.

    FIX [CRIT-G1]: verify() is now called on every AI summary before it is
                   returned to the client. This activates the hallucination
                   enforcement that was implemented but never connected.
    """

    def __init__(self):
        self._judge = HallucinationJudge()

    def verify(
        self,
        ai_response: str,
        source_data: List[Dict[str, Any]],
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Verify AI summary text against retrieved property data.

        Args:
            ai_response: The raw LLM-generated summary text.
            source_data:  List of property dicts from the database query.
                          These are the ground-truth values the LLM must not contradict.

        Returns:
            Tuple of:
              - (str)  Verified or sanitized summary text
              - (dict) Verification result metadata:
                  passed: bool
                  verdict: "clean" | "warning" | "hallucination"
                  flagged_count: int
                  total_claims: int
        """
        if not ai_response or not ai_response.strip():
            return ai_response, {"passed": True, "verdict": "clean", "flagged_count": 0, "total_claims": 0}

        # Convert property list into tool_outputs format expected by HallucinationJudge
        # Numeric fields from DB records become the authoritative reference set
        tool_outputs: Dict[str, Any] = {
            "retrieved_properties": source_data,
            "price_values": [p.get("price", 0) for p in source_data if p.get("price")],
            "price_per_sqft_values": [p.get("price_per_sqft") for p in source_data if p.get("price_per_sqft")],
            "area_values": [p.get("carpet_area_sqft") for p in source_data if p.get("carpet_area_sqft")],
        }

        # Run the actual hallucination verification
        verdict = self._judge.verify(
            narrative=ai_response,
            tool_outputs=tool_outputs,
            retrieved_data=source_data,
        )

        # Determine pass/fail
        passed = verdict.verdict in ("clean", "warning")

        # If hallucination detected, sanitize the response
        if verdict.verdict == "hallucination":
            sanitized = ResponseSanitizer.sanitize(ai_response, verdict)
            return sanitized, {
                "passed": False,
                "verdict": verdict.verdict,
                "flagged_count": verdict.unverified_claims,
                "total_claims": verdict.total_claims,
                "action": verdict.action_taken,
            }

        # For warnings: return original but tag metadata
        return ai_response, {
            "passed": passed,
            "verdict": verdict.verdict,
            "flagged_count": verdict.unverified_claims,
            "total_claims": verdict.total_claims,
            "action": verdict.action_taken,
        }
