"""
SUPABASE-NATIVE REAL ESTATE INTELLIGENCE SYSTEM
Phase 8: Integration Tests — End-to-End Async Validation

Tests the full pipeline:
  Query → Embedding → DB retrieval → Microservice compute → Hallucination check → Response
"""
import asyncio
import sys
import os
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:puritypropAI26@db.rqqkhmbayxnsoyxhpfmk.supabase.co:5432/postgres")
os.environ.setdefault("SUPABASE_URL", "https://rqqkhmbayxnsoyxhpfmk.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJxcWtobWJheXhuc295eGhwZm1rIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzEzOTEyNjAsImV4cCI6MjA4Njk2NzI2MH0.-UeEkUSotAUkkuT2JMf6vkorVmjK_FFaeqH8aExiTRU")
os.environ.setdefault("GROQ_API_KEY", "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")


async def test_database_operations():
    """Test async DB read/write with pgvector and PostGIS."""
    print("--- Test 1: Database Operations (Live) ---")

    from app.core.database import get_db_context, check_db_health
    from sqlalchemy import text

    # Health check
    health = await check_db_health()
    assert health["status"] == "healthy", f"DB unhealthy: {health}"
    print(f"  ✓ Database healthy")
    print(f"  ✓ PostGIS: {health.get('postgis_version')}")
    print(f"  ✓ pgvector: {health.get('pgvector')}")

    # Insert test property
    async with get_db_context() as session:
        test_id = await session.execute(text("""
            INSERT INTO properties (title, slug, property_type, listing_type, price, locality, city, location, attributes, embedding)
            VALUES (
                'Integration Test Property',
                'integration-test-' || extract(epoch from now())::text,
                'apartment', 'sale', 7500000.00,
                'T Nagar', 'Chennai',
                ST_SetSRID(ST_MakePoint(80.2340, 13.0404), 4326),
                '{"bhk": 3, "parking": true, "gym": true}'::jsonb,
                ('[' || array_to_string(array(SELECT random() FROM generate_series(1, 384)), ',') || ']')::vector
            )
            RETURNING id
        """))
        prop_id = test_id.scalar()
        assert prop_id is not None
        print(f"  ✓ Inserted test property: {prop_id}")

        # Vector search
        vector_result = await session.execute(text("""
            SELECT id, title,
                embedding <#> (SELECT embedding FROM properties WHERE id = :pid) AS distance
            FROM properties
            WHERE embedding IS NOT NULL AND id != :pid
            ORDER BY embedding <#> (SELECT embedding FROM properties WHERE id = :pid)
            LIMIT 3
        """), {"pid": prop_id})
        vec_rows = vector_result.fetchall()
        print(f"  ✓ Vector search: {len(vec_rows)} nearest neighbors found")

        # Spatial query
        spatial_result = await session.execute(text("""
            SELECT id, title,
                ST_DistanceSphere(location, ST_SetSRID(ST_MakePoint(80.2340, 13.0404), 4326)) AS distance_m
            FROM properties
            WHERE location IS NOT NULL
            AND ST_DWithin(
                location::geography,
                ST_SetSRID(ST_MakePoint(80.2340, 13.0404), 4326)::geography,
                5000
            )
        """))
        spatial_rows = spatial_result.fetchall()
        print(f"  ✓ Spatial query (5km): {len(spatial_rows)} properties within radius")

        # JSONB query
        jsonb_result = await session.execute(text("""
            SELECT id, title FROM properties
            WHERE attributes @> '{"bhk": 3}'::jsonb
        """))
        jsonb_rows = jsonb_result.fetchall()
        print(f"  ✓ JSONB query (3BHK): {len(jsonb_rows)} properties matched")

        # Full-text search
        fts_result = await session.execute(text("""
            SELECT id, title FROM properties
            WHERE to_tsvector('english', coalesce(title, '') || ' ' || coalesce(locality, ''))
                @@ plainto_tsquery('english', 'Integration Test')
        """))
        fts_rows = fts_result.fetchall()
        print(f"  ✓ Full-text search: {len(fts_rows)} results")

        # Cleanup
        await session.execute(text("DELETE FROM properties WHERE id = :pid"), {"pid": prop_id})
        print(f"  ✓ Cleanup: test property deleted")

    return True


async def test_microservice_pipeline():
    """Test full financial microservice pipeline."""
    print("\n--- Test 2: Microservice Pipeline ---")

    from microservices.financial_services import (
        compute_cagr, compute_liquidity_score, compute_absorption_rate,
        compute_distance_decay_premium, compute_forecast_ensemble,
        compute_risk_synthesis,
        CAGRInput, LiquidityInput, AbsorptionInput,
        DistanceDecayInput, ForecastInput, RiskInput,
    )

    start = time.perf_counter()

    # Step 1: CAGR
    cagr = compute_cagr(CAGRInput(beginning_value=4500, ending_value=7200, years=5))
    print(f"  ✓ CAGR: {cagr.cagr_percent}%")

    # Step 2: Liquidity
    liquidity = compute_liquidity_score(LiquidityInput(
        total_listings=150, total_sold=90,
        avg_days_on_market=55, price_volatility=0.12,
    ))
    print(f"  ✓ Liquidity: {liquidity.liquidity_score} ({liquidity.rating})")

    # Step 3: Absorption
    absorption = compute_absorption_rate(AbsorptionInput(
        total_sold=90, period_months=12, active_inventory=150,
    ))
    print(f"  ✓ Absorption: {absorption.absorption_rate} ({absorption.market_condition})")

    # Step 4: Distance Decay
    distance = compute_distance_decay_premium(DistanceDecayInput(
        base_price_per_sqft=6000,
        distances_km=[
            {"name": "T Nagar Metro", "distance_km": 0.8, "weight": 2.0},
            {"name": "PSBB School", "distance_km": 0.5, "weight": 1.5},
            {"name": "Apollo Hospital", "distance_km": 1.2, "weight": 1.0},
        ],
    ))
    print(f"  ✓ Distance Premium: +{distance.premium_percent}% → ₹{distance.adjusted_price_per_sqft}/sqft")

    # Step 5: Forecast
    forecast = compute_forecast_ensemble(ForecastInput(
        historical_prices=[4500, 4800, 5100, 5400, 5700, 6000, 6200, 6500, 6800, 7000, 7200],
        periods=6,
    ))
    print(f"  ✓ Forecast: {forecast.forecast_values[:3]}... ({forecast.trend})")

    # Step 6: Risk synthesis (uses outputs from above)
    risk = compute_risk_synthesis(RiskInput(
        cagr=cagr.cagr,
        liquidity_score=liquidity.liquidity_score,
        absorption_rate=absorption.absorption_rate,
        price_volatility=0.12,
    ))
    print(f"  ✓ Risk: {risk.overall_risk_score} ({risk.risk_level})")

    elapsed = (time.perf_counter() - start) * 1000
    print(f"  ✓ Full pipeline: {elapsed:.2f}ms")

    return True


async def test_hallucination_pipeline():
    """Test hallucination detection integrated with microservices."""
    print("\n--- Test 3: Hallucination Pipeline ---")

    from microservices.financial_services import (
        compute_cagr, CAGRInput,
        compute_liquidity_score, LiquidityInput,
    )
    from app.core.hallucination_guard import (
        HallucinationJudge, ResponseSanitizer,
    )

    # Run microservices
    cagr = compute_cagr(CAGRInput(beginning_value=4500, ending_value=7200, years=5))
    liquidity = compute_liquidity_score(LiquidityInput(
        total_listings=150, total_sold=90,
        avg_days_on_market=55, price_volatility=0.12,
    ))

    tool_outputs = {
        "cagr": cagr.model_dump(),
        "liquidity": liquidity.model_dump(),
    }

    judge = HallucinationJudge()

    # Test 1: Clean narrative using real tool outputs
    cagr_pct = cagr.cagr_percent
    liq_score = liquidity.liquidity_score
    clean_narrative = (
        f"T Nagar shows a healthy CAGR of {cagr_pct}% over 5 years. "
        f"The market has a liquidity score of {liq_score}."
    )

    verdict = judge.verify(clean_narrative, tool_outputs)
    assert verdict.verdict == "clean", f"Expected clean, got {verdict.verdict}"
    sanitized = ResponseSanitizer.sanitize(clean_narrative, verdict)
    assert sanitized == clean_narrative
    print(f"  ✓ Clean narrative: verdict={verdict.verdict}")

    # Test 2: Hallucinated narrative
    hallucinated = (
        "T Nagar shows an amazing CAGR of 25.3% over 5 years. "
        "The market has a liquidity score of 0.95 and prices are at ₹15,000 per sq ft."
    )

    verdict2 = judge.verify(hallucinated, tool_outputs)
    assert verdict2.mismatch_detected, "Should detect mismatches"
    sanitized2 = ResponseSanitizer.sanitize(hallucinated, verdict2)
    print(f"  ✓ Hallucinated narrative: verdict={verdict2.verdict}, mismatches={len(verdict2.mismatches)}")
    print(f"  ✓ Sanitized: {'REJECTED' if 'cannot provide' in sanitized2.lower() else 'FLAGGED'}")

    return True


async def test_observability_integration():
    """Test observability with actual operations."""
    print("\n--- Test 4: Observability Integration ---")

    from app.core.observability import get_observability_hub

    hub = get_observability_hub()

    # Simulate tracked operations
    async with hub.db_monitor.track_query("select"):
        await asyncio.sleep(0.01)

    async with hub.groq_monitor.track_call("llama-3.1"):
        await asyncio.sleep(0.01)

    async with hub.vector_monitor.track_search(384, "hnsw"):
        await asyncio.sleep(0.01)

    hub.hallucination_monitor.record_check("clean", 5, 5, 0)

    # Get dashboard
    dashboard = hub.get_dashboard()
    assert dashboard["system"]["status"] == "operational"
    print(f"  ✓ Dashboard operational, uptime={dashboard['system']['uptime_seconds']}s")

    # Prometheus export
    prom = hub.metrics.export_prometheus()
    assert "uptime_seconds" in prom
    print(f"  ✓ Prometheus export: {len(prom)} chars")

    return True


async def test_concurrent_queries():
    """Test concurrent async operations don't block each other."""
    print("\n--- Test 5: Concurrent Query Simulation ---")

    from microservices.financial_services import (
        compute_cagr, CAGRInput,
        compute_forecast_ensemble, ForecastInput,
    )

    async def simulated_query(query_id: int):
        """Simulate a full query pipeline."""
        await asyncio.sleep(0.01)  # Simulate DB lookup
        cagr = compute_cagr(CAGRInput(beginning_value=5000 + query_id * 100, ending_value=7000, years=5))
        forecast = compute_forecast_ensemble(ForecastInput(
            historical_prices=[5000, 5200, 5400, 5600, 5800, 6000],
            periods=3,
        ))
        await asyncio.sleep(0.01)  # Simulate Groq call
        return {
            "query_id": query_id,
            "cagr": cagr.cagr_percent,
            "forecast": forecast.forecast_values,
        }

    start = time.perf_counter()
    tasks = [simulated_query(i) for i in range(20)]
    results = await asyncio.gather(*tasks)
    elapsed = (time.perf_counter() - start) * 1000

    assert len(results) == 20
    assert all(r["cagr"] > 0 for r in results)
    # Concurrent should complete in ~20-40ms, not 20*20=400ms
    assert elapsed < 300, f"Too slow: {elapsed}ms (should be concurrent)"
    print(f"  ✓ 20 concurrent queries: {elapsed:.2f}ms")
    print(f"  ✓ All returned valid CAGR and forecast data")

    return True


async def test_schema_trigger_validation():
    """Test auto-triggers: updated_at, slug, price_per_sqft."""
    print("\n--- Test 6: Schema Trigger Validation ---")

    from app.core.database import get_db_context
    from sqlalchemy import text

    async with get_db_context() as session:
        # Insert property — triggers should fire
        result = await session.execute(text("""
            INSERT INTO properties (
                title, property_type, listing_type, price,
                carpet_area_sqft, locality, city
            )
            VALUES (
                'Trigger Test Property', 'apartment', 'sale', 8000000,
                1200, 'Anna Nagar', 'Chennai'
            )
            RETURNING id, slug, price_per_sqft, created_at, updated_at
        """))
        row = result.fetchone()
        prop_id = row[0]

        # Slug auto-generated
        slug = row[1]
        assert slug is not None and len(slug) > 0, "Slug should be auto-generated"
        print(f"  ✓ Auto-slug: {slug}")

        # Price per sqft auto-calculated
        ppsf = row[2]
        assert ppsf is not None, "Price per sqft should be auto-calculated"
        expected_ppsf = 8000000 / 1200
        assert abs(float(ppsf) - expected_ppsf) < 1, f"Price/sqft mismatch: {ppsf} vs {expected_ppsf}"
        print(f"  ✓ Auto price/sqft: ₹{ppsf}")

        # Update — should trigger updated_at
        await session.execute(text("""
            UPDATE properties SET price = 8500000 WHERE id = :pid
        """), {"pid": prop_id})

        updated = await session.execute(text("""
            SELECT updated_at, price_per_sqft FROM properties WHERE id = :pid
        """), {"pid": prop_id})
        updated_row = updated.fetchone()
        new_ppsf = updated_row[1]
        new_expected = 8500000 / 1200
        assert abs(float(new_ppsf) - new_expected) < 1, "Price/sqft should recalculate on update"
        print(f"  ✓ Updated price/sqft: ₹{new_ppsf}")

        # Cleanup
        await session.execute(text("DELETE FROM properties WHERE id = :pid"), {"pid": prop_id})
        print(f"  ✓ Cleanup done")

    return True


async def main():
    print("=" * 60)
    print("PHASE 8 VALIDATION — INTEGRATION TESTS")
    print("=" * 60)

    tests = [
        ("Database Operations", test_database_operations),
        ("Microservice Pipeline", test_microservice_pipeline),
        ("Hallucination Pipeline", test_hallucination_pipeline),
        ("Observability Integration", test_observability_integration),
        ("Concurrent Queries", test_concurrent_queries),
        ("Schema Triggers", test_schema_trigger_validation),
    ]

    results = {}
    all_pass = True

    for name, test_fn in tests:
        try:
            await test_fn()
            results[name] = "PASS"
        except Exception as e:
            results[name] = f"FAIL: {e}"
            all_pass = False
            print(f"  ✗ FAILED: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'=' * 60}")
    print("RESULTS:")
    for name, status in results.items():
        icon = "✓" if status == "PASS" else "✗"
        print(f"  {icon} {name}: {status}")

    overall = "success" if all_pass else "failed"
    print(f"\nOVERALL STATUS: {overall.upper()}")
    print(f"{'=' * 60}")

    state_dir = os.path.join(os.path.dirname(__file__), "..", "state")
    os.makedirs(state_dir, exist_ok=True)
    with open(os.path.join(state_dir, "phase8_validation.json"), "w") as f:
        json.dump({"tests": results, "status": overall}, f, indent=2)

    if not all_pass:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
