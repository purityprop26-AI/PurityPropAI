"""
SUPABASE-NATIVE REAL ESTATE INTELLIGENCE SYSTEM
Phase 7 Validation — Observability & Logging Tests
"""
import sys
import os
import json
import asyncio
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test")
os.environ.setdefault("GROQ_API_KEY", "test")

from app.core.observability import (
    MetricsCollector,
    RequestTracer,
    DatabaseMonitor,
    GroqMonitor,
    VectorSearchMonitor,
    HallucinationMonitor,
    ObservabilityHub,
    get_observability_hub,
    track_latency,
)


def test_metrics_collector():
    """Test metrics collector — counters, gauges, histograms."""
    print("--- Test 1: Metrics Collector ---")

    m = MetricsCollector()

    # Counters
    m.increment("test_counter")
    m.increment("test_counter")
    m.increment("test_counter", 5)
    assert m.get_counter("test_counter") == 7
    print(f"  ✓ Counter: {m.get_counter('test_counter')}")

    # Gauges
    m.set_gauge("test_gauge", 42.5)
    assert m.get_gauge("test_gauge") == 42.5
    print(f"  ✓ Gauge: {m.get_gauge('test_gauge')}")

    # Histograms
    for val in [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
        m.observe("test_histogram", val)
    stats = m.get_histogram_stats("test_histogram")
    assert stats["count"] == 10
    assert stats["avg"] == 55.0
    assert stats["min"] == 10.0
    assert stats["max"] == 100.0
    assert stats["p50"] > 0
    assert stats["p95"] > 0
    print(f"  ✓ Histogram: count={stats['count']}, avg={stats['avg']}, p95={stats['p95']}")

    # Labels
    m.increment("labeled_counter", labels={"method": "GET"})
    m.increment("labeled_counter", labels={"method": "POST"})
    assert m.get_counter('labeled_counter{method="GET"}') == 1
    assert m.get_counter('labeled_counter{method="POST"}') == 1
    print(f"  ✓ Labeled counters work")

    return True


def test_prometheus_export():
    """Test Prometheus text format export."""
    print("\n--- Test 2: Prometheus Export ---")

    m = MetricsCollector()
    m.increment("http_requests_total", 100)
    m.set_gauge("active_connections", 5)
    m.observe("request_duration_ms", 25.5)
    m.observe("request_duration_ms", 50.0)

    export = m.export_prometheus()
    assert "uptime_seconds" in export
    assert "http_requests_total 100" in export
    assert "active_connections 5" in export
    assert "request_duration_ms_count 2" in export
    print(f"  ✓ Export contains uptime, counters, gauges, histograms")
    print(f"  ✓ Export length: {len(export)} chars")

    return True


def test_snapshot():
    """Test metrics snapshot."""
    print("\n--- Test 3: Metrics Snapshot ---")

    m = MetricsCollector()
    m.increment("queries", 10)
    m.set_gauge("pool_size", 5.0)
    m.observe("latency", 25.0)

    snap = m.snapshot()
    assert "uptime_seconds" in snap
    assert "counters" in snap
    assert "gauges" in snap
    assert "histograms" in snap
    assert "exported_at" in snap
    print(f"  ✓ Snapshot keys: {list(snap.keys())}")

    # JSON serializable
    json.dumps(snap)
    print(f"  ✓ Snapshot is JSON serializable")

    return True


async def test_request_tracer():
    """Test request tracing with correlation IDs."""
    print("\n--- Test 4: Request Tracer ---")

    m = MetricsCollector()
    tracer = RequestTracer(m)

    async with tracer.trace("test_operation", {"user": "test"}) as trace_id:
        assert trace_id is not None
        assert len(trace_id) == 8  # Short trace ID
        await asyncio.sleep(0.05)

    assert m.get_counter('spans_total{operation="test_operation"}') == 1
    stats = m.get_histogram_stats('span_duration_ms{operation="test_operation"}')
    assert stats["count"] == 1
    assert stats["avg"] >= 40  # At least 40ms (we slept 50ms)
    print(f"  ✓ Trace ID: {trace_id}")
    print(f"  ✓ Span recorded: duration={stats['avg']}ms")

    return True


async def test_db_monitor():
    """Test database operation monitoring."""
    print("\n--- Test 5: Database Monitor ---")

    m = MetricsCollector()
    db = DatabaseMonitor(m)

    async with db.track_query("select"):
        await asyncio.sleep(0.02)

    async with db.track_query("insert"):
        await asyncio.sleep(0.01)

    select_key = 'db_queries_total{type="select"}'
    insert_key = 'db_queries_total{type="insert"}'
    assert m.get_counter(select_key) == 1
    assert m.get_counter(insert_key) == 1
    select_count = m.get_counter(select_key)
    insert_count = m.get_counter(insert_key)
    print(f"  ✓ Select tracked: {select_count} queries")
    print(f"  ✓ Insert tracked: {insert_count} queries")

    # Test error tracking
    try:
        async with db.track_query("broken"):
            raise ValueError("test error")
    except ValueError:
        pass
    error_key = 'db_errors_total{type="broken"}'
    assert m.get_counter(error_key) == 1
    error_count = m.get_counter(error_key)
    print(f"  ✓ Error tracked: {error_count} errors")

    return True


async def test_groq_monitor():
    """Test Groq API monitoring."""
    print("\n--- Test 6: Groq Monitor ---")

    m = MetricsCollector()
    groq = GroqMonitor(m)

    async with groq.track_call("llama-3.1"):
        await asyncio.sleep(0.01)

    assert m.get_counter('groq_calls_total{model="llama-3.1"}') == 1
    print(f"  ✓ Groq call tracked")

    return True


async def test_vector_monitor():
    """Test vector search monitoring."""
    print("\n--- Test 7: Vector Search Monitor ---")

    m = MetricsCollector()
    vec = VectorSearchMonitor(m)

    async with vec.track_search(dimension=384, method="hnsw"):
        await asyncio.sleep(0.01)

    assert m.get_counter('vector_searches_total{method="hnsw"}') == 1
    assert m.get_gauge("vector_dimension") == 384.0
    print(f"  ✓ Vector search tracked, dimension={m.get_gauge('vector_dimension')}")

    return True


def test_hallucination_monitor():
    """Test hallucination detection monitoring."""
    print("\n--- Test 8: Hallucination Monitor ---")

    m = MetricsCollector()
    hall = HallucinationMonitor(m)

    hall.record_check("clean", total_claims=5, verified=5, unverified=0)
    hall.record_check("warning", total_claims=5, verified=4, unverified=1)
    hall.record_check("hallucination", total_claims=5, verified=2, unverified=3)

    assert m.get_counter("hallucination_checks_total") == 3
    assert m.get_counter('hallucination_verdicts_total{verdict="clean"}') == 1
    assert m.get_counter('hallucination_verdicts_total{verdict="warning"}') == 1
    assert m.get_counter('hallucination_verdicts_total{verdict="hallucination"}') == 1
    print(f"  ✓ Hallucination checks: {m.get_counter('hallucination_checks_total')}")
    print(f"  ✓ Verdicts tracked: clean=1, warning=1, hallucination=1")

    return True


def test_observability_hub():
    """Test the ObservabilityHub singleton and dashboard."""
    print("\n--- Test 9: Observability Hub ---")

    hub = get_observability_hub()
    assert hub is not None

    # Dashboard
    dashboard = hub.get_dashboard()
    assert "system" in dashboard
    assert "database" in dashboard
    assert "groq" in dashboard
    assert "vector_search" in dashboard
    assert "hallucination" in dashboard
    assert "raw_metrics" in dashboard

    # JSON serializable
    json.dumps(dashboard)
    print(f"  ✓ Dashboard keys: {list(dashboard.keys())}")
    print(f"  ✓ Dashboard is JSON serializable")
    print(f"  ✓ Uptime: {dashboard['system']['uptime_seconds']}s")

    return True


async def test_track_latency_decorator():
    """Test the @track_latency decorator."""
    print("\n--- Test 10: @track_latency Decorator ---")

    @track_latency("decorated_function_ms")
    async def example_function():
        await asyncio.sleep(0.05)
        return 42

    result = await example_function()
    assert result == 42

    hub = get_observability_hub()
    stats = hub.metrics.get_histogram_stats("decorated_function_ms")
    assert stats["count"] >= 1
    assert stats["avg"] >= 40
    print(f"  ✓ Decorated function returned: {result}")
    print(f"  ✓ Latency tracked: {stats['avg']}ms")

    return True


async def async_main():
    """Run all async tests."""
    await test_request_tracer()
    await test_db_monitor()
    await test_groq_monitor()
    await test_vector_monitor()
    await test_track_latency_decorator()


if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 7 VALIDATION — OBSERVABILITY & LOGGING")
    print("=" * 60)

    sync_tests = [
        ("Metrics Collector", test_metrics_collector),
        ("Prometheus Export", test_prometheus_export),
        ("Metrics Snapshot", test_snapshot),
        ("Hallucination Monitor", test_hallucination_monitor),
        ("Observability Hub", test_observability_hub),
    ]

    results = {}
    all_pass = True

    for name, test_fn in sync_tests:
        try:
            test_fn()
            results[name] = "PASS"
        except Exception as e:
            results[name] = f"FAIL: {e}"
            all_pass = False
            print(f"  ✗ FAILED: {e}")

    # Async tests
    async_tests = [
        "Request Tracer",
        "DB Monitor",
        "Groq Monitor",
        "Vector Monitor",
        "Latency Decorator",
    ]
    try:
        asyncio.run(async_main())
        for name in async_tests:
            results[name] = "PASS"
    except Exception as e:
        for name in async_tests:
            if name not in results:
                results[name] = f"FAIL: {e}"
        all_pass = False

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
    with open(os.path.join(state_dir, "phase7_validation.json"), "w") as f:
        json.dump({"tests": results, "status": overall}, f, indent=2)

    if not all_pass:
        sys.exit(1)
