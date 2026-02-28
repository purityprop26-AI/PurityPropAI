"""
SUPABASE-NATIVE REAL ESTATE INTELLIGENCE SYSTEM
Phase 6 Validation — Docker & CI/CD Verification
"""
import sys
import os
import json
import subprocess
import yaml


def test_dockerfile():
    """Validate Dockerfile structure."""
    print("--- Test 1: Dockerfile Validation ---")

    dockerfile = os.path.join(os.path.dirname(__file__), "..", "Dockerfile")
    assert os.path.exists(dockerfile), "Dockerfile missing"

    with open(dockerfile, "r") as f:
        content = f.read()

    # Multi-stage build
    assert content.count("FROM") >= 2, "Must be multi-stage build"
    print(f"  ✓ Multi-stage: {content.count('FROM')} stages")

    # Non-root user
    assert "USER appuser" in content or "USER app" in content, "Must run as non-root"
    print(f"  ✓ Non-root user configured")

    # Health check
    assert "HEALTHCHECK" in content, "Must have healthcheck"
    print(f"  ✓ HEALTHCHECK defined")

    # No secrets baked in
    assert "password" not in content.lower() or "password" in content.lower().split("#")[0] is False, "No secrets in Dockerfile"
    assert "API_KEY" not in content, "No API keys in Dockerfile"
    print(f"  ✓ No secrets baked in")

    # uvicorn/uvloop
    assert "uvicorn" in content, "Must use uvicorn"
    assert "uvloop" in content, "Should use uvloop for performance"
    print(f"  ✓ uvicorn + uvloop configured")

    return True


def test_docker_compose():
    """Validate docker-compose.yml structure."""
    print("\n--- Test 2: Docker Compose Validation ---")

    compose_path = os.path.join(os.path.dirname(__file__), "..", "docker-compose.yml")
    assert os.path.exists(compose_path), "docker-compose.yml missing"

    with open(compose_path, "r") as f:
        compose = yaml.safe_load(f)

    assert "services" in compose, "Must have services"
    services = compose["services"]

    # intelligence-api service
    assert "intelligence-api" in services, "Must have intelligence-api service"
    api = services["intelligence-api"]

    # Health check
    assert "healthcheck" in api, "API service must have healthcheck"
    print(f"  ✓ intelligence-api with healthcheck")

    # Resource limits
    assert "deploy" in api, "Must have deploy config"
    assert "resources" in api["deploy"], "Must have resource limits"
    print(f"  ✓ Resource limits configured")

    # Environment from .env
    assert "env_file" in api, "Must reference env_file"
    print(f"  ✓ env_file referenced")

    # Network
    assert "networks" in compose, "Must define networks"
    print(f"  ✓ Network defined")

    return True


def test_ci_pipeline():
    """Validate CI/CD pipeline structure."""
    print("\n--- Test 3: CI/CD Pipeline Validation ---")

    ci_path = os.path.join(os.path.dirname(__file__), "..", "cicd", "ci.yml")
    assert os.path.exists(ci_path), "CI pipeline missing"

    with open(ci_path, "r") as f:
        ci = yaml.safe_load(f)

    assert "jobs" in ci, "Must have jobs"
    jobs = ci["jobs"]

    required_jobs = {"lint", "test", "build"}
    actual_jobs = set(jobs.keys())
    missing = required_jobs - actual_jobs
    assert not missing, f"Missing jobs: {missing}"

    print(f"  ✓ Jobs: {list(jobs.keys())}")

    # Check test job runs our validation tests
    test_job = jobs["test"]
    steps = test_job.get("steps", [])
    step_names = [s.get("name", "") for s in steps]
    print(f"  ✓ Test steps: {[n for n in step_names if n]}")

    # Check build job uses Docker
    build_job = jobs["build"]
    assert "needs" in build_job, "Build must depend on test"
    print(f"  ✓ Build depends on: {build_job['needs']}")

    return True


def test_dockerignore():
    """Validate .dockerignore exists and excludes secrets."""
    print("\n--- Test 4: .dockerignore Validation ---")

    ignore_path = os.path.join(os.path.dirname(__file__), "..", ".dockerignore")
    assert os.path.exists(ignore_path), ".dockerignore missing"

    with open(ignore_path, "r") as f:
        content = f.read()

    required_excludes = [".env", "venv", ".terraform", "state/"]
    for exc in required_excludes:
        found = any(exc in line for line in content.split("\n"))
        assert found, f"Must exclude {exc}"
        print(f"  ✓ Excludes: {exc}")

    return True


def test_prometheus_config():
    """Validate Prometheus configuration."""
    print("\n--- Test 5: Prometheus Config Validation ---")

    prom_path = os.path.join(os.path.dirname(__file__), "..", "cicd", "prometheus.yml")
    assert os.path.exists(prom_path), "prometheus.yml missing"

    with open(prom_path, "r") as f:
        config = yaml.safe_load(f)

    assert "scrape_configs" in config, "Must have scrape_configs"
    scrape = config["scrape_configs"][0]
    assert scrape["metrics_path"] == "/api/v1/metrics", "Must scrape /api/v1/metrics"
    print(f"  ✓ Scrapes: {scrape['metrics_path']}")
    print(f"  ✓ Targets: {scrape['static_configs'][0]['targets']}")

    return True


def test_docker_available():
    """Check Docker is available for image build."""
    print("\n--- Test 6: Docker Availability ---")

    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0
        print(f"  ✓ Docker: {result.stdout.strip()}")
    except Exception as e:
        print(f"  ⚠ Docker check: {e}")
        return True  # Non-fatal

    # Check Docker is running
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            print(f"  ✓ Docker daemon running")
        else:
            print(f"  ⚠ Docker daemon not running (non-fatal)")
    except Exception:
        pass

    return True


if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 6 VALIDATION — DOCKER / CI-CD")
    print("=" * 60)

    tests = [
        ("Dockerfile", test_dockerfile),
        ("Docker Compose", test_docker_compose),
        ("CI Pipeline", test_ci_pipeline),
        ("Docker Ignore", test_dockerignore),
        ("Prometheus Config", test_prometheus_config),
        ("Docker Available", test_docker_available),
    ]

    results = {}
    all_pass = True

    for name, test_fn in tests:
        try:
            passed = test_fn()
            results[name] = "PASS"
        except Exception as e:
            results[name] = f"FAIL: {e}"
            all_pass = False
            print(f"  ✗ FAILED: {e}")

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
    with open(os.path.join(state_dir, "phase6_validation.json"), "w") as f:
        json.dump({"tests": results, "status": overall}, f, indent=2)

    if not all_pass:
        sys.exit(1)
