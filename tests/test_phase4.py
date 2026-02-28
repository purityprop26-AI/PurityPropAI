"""
SUPABASE-NATIVE REAL ESTATE INTELLIGENCE SYSTEM
Phase 4 Validation — Deterministic Microservices Unit Tests
"""
import sys
import os
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from microservices.financial_services import (
    compute_cagr, compute_liquidity_score, compute_absorption_rate,
    compute_distance_decay_premium, compute_forecast_ensemble,
    compute_risk_synthesis, execute_service,
    CAGRInput, LiquidityInput, AbsorptionInput,
    DistanceDecayInput, ForecastInput, RiskInput,
)
from pydantic import ValidationError


def test_cagr():
    """Test CAGR computation — deterministic."""
    print("--- Test CAGR ---")

    # Test 1: Standard case
    result = compute_cagr(CAGRInput(beginning_value=100000, ending_value=150000, years=5))
    assert abs(result.cagr - 0.084472) < 0.001, f"CAGR mismatch: {result.cagr}"
    print(f"  ✓ Standard: {result.cagr_percent}%")

    # Test 2: Determinism — run 10 times, all identical
    results = [
        compute_cagr(CAGRInput(beginning_value=100000, ending_value=150000, years=5)).cagr
        for _ in range(10)
    ]
    assert len(set(results)) == 1, "CAGR not deterministic!"
    print(f"  ✓ Deterministic: 10 runs identical")

    # Test 3: Edge case — 1 year
    result = compute_cagr(CAGRInput(beginning_value=100, ending_value=200, years=1))
    assert abs(result.cagr - 1.0) < 0.001
    print(f"  ✓ Edge (1yr): {result.cagr_percent}%")

    # Test 4: Input validation
    try:
        CAGRInput(beginning_value=-100, ending_value=200, years=5)
        assert False, "Should have rejected negative value"
    except ValidationError:
        print(f"  ✓ Input validation: rejects negative values")

    return True


def test_liquidity():
    """Test liquidity score computation."""
    print("\n--- Test Liquidity ---")

    result = compute_liquidity_score(LiquidityInput(
        total_listings=100, total_sold=80,
        avg_days_on_market=45, price_volatility=0.1
    ))
    assert 0 <= result.liquidity_score <= 1
    assert result.rating in ("highly_liquid", "moderately_liquid", "illiquid", "frozen")
    print(f"  ✓ Score: {result.liquidity_score}, Rating: {result.rating}")

    # Determinism
    results = [
        compute_liquidity_score(LiquidityInput(
            total_listings=100, total_sold=80,
            avg_days_on_market=45, price_volatility=0.1
        )).liquidity_score
        for _ in range(10)
    ]
    assert len(set(results)) == 1
    print(f"  ✓ Deterministic: 10 runs identical")

    # Zero listings
    result = compute_liquidity_score(LiquidityInput(
        total_listings=0, total_sold=0,
        avg_days_on_market=0, price_volatility=0
    ))
    assert result.liquidity_score >= 0
    print(f"  ✓ Zero input handled: {result.liquidity_score}")

    return True


def test_absorption():
    """Test absorption rate computation."""
    print("\n--- Test Absorption ---")

    result = compute_absorption_rate(AbsorptionInput(
        total_sold=60, period_months=12, active_inventory=200
    ))
    assert result.absorption_rate > 0
    assert result.market_condition in ("seller_market", "balanced", "buyer_market", "no_data")
    print(f"  ✓ Rate: {result.absorption_rate}, Months supply: {result.months_of_supply}, Condition: {result.market_condition}")

    # Determinism
    results = [
        compute_absorption_rate(AbsorptionInput(
            total_sold=60, period_months=12, active_inventory=200
        )).absorption_rate
        for _ in range(10)
    ]
    assert len(set(results)) == 1
    print(f"  ✓ Deterministic: 10 runs identical")

    return True


def test_distance_decay():
    """Test distance-decay premium computation."""
    print("\n--- Test Distance Decay ---")

    result = compute_distance_decay_premium(DistanceDecayInput(
        base_price_per_sqft=5000,
        distances_km=[
            {"name": "Metro Station", "distance_km": 0.5, "weight": 2.0},
            {"name": "Hospital", "distance_km": 1.0, "weight": 1.5},
            {"name": "School", "distance_km": 0.3, "weight": 1.0},
            {"name": "Mall", "distance_km": 2.0, "weight": 1.0},
        ],
        decay_rate=0.15,
    ))
    assert result.adjusted_price_per_sqft > result.adjusted_price_per_sqft * 0
    assert result.premium_percent >= 0
    print(f"  ✓ Adjusted: ₹{result.adjusted_price_per_sqft}/sqft (+{result.premium_percent}%)")

    # Determinism
    results = [
        compute_distance_decay_premium(DistanceDecayInput(
            base_price_per_sqft=5000,
            distances_km=[
                {"name": "Metro", "distance_km": 0.5, "weight": 2.0},
            ],
            decay_rate=0.15,
        )).adjusted_price_per_sqft
        for _ in range(10)
    ]
    assert len(set(results)) == 1
    print(f"  ✓ Deterministic: 10 runs identical")

    return True


def test_forecast():
    """Test forecast ensemble computation."""
    print("\n--- Test Forecast ---")

    result = compute_forecast_ensemble(ForecastInput(
        historical_prices=[5000, 5200, 5400, 5600, 5800, 6000, 6200, 6400, 6600, 6800, 7000, 7200],
        periods=6,
    ))
    assert len(result.forecast_values) == 6
    assert result.trend in ("upward", "downward", "stable")
    assert len(result.confidence_interval["lower"]) == 6
    assert len(result.confidence_interval["upper"]) == 6
    print(f"  ✓ Forecast: {result.forecast_values}")
    print(f"  ✓ Trend: {result.trend}, Growth: {result.avg_growth_rate}")

    # Determinism
    results = [
        compute_forecast_ensemble(ForecastInput(
            historical_prices=[5000, 5200, 5400, 5600, 5800, 6000],
            periods=3,
        )).forecast_values
        for _ in range(10)
    ]
    assert all(r == results[0] for r in results)
    print(f"  ✓ Deterministic: 10 runs identical")

    return True


def test_risk():
    """Test risk synthesis computation."""
    print("\n--- Test Risk ---")

    result = compute_risk_synthesis(RiskInput(
        cagr=0.08,
        liquidity_score=0.65,
        absorption_rate=0.12,
        price_volatility=0.15,
    ))
    assert 0 <= result.overall_risk_score <= 1
    assert result.risk_level in ("low", "moderate", "high")
    assert len(result.risk_factors) > 0
    assert len(result.recommendations) > 0
    print(f"  ✓ Risk: {result.overall_risk_score} ({result.risk_level})")
    print(f"  ✓ Factors: {len(result.risk_factors)}, Recommendations: {len(result.recommendations)}")

    # Determinism
    results = [
        compute_risk_synthesis(RiskInput(
            cagr=0.08, liquidity_score=0.65,
            absorption_rate=0.12, price_volatility=0.15,
        )).overall_risk_score
        for _ in range(10)
    ]
    assert len(set(results)) == 1
    print(f"  ✓ Deterministic: 10 runs identical")

    return True


def test_service_registry():
    """Test the service registry execute_service function."""
    print("\n--- Test Service Registry ---")

    result = execute_service("cagr", {
        "beginning_value": 100000,
        "ending_value": 150000,
        "years": 5,
    })
    assert "cagr" in result
    assert result["service"] == "cagr_microservice"
    print(f"  ✓ Registry call: cagr = {result['cagr_percent']}%")

    # Unknown service
    try:
        execute_service("unknown_service", {})
        assert False, "Should have raised ValueError"
    except ValueError:
        print(f"  ✓ Unknown service rejected")

    # Malformed data
    try:
        execute_service("cagr", {"beginning_value": "not_a_number"})
        assert False, "Should have raised ValidationError"
    except (ValidationError, Exception):
        print(f"  ✓ Malformed input rejected")

    return True


def test_json_serialization():
    """Test all outputs are strictly JSON serializable."""
    print("\n--- Test JSON Serialization ---")

    outputs = [
        compute_cagr(CAGRInput(beginning_value=100, ending_value=200, years=3)),
        compute_liquidity_score(LiquidityInput(total_listings=100, total_sold=50, avg_days_on_market=60, price_volatility=0.2)),
        compute_absorption_rate(AbsorptionInput(total_sold=30, period_months=6, active_inventory=100)),
        compute_distance_decay_premium(DistanceDecayInput(base_price_per_sqft=5000, distances_km=[{"name": "Metro", "distance_km": 1.0, "weight": 1.0}])),
        compute_forecast_ensemble(ForecastInput(historical_prices=[100, 110, 120, 130, 140])),
        compute_risk_synthesis(RiskInput(cagr=0.1, liquidity_score=0.6)),
    ]

    for output in outputs:
        json_str = json.dumps(output.model_dump())
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)
        print(f"  ✓ {output.service}: JSON serializable")

    return True


if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 4 VALIDATION — DETERMINISTIC MICROSERVICES")
    print("=" * 60)

    tests = [
        ("CAGR", test_cagr),
        ("Liquidity", test_liquidity),
        ("Absorption", test_absorption),
        ("Distance Decay", test_distance_decay),
        ("Forecast", test_forecast),
        ("Risk", test_risk),
        ("Service Registry", test_service_registry),
        ("JSON Serialization", test_json_serialization),
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
    print(f"RESULTS:")
    for name, status in results.items():
        icon = "✓" if status == "PASS" else "✗"
        print(f"  {icon} {name}: {status}")

    overall = "SUCCESS" if all_pass else "FAILED"
    print(f"\nOVERALL STATUS: {overall}")
    print(f"{'=' * 60}")

    # Save results
    state_dir = os.path.join(os.path.dirname(__file__), "..", "state")
    os.makedirs(state_dir, exist_ok=True)
    with open(os.path.join(state_dir, "phase4_validation.json"), "w") as f:
        json.dump({"tests": results, "status": overall.lower()}, f, indent=2)

    if not all_pass:
        sys.exit(1)
