"""
PurityProp — Reranker Module
==============================

Lightweight score-based cross-reranker for Hybrid RAG retrieval.

Strategy: After vector+scalar retrieval, rerank results using a
multi-signal scoring function that combines:
  1. Vector similarity (from embedding distance)
  2. Recency boost (newer transactions ranked higher)
  3. Price consistency (penalize outlier-like prices)
  4. Exact locality match bonus

No external ML model needed — deterministic scoring.
"""

from __future__ import annotations

import structlog
from typing import Any, Dict, List
from datetime import date

logger = structlog.get_logger(__name__)

# ── Weights for reranking signals ─────────────────────────────────────
WEIGHTS = {
    "similarity": 0.35,   # Vector cosine similarity
    "recency": 0.25,      # Recent transactions score higher
    "price_consistency": 0.20,  # Prices near median score higher
    "locality_match": 0.20,     # Exact locality match bonus
}


def _recency_score(registration_date: str, max_age_months: int = 48) -> float:
    """Score from 0.0 (old) to 1.0 (today) based on registration date."""
    try:
        reg = date.fromisoformat(str(registration_date))
        age_days = (date.today() - reg).days
        age_months = max(0, age_days / 30.0)
        return max(0.0, 1.0 - (age_months / max_age_months))
    except (ValueError, TypeError):
        return 0.5  # Unknown date → neutral


def _price_consistency_score(
    price: float, median: float, iqr_range: float
) -> float:
    """
    Score 0.0–1.0 based on how close the price is to the median.
    Prices within 1 IQR score highly; beyond 2 IQR score low.
    """
    if median <= 0 or iqr_range <= 0:
        return 0.5

    deviation = abs(price - median) / iqr_range
    return max(0.0, 1.0 - (deviation * 0.5))


def _locality_match_score(
    result_locality: str, query_locality: str
) -> float:
    """
    1.0 for exact match, 0.7 for substring match, 0.3 otherwise.
    """
    rl = result_locality.lower().strip()
    ql = query_locality.lower().strip()

    if rl == ql:
        return 1.0
    if ql in rl or rl in ql:
        return 0.7
    return 0.3


def rerank(
    results: List[Dict[str, Any]],
    query_locality: str,
    median_price: float = 0,
    iqr_range: float = 0,
) -> List[Dict[str, Any]]:
    """
    Rerank retrieval results using multi-signal scoring.

    Args:
        results: List of transaction dicts from hybrid_search()
        query_locality: The locality the user queried
        median_price: Median price from valuation stats (for consistency)
        iqr_range: IQR from stats (Q3-Q1)

    Returns:
        Reranked list with 'rerank_score' added to each result.
    """
    if not results:
        return results

    if len(results) <= 1:
        for r in results:
            r["rerank_score"] = 1.0
        return results

    # Compute individual scores
    for r in results:
        # 1. Similarity (already from vector search, 0-1)
        sim = r.get("similarity", 0.5)

        # 2. Recency
        rec = _recency_score(r.get("registration_date", ""))

        # 3. Price consistency
        price = r.get("price_per_sqft", 0)
        pc = _price_consistency_score(
            price,
            median_price if median_price > 0 else price,
            iqr_range if iqr_range > 0 else max(price * 0.3, 1),
        )

        # 4. Locality match
        lm = _locality_match_score(
            r.get("locality", ""), query_locality
        )

        # Weighted composite
        score = (
            sim * WEIGHTS["similarity"]
            + rec * WEIGHTS["recency"]
            + pc * WEIGHTS["price_consistency"]
            + lm * WEIGHTS["locality_match"]
        )
        r["rerank_score"] = round(score, 4)
        r["rerank_breakdown"] = {
            "similarity": round(sim, 3),
            "recency": round(rec, 3),
            "price_consistency": round(pc, 3),
            "locality_match": round(lm, 3),
        }

    # Sort by rerank score descending
    results.sort(key=lambda x: x["rerank_score"], reverse=True)

    logger.info(
        "reranker_executed",
        total=len(results),
        top_score=results[0]["rerank_score"] if results else 0,
        locality=query_locality,
    )

    return results
