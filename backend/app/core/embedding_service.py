"""
Embedding Service — Query Vectorisation for Hybrid RAG
Calls HuggingFace Inference API (all-MiniLM-L6-v2, 384-dim).

Why HF API instead of local sentence-transformers:
  • No PyTorch dependency (saves ~2 GB on container)
  • Free tier: 30,000 requests / month
  • Hosted on same model used to build property embeddings

Env var required: HF_API_TOKEN  (or set HF_API_TOKEN="" to disable)
If disabled, vector search is skipped; keyword+spatial search still runs.
"""

from __future__ import annotations

import hashlib
import structlog
import httpx
import os
from typing import List, Optional

logger = structlog.get_logger(__name__)

# ── Constants ─────────────────────────────────────────────────────────
HF_API_URL = (
    "https://router.huggingface.co/hf-inference/models/"
    "sentence-transformers/all-MiniLM-L6-v2/pipeline/feature-extraction"
)
EMBEDDING_DIM = 384
_HF_TOKEN = os.getenv("HF_API_TOKEN", "")

# ── Persistent client (shared connection pool, TLS reuse) ─────────────
_client: Optional[httpx.AsyncClient] = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        headers = {"Content-Type": "application/json"}
        if _HF_TOKEN:
            headers["Authorization"] = f"Bearer {_HF_TOKEN}"
        _client = httpx.AsyncClient(
            headers=headers,
            timeout=httpx.Timeout(10.0, connect=5.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )
    return _client


# ── In-process LRU cache (avoids re-embedding identical queries) ───────
_EMBED_CACHE: dict[str, List[float]] = {}
_CACHE_MAX = 256


def _cache_key(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


async def close_embedding_client() -> None:
    """Call on app shutdown to flush the connection pool."""
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


# ── Public API ─────────────────────────────────────────────────────────
async def embed_query(query: str) -> Optional[List[float]]:
    """
    Return a 384-dim embedding vector for *query*.

    Returns None if:
    - HF_API_TOKEN is not set (disabled mode)
    - HF API call fails (graceful degradation — keyword search continues)
    """
    if not _HF_TOKEN:
        logger.debug("embedding_disabled", reason="HF_API_TOKEN not set")
        return None

    key = _cache_key(query)
    if key in _EMBED_CACHE:
        logger.debug("embedding_cache_hit", query_prefix=query[:40])
        return _EMBED_CACHE[key]

    try:
        client = _get_client()
        response = await client.post(
            HF_API_URL,
            json={"inputs": query, "options": {"wait_for_model": True}},
        )
        response.raise_for_status()
        data = response.json()

        # HF returns [[...384 floats...]] — unwrap outer list
        if isinstance(data, list) and isinstance(data[0], list):
            vector = data[0]
        elif isinstance(data, list) and isinstance(data[0], float):
            vector = data
        else:
            logger.warning("embedding_unexpected_shape", shape=type(data).__name__)
            return None

        if len(vector) != EMBEDDING_DIM:
            logger.warning("embedding_dim_mismatch", got=len(vector), expected=EMBEDDING_DIM)
            return None

        # Cache with LRU eviction (drop oldest when full)
        if len(_EMBED_CACHE) >= _CACHE_MAX:
            oldest = next(iter(_EMBED_CACHE))
            del _EMBED_CACHE[oldest]
        _EMBED_CACHE[key] = vector

        logger.info("embedding_generated", query_prefix=query[:40], dim=len(vector))
        return vector

    except httpx.HTTPStatusError as e:
        logger.warning("embedding_api_error", status=e.response.status_code, query=query[:40])
        return None
    except Exception as e:
        logger.warning("embedding_failed", error=str(e), query=query[:40])
        return None


def vector_to_pg_literal(vector: List[float]) -> str:
    """
    Convert a Python list of floats to a PostgreSQL pgvector literal string.
    Example: [0.1, 0.2, ...] → '[0.1,0.2,...]'
    """
    return "[" + ",".join(f"{v:.6f}" for v in vector) + "]"
