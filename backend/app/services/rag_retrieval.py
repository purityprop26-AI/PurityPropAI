"""
PurityProp — Database-Backed RAG Retrieval Service
====================================================

Replaces hardcoded dict lookups with real PostgreSQL queries.
Uses: pgvector (HNSW), PostGIS (ST_DWithin), scalar filters.

This is the TRUE retrieval layer.
"""

from __future__ import annotations

import structlog
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_context
from app.core.embedding_service import embed_query
from app.services.reranker import rerank

logger = structlog.get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────
# 1. GUIDELINE VALUE RETRIEVAL (replaces TN_GUIDELINE_VALUES_2024 dict)
# ─────────────────────────────────────────────────────────────────────

async def get_guideline_from_db(
    locality: str,
    asset_type: str = "land",
    session: Optional[AsyncSession] = None,
) -> Optional[Dict[str, Any]]:
    """
    Fetch guideline value from database.
    Falls back to fuzzy match if exact match not found.
    """
    query = text("""
        SELECT  district, locality, asset_type,
                min_per_sqft, max_per_sqft,
                effective_date, source_url
        FROM guideline_values
        WHERE locality ILIKE :locality
          AND asset_type = :asset_type
        ORDER BY effective_date DESC
        LIMIT 1
    """)

    async def _execute(s: AsyncSession):
        result = await s.execute(query, {"locality": f"%{locality}%", "asset_type": asset_type})
        row = result.fetchone()
        if row:
            return {
                "district": row[0], "locality": row[1], "asset_type": row[2],
                "min_per_sqft": float(row[3]), "max_per_sqft": float(row[4]),
                "effective_date": str(row[5]), "source_url": row[6],
            }

        # Fuzzy fallback with trigram similarity
        fuzzy = text("""
            SELECT  district, locality, asset_type,
                    min_per_sqft, max_per_sqft,
                    effective_date, source_url,
                    similarity(locality, :locality) AS sim
            FROM guideline_values
            WHERE locality % :locality
              AND asset_type = :asset_type
            ORDER BY sim DESC
            LIMIT 1
        """)
        result = await s.execute(fuzzy, {"locality": locality, "asset_type": asset_type})
        row = result.fetchone()
        if row:
            return {
                "district": row[0], "locality": row[1], "asset_type": row[2],
                "min_per_sqft": float(row[3]), "max_per_sqft": float(row[4]),
                "effective_date": str(row[5]), "source_url": row[6],
                "fuzzy_match": True, "similarity": float(row[7]),
            }
        return None

    if session:
        return await _execute(session)
    else:
        async with get_db_context() as s:
            return await _execute(s)


# ─────────────────────────────────────────────────────────────────────
# 2. TRANSACTION RETRIEVAL (the core RAG query)
# ─────────────────────────────────────────────────────────────────────

async def get_transactions(
    locality: str,
    asset_type: str = "land",
    months: int = 24,
    limit: int = 50,
    session: Optional[AsyncSession] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch registry transactions by locality + asset_type + date window.
    Scalar filter query (no vector — used when embeddings unavailable).
    """
    query = text("""
        SELECT  id, district, locality, micro_market, asset_type,
                area_sqft, sale_value, price_per_sqft,
                registration_date, zone_tier, data_source
        FROM registry_transactions
        WHERE locality ILIKE :locality
          AND asset_type = :asset_type
          AND registration_date >= (CURRENT_DATE - (:months || ' months')::INTERVAL)
          AND is_outlier = FALSE
        ORDER BY registration_date DESC
        LIMIT :limit
    """)

    async def _execute(s: AsyncSession):
        result = await s.execute(query, {
            "locality": f"%{locality}%", "asset_type": asset_type,
            "months": str(months), "limit": limit,
        })
        rows = result.fetchall()
        return [
            {
                "id": str(r[0]), "district": r[1], "locality": r[2],
                "micro_market": r[3], "asset_type": r[4],
                "area_sqft": float(r[5]), "sale_value": float(r[6]),
                "price_per_sqft": float(r[7]) if r[7] else 0,
                "registration_date": str(r[8]), "zone_tier": r[9],
                "data_source": r[10],
            }
            for r in rows
        ]

    if session:
        return await _execute(session)
    else:
        async with get_db_context() as s:
            return await _execute(s)


# ─────────────────────────────────────────────────────────────────────
# 3. HYBRID SEARCH (Vector + Scalar — TRUE RAG)
# ─────────────────────────────────────────────────────────────────────

async def hybrid_search(
    user_query: str,
    locality: str,
    asset_type: str = "land",
    months: int = 24,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    True hybrid retrieval: embed query → vector similarity + scalar filters.
    Falls back to scalar-only if embedding fails.
    """
    # Step 1: Embed user query
    query_vector = await embed_query(user_query)

    async with get_db_context() as session:
        if query_vector:
            # Hybrid: vector + scalar
            vector_str = "[" + ",".join(f"{v:.6f}" for v in query_vector) + "]"
            result = await session.execute(
                text("""
                    SELECT  id, district, locality, micro_market, asset_type,
                            area_sqft, sale_value, price_per_sqft,
                            registration_date, zone_tier, data_source,
                            1 - (embedding <=> CAST(:vec AS vector)) AS similarity
                    FROM registry_transactions
                    WHERE locality ILIKE :locality
                      AND asset_type = :asset_type
                      AND registration_date >= (CURRENT_DATE - CAST(:months || ' months' AS INTERVAL))
                      AND is_outlier = FALSE
                      AND embedding IS NOT NULL
                    ORDER BY embedding <=> CAST(:vec AS vector)
                    LIMIT :limit
                """),
                {
                    "vec": vector_str, "locality": f"%{locality}%",
                    "asset_type": asset_type, "months": str(months), "limit": limit,
                }
            )
            logger.info("hybrid_search_vector", locality=locality, asset_type=asset_type)
        else:
            # Fallback: scalar-only
            result = await session.execute(
                text("""
                    SELECT  id, district, locality, micro_market, asset_type,
                            area_sqft, sale_value, price_per_sqft,
                            registration_date, zone_tier, data_source,
                            0.0 AS similarity
                    FROM registry_transactions
                    WHERE locality ILIKE :locality
                      AND asset_type = :asset_type
                      AND registration_date >= (CURRENT_DATE - CAST(:months || ' months' AS INTERVAL))
                      AND is_outlier = FALSE
                    ORDER BY registration_date DESC
                    LIMIT :limit
                """),
                {
                    "locality": f"%{locality}%", "asset_type": asset_type,
                    "months": str(months), "limit": limit,
                }
            )
            logger.info("hybrid_search_scalar_fallback", locality=locality)

        rows = result.fetchall()
        return [
            {
                "id": str(r[0]), "district": r[1], "locality": r[2],
                "micro_market": r[3], "asset_type": r[4],
                "area_sqft": float(r[5]), "sale_value": float(r[6]),
                "price_per_sqft": float(r[7]) if r[7] else 0,
                "registration_date": str(r[8]), "zone_tier": r[9],
                "data_source": r[10], "similarity": float(r[11]),
            }
            for r in rows
        ]


# ─────────────────────────────────────────────────────────────────────
# 4. LOCALITY METADATA RETRIEVAL (replaces ZONE_TIERS dict)
# ─────────────────────────────────────────────────────────────────────

async def get_locality_metadata(
    locality: str,
    session: Optional[AsyncSession] = None,
) -> Optional[Dict[str, Any]]:
    """Fetch zone tier, features, and infrastructure premiums from DB."""
    query = text("""
        SELECT  locality, district, zone_tier, population_tier,
                features, infra_premium, metro_proximity_km, it_corridor
        FROM locality_metadata
        WHERE locality ILIKE :locality
        LIMIT 1
    """)

    async def _execute(s: AsyncSession):
        result = await s.execute(query, {"locality": f"%{locality}%"})
        row = result.fetchone()
        if row:
            return {
                "locality": row[0], "district": row[1],
                "zone_tier": row[2], "population_tier": row[3],
                "features": row[4] or [], "infra_premium": row[5] or {},
                "metro_proximity_km": float(row[6]) if row[6] else None,
                "it_corridor": row[7],
            }
        return None

    if session:
        return await _execute(session)
    else:
        async with get_db_context() as s:
            return await _execute(s)


# ─────────────────────────────────────────────────────────────────────
# 5. VALUATION STATS (Server-side computation via SQL function)
# ─────────────────────────────────────────────────────────────────────

async def get_valuation_stats(
    locality: str,
    asset_type: str = "land",
    months: int = 48,
) -> Dict[str, Any]:
    """
    Call server-side compute_valuation_stats() function.
    Returns: comparable_count, min, max, median, q1, q3, std_dev, cov, dates.
    """
    async with get_db_context() as session:
        try:
            result = await session.execute(
                text("SELECT * FROM compute_valuation_stats(:loc, :asset, :months)"),
                {"loc": locality, "asset": asset_type, "months": months}
            )
            row = result.fetchone()
        except Exception as e:
            logger.warning("valuation_stats_function_failed", error=str(e), locality=locality)
            # Fallback: inline stats query
            result = await session.execute(
                text("""
                    SELECT COUNT(*)::BIGINT, MIN(price_per_sqft), MAX(price_per_sqft),
                           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price_per_sqft),
                           PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY price_per_sqft),
                           PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY price_per_sqft),
                           STDDEV(price_per_sqft)::DOUBLE PRECISION,
                           CASE WHEN AVG(price_per_sqft) > 0
                                THEN (STDDEV(price_per_sqft) / AVG(price_per_sqft))::DOUBLE PRECISION
                                ELSE 0::DOUBLE PRECISION END,
                           MIN(registration_date), MAX(registration_date)
                    FROM registry_transactions
                    WHERE locality ILIKE :loc
                      AND asset_type = :asset
                      AND registration_date >= (CURRENT_DATE - (:months || ' months')::INTERVAL)
                      AND is_outlier = FALSE
                """),
                {"loc": f"%{locality}%", "asset": asset_type, "months": str(months)}
            )
            row = result.fetchone()

        if row and row[0] and row[0] > 0:
            return {
                "comparable_count": int(row[0]),
                "min_price": float(row[1]) if row[1] else 0,
                "max_price": float(row[2]) if row[2] else 0,
                "median_price": float(row[3]) if row[3] else 0,
                "q1_price": float(row[4]) if row[4] else 0,
                "q3_price": float(row[5]) if row[5] else 0,
                "std_dev": float(row[6]) if row[6] else 0,
                "cov": float(row[7]) if row[7] else 0,
                "earliest_date": str(row[8]) if row[8] else None,
                "latest_date": str(row[9]) if row[9] else None,
                "source": "registry_transactions",
            }
        return {
            "comparable_count": 0,
            "source": "no_data",
        }


# ─────────────────────────────────────────────────────────────────────
# 6. FULL RAG RETRIEVAL PIPELINE (Orchestrator)
# ─────────────────────────────────────────────────────────────────────

async def rag_retrieve(
    user_query: str,
    locality: str,
    asset_type: str = "land",
) -> Dict[str, Any]:
    """
    Full RAG retrieval pipeline:
      1. Get valuation stats from registry_transactions
      2. Get guideline value from guideline_values
      3. Get locality metadata (zone, features, premiums)
      4. If stats.comparable_count == 0 → fallback to guideline only
      5. Return structured result for confidence engine + LLM

    Returns dict with all data needed for deterministic valuation.
    """
    import asyncio

    # Parallel async calls
    stats_task = asyncio.create_task(get_valuation_stats(locality, asset_type))
    guideline_task = asyncio.create_task(get_guideline_from_db(locality, asset_type))
    metadata_task = asyncio.create_task(get_locality_metadata(locality))
    search_task = asyncio.create_task(hybrid_search(user_query, locality, asset_type))

    stats, guideline, metadata, search_results = await asyncio.gather(
        stats_task, guideline_task, metadata_task, search_task
    )

    # ── RERANK search results ────────────────────────────────────────
    if search_results:
        median_for_rerank = stats.get('median_price', 0) if stats.get('comparable_count', 0) > 0 else 0
        iqr_for_rerank = (stats.get('q3_price', 0) - stats.get('q1_price', 0)) if stats.get('comparable_count', 0) > 0 else 0
        search_results = rerank(
            search_results, locality,
            median_price=median_for_rerank,
            iqr_range=max(iqr_for_rerank, 1),
        )

    has_registry_data = stats.get("comparable_count", 0) > 0
    has_guideline_data = guideline is not None

    # Determine pricing source
    if has_registry_data:
        # Use actual transaction data (authoritative)
        price_min = stats["min_price"]
        price_max = stats["max_price"]
        price_median = stats["median_price"]
        comparable_count = stats["comparable_count"]
        data_source = "registry_transactions"
    elif has_guideline_data:
        # Fallback to guideline values
        price_min = guideline["min_per_sqft"]
        price_max = guideline["max_per_sqft"]
        price_median = (price_min + price_max) / 2
        comparable_count = 1  # Guideline = 1 comparable
        data_source = "guideline_values"
    else:
        # No data at all
        return {
            "has_data": False,
            "locality": locality,
            "asset_type": asset_type,
            "message": "No registry transactions or guideline values found for this locality.",
        }

    # Compute data age
    from datetime import date
    if has_registry_data and stats.get("latest_date"):
        try:
            latest = date.fromisoformat(stats["latest_date"])
            data_age_months = max(1, (date.today() - latest).days // 30)
        except (ValueError, TypeError):
            data_age_months = 20
    elif has_guideline_data:
        # Guideline from Jul 2024
        try:
            eff_date = date.fromisoformat(guideline["effective_date"])
            data_age_months = max(1, (date.today() - eff_date).days // 30)
        except (ValueError, TypeError):
            data_age_months = 20
    else:
        data_age_months = 24

    return {
        "has_data": True,
        "locality": locality,
        "asset_type": asset_type,
        "data_source": data_source,

        # Pricing
        "price_min": price_min,
        "price_max": price_max,
        "price_median": price_median,
        "comparable_count": comparable_count,

        # Statistics (from SQL function)
        "stats": stats if has_registry_data else None,

        # Guideline reference
        "guideline": guideline,

        # Metadata
        "metadata": metadata or {
            "zone_tier": "C",
            "features": [],
            "infra_premium": {},
        },

        # For confidence engine
        "data_age_months": data_age_months,
        "has_registry_data": has_registry_data,
        "has_guideline_data": has_guideline_data,
    }
