"""
SUPABASE-NATIVE REAL ESTATE INTELLIGENCE SYSTEM
Phase 7: Observability — Structured Logging, Metrics, Tracing

Provides:
- Structured JSON logging via structlog
- Prometheus-compatible metrics collection
- Request tracing with correlation IDs
- Performance monitoring for DB, Groq, and vector operations
"""
from __future__ import annotations
import time
import uuid
import functools
import structlog
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timezone
from collections import defaultdict
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field


logger = structlog.get_logger(__name__)


# ============================================
# METRICS COLLECTOR
# ============================================

class MetricsCollector:
    """Thread-safe metrics collector for the intelligence system."""

    def __init__(self):
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._start_time = time.time()
        self._MAX_HISTOGRAM_SIZE = 1000

    def increment(self, name: str, value: int = 1, labels: Optional[Dict] = None):
        """Increment a counter."""
        key = self._make_key(name, labels)
        self._counters[key] += value

    def set_gauge(self, name: str, value: float, labels: Optional[Dict] = None):
        """Set a gauge value."""
        key = self._make_key(name, labels)
        self._gauges[key] = value

    def observe(self, name: str, value: float, labels: Optional[Dict] = None):
        """Add an observation to a histogram."""
        key = self._make_key(name, labels)
        self._histograms[key].append(value)
        if len(self._histograms[key]) > self._MAX_HISTOGRAM_SIZE:
            self._histograms[key] = self._histograms[key][-500:]

    def _make_key(self, name: str, labels: Optional[Dict] = None) -> str:
        if labels:
            label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
            return f"{name}{{{label_str}}}"
        return name

    def get_counter(self, name: str) -> int:
        return self._counters.get(name, 0)

    def get_gauge(self, name: str) -> float:
        return self._gauges.get(name, 0.0)

    def get_histogram_stats(self, name: str) -> Dict[str, float]:
        values = self._histograms.get(name, [])
        if not values:
            return {"count": 0, "avg": 0, "p50": 0, "p95": 0, "p99": 0, "min": 0, "max": 0}

        sorted_vals = sorted(values)
        n = len(sorted_vals)
        return {
            "count": n,
            "avg": round(sum(sorted_vals) / n, 3),
            "p50": round(sorted_vals[int(n * 0.50)], 3),
            "p95": round(sorted_vals[int(n * 0.95)], 3),
            "p99": round(sorted_vals[min(int(n * 0.99), n - 1)], 3),
            "min": round(sorted_vals[0], 3),
            "max": round(sorted_vals[-1], 3),
        }

    def get_uptime(self) -> float:
        return round(time.time() - self._start_time, 2)

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus text format."""
        lines = []
        lines.append(f"# HELP uptime_seconds Application uptime in seconds")
        lines.append(f"# TYPE uptime_seconds gauge")
        lines.append(f"uptime_seconds {self.get_uptime()}")

        for key, value in sorted(self._counters.items()):
            safe_key = key.split("{")[0]
            lines.append(f"# TYPE {safe_key} counter")
            lines.append(f"{key} {value}")

        for key, value in sorted(self._gauges.items()):
            safe_key = key.split("{")[0]
            lines.append(f"# TYPE {safe_key} gauge")
            lines.append(f"{key} {value}")

        for key, values in sorted(self._histograms.items()):
            safe_key = key.split("{")[0]
            stats = self.get_histogram_stats(key)
            lines.append(f"# TYPE {safe_key} summary")
            lines.append(f'{safe_key}_count {stats["count"]}')
            lines.append(f'{safe_key}_avg {stats["avg"]}')
            lines.append(f'{safe_key}_p95 {stats["p95"]}')

        return "\n".join(lines) + "\n"

    def snapshot(self) -> Dict[str, Any]:
        """Return a complete metrics snapshot."""
        return {
            "uptime_seconds": self.get_uptime(),
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {
                k: self.get_histogram_stats(k)
                for k in self._histograms
            },
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }


# ============================================
# REQUEST TRACER
# ============================================

class RequestTracer:
    """Traces individual requests with correlation IDs and span tracking."""

    def __init__(self, metrics: MetricsCollector):
        self.metrics = metrics

    @asynccontextmanager
    async def trace(self, operation: str, metadata: Optional[Dict] = None):
        """Async context manager for tracing operations."""
        trace_id = str(uuid.uuid4())[:8]
        start = time.perf_counter()

        bound_logger = logger.bind(
            trace_id=trace_id,
            operation=operation,
        )

        bound_logger.info(
            "span_start",
            **(metadata or {}),
        )

        self.metrics.increment("spans_total", labels={"operation": operation})

        error = None
        try:
            yield trace_id
        except Exception as e:
            error = str(e)
            self.metrics.increment("span_errors_total", labels={"operation": operation})
            raise
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            self.metrics.observe(
                f"span_duration_ms",
                elapsed_ms,
                labels={"operation": operation},
            )

            log_fn = bound_logger.error if error else bound_logger.info
            log_fn(
                "span_end",
                elapsed_ms=round(elapsed_ms, 3),
                error=error,
            )


# ============================================
# OPERATION MONITORS
# ============================================

class DatabaseMonitor:
    """Monitors database operation performance."""

    def __init__(self, metrics: MetricsCollector):
        self.metrics = metrics

    @asynccontextmanager
    async def track_query(self, query_type: str = "select"):
        """Track database query performance."""
        start = time.perf_counter()
        self.metrics.increment("db_queries_total", labels={"type": query_type})

        try:
            yield
        except Exception as e:
            self.metrics.increment("db_errors_total", labels={"type": query_type})
            logger.error("db_query_error", query_type=query_type, error=str(e))
            raise
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            self.metrics.observe("db_query_duration_ms", elapsed_ms, labels={"type": query_type})

            if elapsed_ms > 1000:
                logger.warning("slow_query_detected", query_type=query_type, elapsed_ms=round(elapsed_ms, 2))


class GroqMonitor:
    """Monitors Groq API call performance."""

    def __init__(self, metrics: MetricsCollector):
        self.metrics = metrics

    @asynccontextmanager
    async def track_call(self, model: str = "default"):
        """Track Groq API call performance."""
        start = time.perf_counter()
        self.metrics.increment("groq_calls_total", labels={"model": model})

        try:
            yield
        except Exception as e:
            self.metrics.increment("groq_errors_total", labels={"model": model})
            logger.error("groq_call_error", model=model, error=str(e))
            raise
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            self.metrics.observe("groq_call_duration_ms", elapsed_ms, labels={"model": model})

            if elapsed_ms > 5000:
                logger.warning("slow_groq_call", model=model, elapsed_ms=round(elapsed_ms, 2))


class VectorSearchMonitor:
    """Monitors vector search operation performance."""

    def __init__(self, metrics: MetricsCollector):
        self.metrics = metrics

    @asynccontextmanager
    async def track_search(self, dimension: int = 384, method: str = "hnsw"):
        """Track vector search performance."""
        start = time.perf_counter()
        self.metrics.increment("vector_searches_total", labels={"method": method})

        try:
            yield
        except Exception as e:
            self.metrics.increment("vector_search_errors_total", labels={"method": method})
            raise
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            self.metrics.observe("vector_search_duration_ms", elapsed_ms, labels={"method": method})
            self.metrics.set_gauge("vector_dimension", float(dimension))


class HallucinationMonitor:
    """Monitors hallucination detection performance."""

    def __init__(self, metrics: MetricsCollector):
        self.metrics = metrics

    def record_check(self, verdict: str, total_claims: int, verified: int, unverified: int):
        """Record a hallucination check result."""
        self.metrics.increment("hallucination_checks_total")
        self.metrics.increment(f"hallucination_verdicts_total", labels={"verdict": verdict})
        self.metrics.set_gauge("hallucination_last_claims_total", float(total_claims))
        self.metrics.set_gauge("hallucination_last_verified", float(verified))
        self.metrics.set_gauge("hallucination_last_unverified", float(unverified))

        if verdict == "hallucination":
            logger.warning(
                "hallucination_detected",
                total_claims=total_claims,
                verified=verified,
                unverified=unverified,
            )


# ============================================
# OBSERVABILITY HUB (Singleton)
# ============================================

class ObservabilityHub:
    """Central hub for all observability components."""

    def __init__(self):
        self.metrics = MetricsCollector()
        self.tracer = RequestTracer(self.metrics)
        self.db_monitor = DatabaseMonitor(self.metrics)
        self.groq_monitor = GroqMonitor(self.metrics)
        self.vector_monitor = VectorSearchMonitor(self.metrics)
        self.hallucination_monitor = HallucinationMonitor(self.metrics)

    def get_dashboard(self) -> Dict[str, Any]:
        """Return a complete observability dashboard."""
        snapshot = self.metrics.snapshot()
        return {
            "system": {
                "uptime_seconds": snapshot["uptime_seconds"],
                "status": "operational",
            },
            "database": {
                "total_queries": self.metrics.get_counter("db_queries_total"),
                "errors": self.metrics.get_counter("db_errors_total"),
                "latency": self.metrics.get_histogram_stats("db_query_duration_ms"),
            },
            "groq": {
                "total_calls": self.metrics.get_counter("groq_calls_total"),
                "errors": self.metrics.get_counter("groq_errors_total"),
                "latency": self.metrics.get_histogram_stats("groq_call_duration_ms"),
            },
            "vector_search": {
                "total_searches": self.metrics.get_counter("vector_searches_total"),
                "errors": self.metrics.get_counter("vector_search_errors_total"),
                "latency": self.metrics.get_histogram_stats("vector_search_duration_ms"),
            },
            "hallucination": {
                "total_checks": self.metrics.get_counter("hallucination_checks_total"),
                "clean": self.metrics.get_counter('hallucination_verdicts_total{verdict="clean"}'),
                "warnings": self.metrics.get_counter('hallucination_verdicts_total{verdict="warning"}'),
                "detected": self.metrics.get_counter('hallucination_verdicts_total{verdict="hallucination"}'),
            },
            "raw_metrics": snapshot,
        }


# Singleton
_hub: Optional[ObservabilityHub] = None


def get_observability_hub() -> ObservabilityHub:
    """Get the singleton observability hub."""
    global _hub
    if _hub is None:
        _hub = ObservabilityHub()
    return _hub


# ============================================
# DECORATORS
# ============================================

def track_latency(metric_name: str):
    """Decorator to track function execution latency."""
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            hub = get_observability_hub()
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                elapsed_ms = (time.perf_counter() - start) * 1000
                hub.metrics.observe(metric_name, elapsed_ms)
        return wrapper
    return decorator
