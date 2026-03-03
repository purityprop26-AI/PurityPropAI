"""
PurityProp — Embedding Pipeline
================================

Batch embeds registry transactions and guideline values.
Generates 384-dim vectors via HuggingFace all-MiniLM-L6-v2.

Run: python -m migrations.embed_transactions
"""

from __future__ import annotations

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Load .env BEFORE importing app modules — embedding_service reads HF_API_TOKEN at import time
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from sqlalchemy import text
from app.core.database import get_db_context
from app.core.embedding_service import embed_query, vector_to_pg_literal

import structlog
logger = structlog.get_logger(__name__)


async def build_embedding_text(row: dict) -> str:
    """Build a searchable text representation for embedding."""
    parts = [
        f"{row.get('locality', '')} {row.get('district', '')}",
        f"{row.get('asset_type', 'land')} property",
        f"price {row.get('price_per_sqft', '')} per sqft",
        f"area {row.get('area_sqft', '')} sqft",
        f"zone {row.get('zone_tier', '')}",
    ]
    if row.get('micro_market'):
        parts.append(row['micro_market'])
    return " ".join(p for p in parts if p.strip())


async def embed_registry_transactions():
    """Batch embed all registry transactions that don't have embeddings."""
    print("Embedding registry_transactions...")
    count = 0
    errors = 0

    async with get_db_context() as session:
        # Get unembedded transactions
        result = await session.execute(text("""
            SELECT id, district, locality, micro_market, asset_type,
                   area_sqft, price_per_sqft, zone_tier
            FROM registry_transactions
            WHERE embedding IS NULL
            ORDER BY created_at DESC
            LIMIT 2500
        """))
        rows = result.fetchall()
        total = len(rows)
        print(f"  Found {total} transactions to embed")

        for i, row in enumerate(rows):
            row_dict = {
                "locality": row[2], "district": row[1],
                "micro_market": row[3], "asset_type": row[4],
                "area_sqft": row[5], "price_per_sqft": row[6],
                "zone_tier": row[7],
            }
            embed_text = await build_embedding_text(row_dict)
            vector = await embed_query(embed_text)

            if vector:
                vec_literal = vector_to_pg_literal(vector)
                await session.execute(
                    text("""
                        UPDATE registry_transactions
                        SET embedding = CAST(:vec AS vector)
                        WHERE id = CAST(:id AS uuid)
                    """),
                    {"vec": vec_literal, "id": str(row[0])}
                )
                count += 1
            else:
                errors += 1

            if (i + 1) % 10 == 0:
                print(f"  Progress: {i+1}/{total} (embedded: {count}, errors: {errors})")
                await asyncio.sleep(0.5)  # Rate limit HF API

    print(f"  ✅ Embedded {count}/{total} transactions ({errors} errors)")


async def embed_guideline_descriptions():
    """Create searchable text representations for guideline values."""
    print("Creating guideline embeddings (stored as registry_transactions with source='guideline')...")
    # Guideline values don't need vector embeddings — they're looked up by exact locality.
    # But we create text descriptions for potential future RAG use.
    print("  ℹ️ Guideline values use scalar lookup, not vector search. Skipping.")


async def verify_embeddings():
    """Verify embedding coverage."""
    print("\nVerifying embeddings...")
    async with get_db_context() as session:
        total = await session.execute(text("SELECT COUNT(*) FROM registry_transactions"))
        embedded = await session.execute(text(
            "SELECT COUNT(*) FROM registry_transactions WHERE embedding IS NOT NULL"
        ))
        print(f"  Total transactions: {total.scalar()}")
        print(f"  With embeddings: {embedded.scalar()}")

        # Test vector search
        test = await session.execute(text("""
            SELECT locality, price_per_sqft,
                   1 - (embedding <=> (SELECT embedding FROM registry_transactions LIMIT 1)) AS sim
            FROM registry_transactions
            WHERE embedding IS NOT NULL
            ORDER BY sim DESC
            LIMIT 3
        """))
        for row in test.fetchall():
            sim_val = row[2] if row[2] is not None else 0.0
            price_val = row[1] if row[1] is not None else 0
            print(f"  Vector test: {row[0]} Rs.{price_val}/sqft (sim: {sim_val:.4f})")


async def main():
    print("=" * 60)
    print("PURITYPROP EMBEDDING PIPELINE")
    print("=" * 60)

    await embed_registry_transactions()
    await embed_guideline_descriptions()
    await verify_embeddings()

    print("\n" + "=" * 60)
    print("EMBEDDING PIPELINE COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
