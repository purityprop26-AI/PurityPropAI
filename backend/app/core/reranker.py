"""
Cross-Encoder Re-Ranker — Pure Python, Zero ML Dependencies

Implements a bi-level re-ranking pipeline:
  Stage 1: Reciprocal Rank Fusion (RRF) — merges vector rank + keyword rank
  Stage 2: Feature-based cross-scoring — semantic overlap, structural signals

Why not a neural cross-encoder?
  • sentence-transformers cross-encoder needs PyTorch (2 GB+ container bloat)
  • Free Supabase tier — no GPU available
  • For property search (structured data), feature signals outperform neural
    re-rankers when fields are explicit (price, locality, bedrooms)
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Tuple

import structlog

logger = structlog.get_logger(__name__)

# ── Reciprocal Rank Fusion constant k (standard: 60) ──────────────────
_RRF_K = 60


def reciprocal_rank_fusion(
    vector_hits: List[str],     # Ordered property IDs from vector search
    keyword_hits: List[str],    # Ordered property IDs from keyword/SQL search
    spatial_hits: List[str],    # Ordered property IDs from spatial search
) -> List[Tuple[str, float]]:
    """
    Merge three ranked lists using Reciprocal Rank Fusion.
    Returns: [(property_id, rrf_score)] sorted descending.

    RRF formula: score = Σ  1 / (k + rank_i)
    """
    scores: Dict[str, float] = {}

    for rank_list, weight in [
        (vector_hits, 1.0),
        (keyword_hits, 0.8),
        (spatial_hits, 0.6),
    ]:
        for rank, pid in enumerate(rank_list, start=1):
            scores[pid] = scores.get(pid, 0.0) + weight * (1.0 / (_RRF_K + rank))

    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def cross_score(
    query: str,
    properties: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Feature-based cross-encoder re-ranking.

    Signals computed per property × query pair:
      • Token overlap ratio   — shared words between query and title/locality
      • Price signal         — budget keyword matching (lakhs / CR)
      • BHK signal           — bedroom keyword matching
      • Locality signal      — exact locality name in query
      • Verified bonus        — is_verified properties get a boost
      • Featured bonus        — is_featured properties get a boost

    Returns properties list sorted by final cross_score DESC.
    """
    query_lower = query.lower()
    query_tokens = set(re.findall(r'\b\w+\b', query_lower))

    # Extract price budget from query (e.g. "60 lakhs", "2Cr", "1.5 crore")
    budget_in_rupees: Optional[float] = None
    lakh_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|l\b)', query_lower)
    cr_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:cr|crore|crores)', query_lower)
    if lakh_match:
        budget_in_rupees = float(lakh_match.group(1)) * 100_000
    elif cr_match:
        budget_in_rupees = float(cr_match.group(1)) * 10_000_000

    # Extract BHK from query
    bhk_match = re.search(r'(\d)\s*(?:bhk|bedroom|bed)', query_lower)
    target_bhk = int(bhk_match.group(1)) if bhk_match else None

    scored = []
    for prop in properties:
        score = prop.get("combined_score") or 0.0     # Base DB score

        title = (prop.get("title") or "").lower()
        locality = (prop.get("locality") or "").lower()
        prop_tokens = set(re.findall(r'\b\w+\b', f"{title} {locality}"))

        # ── Signal 1: Token overlap ─────────────────────────────────────
        if query_tokens and prop_tokens:
            overlap = len(query_tokens & prop_tokens) / (len(query_tokens) + 1)
            score += overlap * 0.4

        # ── Signal 2: Budget proximity ──────────────────────────────────
        if budget_in_rupees and prop.get("price"):
            price = float(prop["price"])
            if price <= budget_in_rupees:
                # Within budget → full bonus; tighter fit → larger bonus
                ratio = price / budget_in_rupees
                score += 0.3 * ratio
            else:
                # Over budget → small penalty
                over_pct = (price - budget_in_rupees) / budget_in_rupees
                score -= min(0.2, over_pct * 0.5)

        # ── Signal 3: BHK match ─────────────────────────────────────────
        if target_bhk and prop.get("bedrooms") is not None:
            if prop["bedrooms"] == target_bhk:
                score += 0.25
            elif abs(prop["bedrooms"] - target_bhk) == 1:
                score += 0.1  # 1 off — partial credit

        # ── Signal 4: Locality exact match ──────────────────────────────
        if locality and locality in query_lower:
            score += 0.35

        # ── Signal 5: Trust signals ─────────────────────────────────────
        if prop.get("is_verified"):
            score += 0.10
        if prop.get("is_featured"):
            score += 0.05

        scored.append({**prop, "cross_score": round(score, 6)})

    result = sorted(scored, key=lambda x: x["cross_score"], reverse=True)

    logger.info(
        "reranker_complete",
        query_prefix=query[:40],
        candidates=len(result),
        top_score=result[0]["cross_score"] if result else 0.0,
    )
    return result


def extract_top_k_context(
    properties: List[Dict[str, Any]],
    k: int = 5,
) -> List[Dict[str, Any]]:
    """
    Extract top-k properties as lean context dicts for LLM injection.
    Only includes fields provably grounded in source data.

    Fields excluded: images, amenities, price_history (TOAST / heavy)
    """
    context = []
    for p in properties[:k]:
        ctx: Dict[str, Any] = {
            "property_id": str(p.get("id", "")),
            "title": p.get("title"),
            "locality": p.get("locality"),
            "city": p.get("city"),
            "price": p.get("price"),
            "price_per_sqft": p.get("price_per_sqft"),
            "bedrooms": p.get("bedrooms"),
            "bathrooms": p.get("bathrooms"),
            "carpet_area_sqft": p.get("carpet_area_sqft"),
            "property_type": p.get("property_type"),
            "listing_type": p.get("listing_type"),
            "status": p.get("status"),
            "builder_name": p.get("builder_name"),
            "project_name": p.get("project_name"),
            "rera_id": p.get("rera_id"),
            "is_verified": p.get("is_verified", False),
            "cross_score": p.get("cross_score"),
        }
        # Strip None values to keep context lean
        context.append({k2: v for k2, v in ctx.items() if v is not None})
    return context
