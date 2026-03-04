"""
End-to-End RAG Pipeline Test
Tests the full flow: query → extract locality → DB retrieval → valuation → LLM context
"""
import asyncio
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from app.services.domain_validator import extract_locality, extract_asset_type_from_query
from app.services.rag_retrieval import rag_retrieve
from app.services.valuation_engine import compute_valuation, format_valuation_for_llm
from app.core.database import get_db_context
from sqlalchemy import text


async def test_db_data():
    """Verify what's actually in the database."""
    print("=" * 60)
    print("DATABASE STATUS CHECK")
    print("=" * 60)
    async with get_db_context() as s:
        # Transaction counts
        r = await s.execute(text(
            "SELECT district, COUNT(*), COUNT(DISTINCT locality) "
            "FROM registry_transactions GROUP BY district ORDER BY COUNT(*) DESC"
        ))
        print("\nRegistry Transactions:")
        for row in r.fetchall():
            print(f"  {row[0]}: {row[1]} records, {row[2]} localities")

        # Guideline values
        r = await s.execute(text("SELECT COUNT(*) FROM guideline_values"))
        print(f"\nGuideline Values: {r.scalar()} rows")

        # Embeddings
        r = await s.execute(text(
            "SELECT COUNT(*) FROM registry_transactions WHERE embedding IS NOT NULL"
        ))
        print(f"Embedded: {r.scalar()} rows")

        # Sample prices for Coimbatore
        r = await s.execute(text(
            "SELECT locality, asset_type, price_per_sqft, registration_date "
            "FROM registry_transactions "
            "WHERE district = 'coimbatore' AND asset_type = 'land' "
            "ORDER BY locality, registration_date "
            "LIMIT 10"
        ))
        print("\nSample Coimbatore land prices:")
        for row in r.fetchall():
            price = float(row[2]) if row[2] else 0
            print(f"  {row[0]}: Rs.{price:,.0f}/sqft ({row[1]} | {row[3]})")


async def test_rag_queries():
    """Test full RAG pipeline with real queries."""
    print("\n" + "=" * 60)
    print("RAG PIPELINE TESTS")
    print("=" * 60)

    test_queries = [
        # Chennai queries (new ETL pipeline)
        "What is the land price in Thoraipakkam Chennai?",
        "OMR Chennai property rate",
        "Adyar Chennai apartment price",
        "Velachery Chennai land value",
        # Existing district queries
        "What is the land price in RS Puram Coimbatore?",
        "Fairlands Salem property rate",
        "Ellis Nagar Madurai apartment price",
        "DB Road Coimbatore land value",
        "Sellur Madurai property price",
    ]

    for query in test_queries:
        print(f"\n{'─'*60}")
        print(f"QUERY: {query}")
        print(f"{'─'*60}")

        locality = extract_locality(query)
        asset_type = extract_asset_type_from_query(query)
        print(f"  Extracted: locality={locality}, asset_type={asset_type}")

        if not locality:
            # Try direct locality extraction from the query
            words = query.lower().split()
            for w in words:
                w_norm = w.replace(' ', '_')
                locality = w_norm
                break

        try:
            rag_result = await rag_retrieve(query, locality, asset_type)

            if rag_result.get("has_data"):
                print(f"  Source: {rag_result['data_source']}")
                print(f"  Comps: {rag_result['comparable_count']}")
                print(f"  Price range: Rs.{rag_result['price_min']:,.0f} - Rs.{rag_result['price_max']:,.0f}/sqft")
                print(f"  Median: Rs.{rag_result['price_median']:,.0f}/sqft")

                # Compute valuation
                valuation = compute_valuation(rag_result)
                print(f"  Confidence: {valuation['confidence']['score']} ({valuation['confidence']['band']})")
                print(f"  Tier: {valuation['metrics_tier']}")
                if valuation.get('risks'):
                    for r in valuation['risks']:
                        print(f"  {r}")

                # Format for LLM (just first 3 lines)
                llm_text = format_valuation_for_llm(valuation)
                lines = llm_text.split('\n')
                print(f"\n  LLM Context (first 5 lines):")
                for line in lines[:5]:
                    print(f"    {line}")
            else:
                print(f"  NO DATA: {rag_result.get('message', 'unknown')}")
        except Exception as e:
            print(f"  ERROR: {e}")


async def main():
    await test_db_data()
    await test_rag_queries()
    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
