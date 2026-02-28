"""
SUPABASE-NATIVE REAL ESTATE INTELLIGENCE SYSTEM
API Routes — /query, /health, /metrics

Hybrid RAG Pipeline (v3):
  [STAGE 1]  Vector Search    — pgvector cosine similarity (embed_query → HF API)
  [STAGE 2]  Keyword / SQL    — full-text ILIKE + scalar filters
  [STAGE 3]  Spatial Search   — PostGIS ST_DWithin (if lat/lng provided)
  [STAGE 4]  RRF Merge        — Reciprocal Rank Fusion across all three lists
  [STAGE 5]  Cross-Encoder    — feature-based re-ranking (budget, BHK, locality)
  [STAGE 6]  Top-K Injection  — top-5 context chunks injected into LLM prompt
  [STAGE 7]  Strict Evidence  — LLM answers ONLY from injected context
  [STAGE 8]  Hallucination Guard — numeric claim verification before response
"""
import time
import uuid
import re
import json
import structlog
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.database import get_db_session, check_db_health
from app.core.groq_client import get_groq_client
from app.core.schemas import (
    QueryRequest, QueryResponse, PropertyResponse,
    HealthResponse, MetricsResponse, ErrorResponse,
)
from app.core.config import get_settings
from app.core.hallucination_adapter import HallucinationGuard
from app.core.embedding_service import embed_query, vector_to_pg_literal
from app.core.reranker import cross_score, extract_top_k_context

logger = structlog.get_logger(__name__)
router = APIRouter()

# In-memory metrics — capped list prevents unbounded memory growth [FIX HIGH-B2]
_MAX_LATENCY_HISTORY = 500
_metrics = {
    "total_queries": 0,
    "latencies": [],
    "errors": 0,
    "start_time": time.time(),
}

# ILIKE wildcard escape (prevents pattern DoS via injected % and _ chars)
_ILIKE_SPECIAL = re.compile(r"([%_\\])")


def _escape_ilike(value: str) -> str:
    """Escape ILIKE wildcard characters to prevent pattern injection DoS."""
    return _ILIKE_SPECIAL.sub(r"\\\1", value)


# ============================================
# /query — Main Intelligence Endpoint
# ============================================
@router.post(
    "/query",
    response_model=QueryResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Intelligent Property Query",
    description="Hybrid search: full-text + spatial + scalar filtering with AI-verified summary",
)
async def query_properties(
    request: QueryRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Execute hybrid property search with hallucination-verified AI summary.

    FIX [HIGH-B5]: Single SQL query with COUNT(*) OVER() window function.
                   Eliminates the duplicate WHERE clause execution (previously 2x DB cost).
    FIX [CRIT-G1]: HallucinationGuard.verify() called on AI summary before returning.
    FIX [MED-B1]:  ILIKE patterns have %, _, \\ escaped.
    FIX [MED-D3]:  Heavy TOAST columns (images, price_history) excluded from list query.
    """
    start_time = time.perf_counter()
    request_id = str(uuid.uuid4())

    logger.info(
        "query_start",
        request_id=request_id,
        query=request.query,
        city=request.city,
    )

    try:
        # --- Build WHERE clause ---
        conditions = ["deleted_at IS NULL"]
        sql_params = {}

        if request.city:
            conditions.append("city = :city")
            sql_params["city"] = request.city

        if request.property_type:
            conditions.append("property_type = :property_type")
            sql_params["property_type"] = request.property_type.value

        if request.min_price is not None:
            conditions.append("price >= :min_price")
            sql_params["min_price"] = request.min_price

        if request.max_price is not None:
            conditions.append("price <= :max_price")
            sql_params["max_price"] = request.max_price

        if request.bedrooms is not None:
            conditions.append("bedrooms = :bedrooms")
            sql_params["bedrooms"] = request.bedrooms

        if request.locality:
            # FIX [MED-B1]: Escape ILIKE wildcards before wrapping with %
            escaped_locality = _escape_ilike(request.locality)
            conditions.append("locality ILIKE :locality")
            sql_params["locality"] = f"%{escaped_locality}%"

        # Full-text keyword ILIKE search
        if request.query:
            stop_words = {
                "in", "under", "above", "below", "near", "around",
                "with", "for", "the", "a", "an", "and", "or",
            }
            raw_keywords = [
                w for w in request.query.split()
                if w.lower() not in stop_words and len(w) > 1
            ]

            if raw_keywords:
                keyword_conditions = []
                for i, kw in enumerate(raw_keywords[:5]):  # Cap at 5 keywords
                    # FIX [MED-B1]: Escape user input before ILIKE wrapping
                    escaped_kw = _escape_ilike(kw)
                    param_name = f"kw_{i}"
                    keyword_conditions.append(f"""(
                        title ILIKE :{param_name}
                        OR locality ILIKE :{param_name}
                        OR builder_name ILIKE :{param_name}
                    )""")
                    sql_params[param_name] = f"%{escaped_kw}%"

                conditions.append("(" + " OR ".join(keyword_conditions) + ")")

            sql_params["query_text"] = request.query

        # Spatial filter
        if request.lat is not None and request.lng is not None:
            conditions.append("""
                ST_DWithin(
                    location::geography,
                    ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
                    :radius_m
                )
            """)
            sql_params["lat"] = request.lat
            sql_params["lng"] = request.lng
            sql_params["radius_m"] = request.radius_km * 1000

        where_clause = " AND ".join(conditions)

        # ── STAGE 1: Vector Search (pgvector cosine) ─────────────────────
        # Embed the user's query using HuggingFace all-MiniLM-L6-v2 (384d).
        # Falls back gracefully if HF_API_TOKEN is missing.
        vector_ids: list[str] = []   # ordered list of property IDs by vector rank
        query_vector = await embed_query(request.query)
        if query_vector:
            vector_literal = vector_to_pg_literal(query_vector)
            set_ef = text("SET hnsw.ef_search = 48")  # Tuned: 48 gives ~95% recall with m=16
            await session.execute(set_ef)
            vector_sql = text(f"""
                SELECT id::text, (embedding <=> '{vector_literal}'::vector) AS cos_dist
                FROM properties
                WHERE {where_clause} AND embedding IS NOT NULL
                ORDER BY cos_dist ASC
                LIMIT 50
            """)
            vec_result = await session.execute(vector_sql, sql_params)
            vector_ids = [str(r["id"]) for r in vec_result.mappings().all()]
            logger.info("vector_search_done", hits=len(vector_ids), request_id=request_id)

        # ── STAGE 2&3: Keyword + Spatial SQL Search ───────────────────────
        # Build scoring expression
        score_parts = []
        if request.query:
            score_parts.append("""
                ts_rank(
                    to_tsvector('english',
                        coalesce(title, '') || ' ' ||
                        coalesce(locality, '') || ' ' ||
                        coalesce(builder_name, '') || ' ' ||
                        coalesce(project_name, '')
                    ),
                    plainto_tsquery('english', :query_text)
                ) * 0.5
            """)
        if request.lat is not None and request.lng is not None:
            score_parts.append("""
                (1.0 / (1.0 + ST_DistanceSphere(
                    location,
                    ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)
                ) / 1000.0)) * 0.3
            """)

        score_expr = " + ".join(score_parts) if score_parts else "0.0"

        # FIX [HIGH-B5]: COUNT(*) OVER() window eliminates duplicate round-trip
        # FIX [MED-D3]:  Heavy TOAST cols excluded (images, price_history, amenities)
        sql = text(f"""
            SELECT
                id, title, slug, property_type, listing_type, status,
                price, price_per_sqft, currency,
                carpet_area_sqft, built_up_area_sqft,
                locality, city, pincode,
                bedrooms, bathrooms, parking_slots,
                furnishing, facing, attributes,
                builder_name, project_name, rera_id,
                is_verified, is_featured, listed_at,
                ({score_expr})::float AS combined_score,
                COUNT(*) OVER() AS total_count
            FROM properties
            WHERE {where_clause}
            ORDER BY combined_score DESC
            LIMIT :result_limit OFFSET :result_offset
        """)

        # Fetch up to 5x the requested limit for reranking headroom, capped at 100
        sql_params["result_limit"] = min(100, request.limit * 5)
        sql_params["result_offset"] = request.offset

        # Single DB round-trip
        result = await session.execute(sql, sql_params)
        rows = result.mappings().all()

        total_count = int(rows[0]["total_count"]) if rows else 0

        # Build property dicts for re-ranker
        raw_props = [dict(r) for r in rows]
        keyword_ids = [str(p["id"]) for p in raw_props]
        spatial_ids = [
            str(p["id"]) for p in raw_props
            if (p.get("combined_score") or 0) > 0
        ]

        # ── STAGE 4: RRF Merge ────────────────────────────────────────────
        from app.core.reranker import reciprocal_rank_fusion
        rrf_order = reciprocal_rank_fusion(vector_ids, keyword_ids, spatial_ids)
        rrf_id_map = {pid: score for pid, score in rrf_order}

        # Re-order raw_props by RRF score
        for p in raw_props:
            p["combined_score"] = rrf_id_map.get(str(p["id"]), p.get("combined_score", 0.0))
        rrf_sorted = sorted(raw_props, key=lambda x: x.get("combined_score", 0), reverse=True)

        # ── STAGE 5: Cross-Encoder Re-Ranking ────────────────────────────
        reranked = cross_score(request.query, rrf_sorted)

        # Trim to requested limit AFTER re-ranking (we fetched up to 100 above)
        reranked = reranked[:request.limit]

        # Build Pydantic response objects
        properties = []
        for row in reranked:
            prop = PropertyResponse(
                id=row["id"],
                title=row["title"],
                slug=row["slug"],
                description=None,
                property_type=row["property_type"],
                listing_type=row["listing_type"],
                status=row["status"],
                price=float(row["price"]),
                price_per_sqft=float(row["price_per_sqft"]) if row.get("price_per_sqft") else None,
                currency=row.get("currency", "INR"),
                carpet_area_sqft=float(row["carpet_area_sqft"]) if row.get("carpet_area_sqft") else None,
                built_up_area_sqft=float(row["built_up_area_sqft"]) if row.get("built_up_area_sqft") else None,
                locality=row["locality"],
                city=row["city"],
                pincode=row.get("pincode"),
                bedrooms=row.get("bedrooms"),
                bathrooms=row.get("bathrooms"),
                parking_slots=row.get("parking_slots"),
                furnishing=row.get("furnishing"),
                facing=row.get("facing"),
                attributes=row.get("attributes") or {},
                amenities=[],
                images=[],
                builder_name=row.get("builder_name"),
                project_name=row.get("project_name"),
                rera_id=row.get("rera_id"),
                is_verified=row.get("is_verified", False),
                is_featured=row.get("is_featured", False),
                listed_at=row.get("listed_at"),
                combined_score=row.get("cross_score") or row.get("combined_score"),
            )
            properties.append(prop)

        # ── STAGE 6 & 7: Top-K Context Injection + Strict Evidence Mode ──
        ai_summary = None
        ai_verified = False
        retrieval_method = "hybrid_vector+keyword+spatial+rrf+crossenc" if query_vector else "hybrid_keyword+spatial+crossenc"

        if properties and not getattr(request, "stream", False):
            try:
                groq = get_groq_client()

                # Lean, grounded context — only DB-sourced fields
                props_context = extract_top_k_context(
                    [p.__dict__ for p in properties], k=5
                )
                context_json = json.dumps(props_context, default=str, ensure_ascii=False, indent=2)

                # ── STRICT EVIDENCE MODE SYSTEM PROMPT ────────────────────
                # Deterministic, hallucination-free, context-only answers.
                # The LLM is forbidden from using training knowledge.
                system_prompt = (
                    "You are a domain-restricted real estate AI operating in STRICT EVIDENCE MODE.\n"
                    "The retrieved property context below has been filtered, merged (RRF), and re-ranked.\n"
                    "\n"
                    "NON-NEGOTIABLE RULES:\n"
                    "1. Answer ONLY using the RETRIEVED CONTEXT provided in this prompt.\n"
                    "2. Do NOT use your training knowledge.\n"
                    "3. Do NOT infer, estimate, or extrapolate any values.\n"
                    "4. Do NOT fabricate prices, areas, or property counts.\n"
                    "5. Every numeric claim MUST match a field in the context exactly.\n"
                    "6. If the context lacks information, say exactly: "
                    "'The provided documents do not contain sufficient information to answer this.'\n"
                    "7. Separate each property clearly using its Property ID.\n"
                    "8. Do NOT use phrases like 'typically', 'in general', 'it is likely'.\n"
                    "\n"
                    "FORMAT:\n"
                    "- Bullet points for features.\n"
                    "- Structured summary per property: Property ID | Location | Price | Key Features.\n"
                    "- Maximum 5 sentences total. Be concise and precise.\n"
                    "\n"
                    f"RETRIEVED CONTEXT (top-{len(props_context)} re-ranked results):\n"
                    f"{context_json}"
                )

                summary_response = await groq.chat(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": (
                                f"User Query: {request.query}\n"
                                f"Total matching properties in database: {total_count}\n"
                                f"Answer strictly from the retrieved context above."
                            ),
                        },
                    ],
                    max_tokens=350,
                    temperature=0.0,   # Deterministic — no creativity
                )

                raw_summary = summary_response.get("content", "")

                # ── STAGE 8: Hallucination Guard ──────────────────────────
                guard = HallucinationGuard()
                verified_summary, verification_result = guard.verify(
                    ai_response=raw_summary,
                    source_data=props_context,
                )

                ai_summary = verified_summary
                ai_verified = verification_result.get("passed", False)

                if not ai_verified:
                    logger.warning(
                        "hallucination_detected",
                        request_id=request_id,
                        verdict=verification_result.get("verdict"),
                        flagged_count=verification_result.get("flagged_count", 0),
                    )

            except Exception as e:
                logger.warning("ai_summary_failed", error=str(e), request_id=request_id)

        # --- Metrics update ---
        latency_ms = (time.perf_counter() - start_time) * 1000
        _metrics["total_queries"] += 1
        _metrics["latencies"].append(latency_ms)
        if len(_metrics["latencies"]) > _MAX_LATENCY_HISTORY * 2:
            _metrics["latencies"] = _metrics["latencies"][-_MAX_LATENCY_HISTORY:]

        logger.info(
            "query_complete",
            request_id=request_id,
            results=len(properties),
            total=total_count,
            latency_ms=round(latency_ms, 2),
            ai_verified=ai_verified,
            vector_search=bool(query_vector),
        )

        return QueryResponse(
            query=request.query,
            properties=properties,
            total_results=total_count,
            analytics=None,
            ai_summary=ai_summary,
            retrieval_method=retrieval_method,
            latency_ms=round(latency_ms, 2),
            metadata={
                "request_id": request_id,
                "ai_verified": ai_verified,
                "vector_search_active": bool(query_vector),
                "vector_candidates": len(vector_ids),
                "keyword_candidates": len(keyword_ids),
                "rrf_merged": len(rrf_order),
                "reranked_to": len(properties),
                "strict_evidence_mode": True,
                "filters_applied": {
                    k: v for k, v in sql_params.items()
                    if k not in ("result_limit", "result_offset")
                },
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        _metrics["errors"] += 1
        logger.error("query_failed", request_id=request_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal query error")


# ============================================
# /health — Readiness Check (DB-dependent)
# ============================================
@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Intelligence API Health Check",
)
async def health_check():
    """
    Readiness check — verifies database, extensions, and Groq client.
    NOTE: Do NOT use as liveness probe — DB slowness kills containers unnecessarily.
    """
    db_health = await check_db_health()
    groq = get_groq_client()
    groq_metrics = groq.get_metrics()
    uptime = time.time() - _metrics["start_time"]

    return HealthResponse(
        status="healthy" if db_health["status"] == "healthy" else "degraded",
        timestamp=datetime.now(timezone.utc),
        version="2.0.0",
        database=db_health,
        groq={
            "status": "configured",
            "model": get_settings().groq_model,
            **groq_metrics,
        },
        uptime_seconds=round(uptime, 2),
    )


# ============================================
# /metrics — Performance Metrics
# ============================================
@router.get(
    "/metrics",
    response_model=MetricsResponse,
    summary="System Performance Metrics",
)
async def get_metrics():
    """Return current performance metrics. Safe to poll — no DB queries."""
    latencies = _metrics["latencies"]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
    sorted_lats = sorted(latencies)
    p95_idx = max(0, int(len(sorted_lats) * 0.95) - 1)
    p95_latency = sorted_lats[p95_idx] if sorted_lats else 0.0

    groq = get_groq_client()
    settings = get_settings()

    return MetricsResponse(
        total_queries=_metrics["total_queries"],
        avg_latency_ms=round(avg_latency, 2),
        p95_latency_ms=round(p95_latency, 2),
        cache_hit_rate=0.0,
        groq_metrics=groq.get_metrics(),
        db_pool_stats={
            "pool_size": settings.db_pool_size,
            "max_overflow": settings.db_max_overflow,
            "total_max": settings.db_pool_size + settings.db_max_overflow,
        },
        vector_index_health={
            "type": "hnsw",
            "dimension": 384,
            "metric": "cosine",
            "ef_search": 48,
            "iterative_scan": "relaxed_order",
        },
    )
