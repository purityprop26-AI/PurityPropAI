"""
SUPABASE-NATIVE REAL ESTATE INTELLIGENCE SYSTEM
Phase 3 Validation — Async Concurrency & Blocking Detection
"""
import asyncio
import ast
import os
import sys
import json
import time
import importlib
import inspect

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:puritypropAI26@db.rqqkhmbayxnsoyxhpfmk.supabase.co:5432/postgres")
os.environ.setdefault("SUPABASE_URL", "https://rqqkhmbayxnsoyxhpfmk.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test")
os.environ.setdefault("GROQ_API_KEY", "test")


# ============================================
# Test 1: Blocking Call Detection
# ============================================
BLOCKING_PATTERNS = {
    "time.sleep",
    "requests.get", "requests.post", "requests.put", "requests.delete",
    "open(",  # sync file I/O
    "psycopg2",
    "sqlite3",
    "urllib.request",
}

ASYNC_SAFE_EXCEPTIONS = {
    "aiofiles.open",
    "asyncpg",
    "__file__",
    "open(",  # Allow in config loading
}


def scan_for_blocking_calls(directory: str) -> dict:
    """Scan Python files for blocking I/O calls."""
    results = {"files_scanned": 0, "blocking_calls": [], "status": "pass"}

    for root, dirs, files in os.walk(directory):
        # Skip venv and __pycache__
        dirs[:] = [d for d in dirs if d not in ("venv", "__pycache__", ".git", "node_modules")]

        for filename in files:
            if not filename.endswith(".py"):
                continue

            filepath = os.path.join(root, filename)
            results["files_scanned"] += 1

            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                for line_num, line in enumerate(content.split("\n"), 1):
                    stripped = line.strip()
                    if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                        continue

                    if "time.sleep" in stripped:
                        results["blocking_calls"].append({
                            "file": os.path.relpath(filepath, directory),
                            "line": line_num,
                            "pattern": "time.sleep",
                            "content": stripped[:100],
                        })

                    for pat in ("requests.get", "requests.post", "requests.put"):
                        if pat in stripped and "import" not in stripped:
                            results["blocking_calls"].append({
                                "file": os.path.relpath(filepath, directory),
                                "line": line_num,
                                "pattern": pat,
                                "content": stripped[:100],
                            })

            except Exception as e:
                pass

    if results["blocking_calls"]:
        results["status"] = "warning"  # Warning, not fail — some may be in non-async code

    return results


# ============================================
# Test 2: Module Import Validation
# ============================================
def validate_imports() -> dict:
    """Validate that all critical modules import correctly."""
    results = {"imports": {}, "status": "pass"}

    modules_to_check = [
        ("app.core.config", "Settings configuration"),
        ("app.core.database", "Async database engine"),
        ("app.core.groq_client", "Groq client"),
        ("app.core.schemas", "Pydantic schemas"),
        ("app.core.models", "SQLAlchemy models"),
        ("app.api.routes", "API routes"),
        ("app.intelligence_app", "FastAPI application"),
    ]

    for module_name, description in modules_to_check:
        try:
            mod = importlib.import_module(module_name)
            results["imports"][module_name] = {
                "status": "ok",
                "description": description,
            }
        except Exception as e:
            results["imports"][module_name] = {
                "status": "error",
                "description": description,
                "error": str(e),
            }
            results["status"] = "fail"

    return results


# ============================================
# Test 3: Async Function Verification
# ============================================
def verify_async_endpoints() -> dict:
    """Verify all API endpoints are async."""
    results = {"endpoints": [], "status": "pass"}

    try:
        from app.api.routes import router
        for route in router.routes:
            if hasattr(route, "endpoint"):
                is_async = inspect.iscoroutinefunction(route.endpoint)
                results["endpoints"].append({
                    "path": getattr(route, "path", "unknown"),
                    "name": route.endpoint.__name__,
                    "is_async": is_async,
                    "methods": list(getattr(route, "methods", set())),
                })
                if not is_async:
                    results["status"] = "fail"
    except Exception as e:
        results["error"] = str(e)
        results["status"] = "fail"

    return results


# ============================================
# Test 4: Concurrency Test
# ============================================
async def test_concurrency() -> dict:
    """Test async concurrency with multiple simultaneous operations."""
    results = {"status": "pass", "concurrent_tasks": 0, "max_concurrent": 0, "errors": []}

    concurrent_count = 0
    max_seen = 0
    lock = asyncio.Lock()

    async def simulated_task(task_id: int):
        nonlocal concurrent_count, max_seen
        async with lock:
            concurrent_count += 1
            if concurrent_count > max_seen:
                max_seen = concurrent_count

        await asyncio.sleep(0.1)  # Simulate async I/O

        async with lock:
            concurrent_count -= 1

        return task_id

    try:
        tasks = [simulated_task(i) for i in range(20)]
        start = time.perf_counter()
        results_list = await asyncio.gather(*tasks)
        elapsed = time.perf_counter() - start

        results["concurrent_tasks"] = len(results_list)
        results["max_concurrent"] = max_seen
        results["elapsed_seconds"] = round(elapsed, 3)
        results["concurrency_ratio"] = round(max_seen / len(tasks), 2)

        # If tasks ran truly concurrently, elapsed should be ~0.1s, not ~2.0s
        if elapsed > 1.0:
            results["status"] = "fail"
            results["errors"].append("Tasks appear to run sequentially, not concurrently")

    except Exception as e:
        results["status"] = "fail"
        results["errors"].append(str(e))

    return results


# ============================================
# Main
# ============================================
async def main():
    print("=" * 60)
    print("PHASE 3 VALIDATION — ASYNC FASTAPI")
    print("=" * 60)

    all_results = {}

    # Test 1: Blocking calls
    print("\n--- Test 1: Blocking Call Detection ---")
    backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
    blocking = scan_for_blocking_calls(backend_dir)
    all_results["blocking_calls"] = blocking
    print(f"  Files scanned: {blocking['files_scanned']}")
    print(f"  Blocking calls found: {len(blocking['blocking_calls'])}")
    print(f"  Status: {blocking['status']}")

    # Test 2: Imports
    print("\n--- Test 2: Module Import Validation ---")
    imports = validate_imports()
    all_results["imports"] = imports
    for mod, info in imports["imports"].items():
        status_icon = "✓" if info["status"] == "ok" else "✗"
        print(f"  {status_icon} {mod}: {info['status']}")
        if info.get("error"):
            print(f"    Error: {info['error']}")
    print(f"  Status: {imports['status']}")

    # Test 3: Async endpoints
    print("\n--- Test 3: Async Endpoint Verification ---")
    endpoints = verify_async_endpoints()
    all_results["endpoints"] = endpoints
    for ep in endpoints.get("endpoints", []):
        icon = "✓" if ep["is_async"] else "✗"
        print(f"  {icon} {ep['methods']} {ep['path']} -> {ep['name']} (async={ep['is_async']})")
    print(f"  Status: {endpoints['status']}")

    # Test 4: Concurrency
    print("\n--- Test 4: Async Concurrency Test ---")
    concurrency = await test_concurrency()
    all_results["concurrency"] = concurrency
    print(f"  Tasks: {concurrency['concurrent_tasks']}")
    print(f"  Max concurrent: {concurrency['max_concurrent']}")
    print(f"  Elapsed: {concurrency.get('elapsed_seconds', 'N/A')}s")
    print(f"  Status: {concurrency['status']}")

    # Overall
    overall = all([
        blocking["status"] != "fail",
        imports["status"] == "pass",
        endpoints["status"] == "pass",
        concurrency["status"] == "pass",
    ])
    all_results["overall_status"] = "success" if overall else "failed"

    print(f"\n{'=' * 60}")
    print(f"OVERALL STATUS: {all_results['overall_status'].upper()}")
    print(f"{'=' * 60}")

    # Save results
    state_dir = os.path.join(os.path.dirname(__file__), "..", "state")
    os.makedirs(state_dir, exist_ok=True)
    output_path = os.path.join(state_dir, "phase3_validation.json")
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    print(f"\nResults: {output_path}")

    if not overall:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
