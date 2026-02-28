"""
SUPABASE-NATIVE REAL ESTATE INTELLIGENCE SYSTEM
Phase 5 Validation — Zero-Hallucination Enforcement Tests
"""
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.core.hallucination_guard import (
    HallucinationJudge,
    ResponseSanitizer,
    extract_numeric_claims,
    extract_tool_values,
    flatten_tool_values,
    SYSTEM_PROMPT_BASE,
    SYSTEM_PROMPT_FINANCIAL,
    TOOL_DEFINITIONS,
    HallucinationVerdict,
)


def test_numeric_extraction():
    """Test extraction of numeric claims from narrative text."""
    print("--- Test 1: Numeric Claim Extraction ---")

    text = """
    The property is priced at ₹85,00,000 (Rs. 85 Lakh) with a CAGR of 8.45%.
    The price per sq ft is 6,500/sq ft and it's located 2.3 km from the metro.
    This 3 BHK apartment has a carpet area of 1,250 sq ft.
    The liquidity score is 0.72 and absorption rate is 12.5%.
    """

    claims = extract_numeric_claims(text)
    assert len(claims) > 0, "Should extract at least some claims"

    types_found = {c["type"] for c in claims}
    print(f"  Extracted {len(claims)} claims")
    print(f"  Types found: {types_found}")

    # Check specific extractions
    price_claims = [c for c in claims if c["type"] == "price"]
    pct_claims = [c for c in claims if c["type"] == "percentage"]
    distance_claims = [c for c in claims if c["type"] == "distance_km"]
    bhk_claims = [c for c in claims if c["type"] == "bhk"]

    assert len(price_claims) > 0, "Should find price claims"
    assert len(pct_claims) > 0, "Should find percentage claims"
    assert len(bhk_claims) > 0, "Should find BHK claims"
    print(f"  ✓ Price claims: {len(price_claims)}")
    print(f"  ✓ Percentage claims: {len(pct_claims)}")
    print(f"  ✓ Distance claims: {len(distance_claims)}")
    print(f"  ✓ BHK claims: {len(bhk_claims)}")

    return True


def test_tool_value_extraction():
    """Test extraction of reference values from tool outputs."""
    print("\n--- Test 2: Tool Value Extraction ---")

    tool_outputs = {
        "cagr": {
            "cagr": 0.0845,
            "cagr_percent": 8.45,
            "beginning_value": 5000,
            "ending_value": 7500,
        },
        "liquidity": {
            "liquidity_score": 0.72,
            "sale_ratio": 0.65,
        },
        "properties": [
            {"price": 8500000, "price_per_sqft": 6500},
            {"price": 7200000, "price_per_sqft": 5800},
        ],
    }

    extracted = extract_tool_values(tool_outputs)
    assert len(extracted) > 0
    print(f"  Extracted {len(extracted)} value groups")

    flat = flatten_tool_values(tool_outputs)
    assert 0.0845 in flat or any(abs(v - 0.0845) < 0.001 for v in flat), "CAGR should be in flat values"
    assert 8500000 in flat or any(abs(v - 8500000) < 1 for v in flat), "Price should be in flat values"
    print(f"  ✓ Flat values: {len(flat)} unique values (incl. transformations)")

    return True


def test_clean_narrative():
    """Test judge passes a clean narrative that matches tool outputs."""
    print("\n--- Test 3: Clean Narrative (No Hallucination) ---")

    judge = HallucinationJudge()

    tool_outputs = {
        "cagr": {"cagr": 0.0845, "cagr_percent": 8.45},
        "properties": [
            {"price": 8500000, "price_per_sqft": 6500, "bedrooms": 3}
        ],
    }

    narrative = (
        "Based on our CAGR analysis, the locality shows a growth rate of 8.45%. "
        "The 3 BHK property is priced at ₹85,00,000 with a rate of 6,500 per sq ft."
    )

    verdict = judge.verify(narrative, tool_outputs)

    assert verdict.verdict == "clean", f"Expected clean, got {verdict.verdict}"
    assert not verdict.mismatch_detected
    print(f"  ✓ Verdict: {verdict.verdict}")
    print(f"  ✓ Claims: {verdict.total_claims} total, {verdict.verified_claims} verified")
    print(f"  ✓ Confidence: {verdict.confidence}")

    return True


def test_hallucinated_narrative():
    """Test judge catches a hallucinated narrative with fabricated numbers."""
    print("\n--- Test 4: Hallucinated Narrative (Fabricated Numbers) ---")

    judge = HallucinationJudge()

    # Tool says CAGR is 8.45%, but narrative claims 15.2%
    tool_outputs = {
        "cagr": {"cagr": 0.0845, "cagr_percent": 8.45},
        "properties": [
            {"price": 8500000, "price_per_sqft": 6500}
        ],
    }

    narrative = (
        "The locality shows an impressive CAGR of 15.2% over the last 5 years. "
        "Properties are priced around ₹1,20,00,000 with rates of 9,800 per sq ft. "
        "The liquidity score is 0.89 indicating a highly liquid market."
    )

    verdict = judge.verify(narrative, tool_outputs)

    assert verdict.mismatch_detected, "Should detect mismatches"
    assert verdict.verdict in ("warning", "hallucination"), f"Expected warning/hallucination, got {verdict.verdict}"
    assert verdict.unverified_claims > 0
    print(f"  ✓ Verdict: {verdict.verdict}")
    print(f"  ✓ Mismatches detected: {len(verdict.mismatches)}")
    for m in verdict.mismatches:
        print(f"    - Claimed {m['raw_text']} (value: {m['claimed_value']}), "
              f"closest ref: {m.get('closest_reference', 'N/A')}")
    print(f"  ✓ Action: {verdict.action_taken}")

    return True


def test_response_sanitizer_clean():
    """Test sanitizer passes clean responses through."""
    print("\n--- Test 5: Response Sanitizer (Clean) ---")

    clean_verdict = HallucinationVerdict(verdict="clean", mismatch_detected=False)
    narrative = "The CAGR is 8.45%. The property costs ₹85,00,000."

    result = ResponseSanitizer.sanitize(narrative, clean_verdict)
    assert result == narrative, "Clean response should pass through unchanged"
    print(f"  ✓ Clean response passed through unchanged")

    return True


def test_response_sanitizer_warning():
    """Test sanitizer flags warned responses."""
    print("\n--- Test 6: Response Sanitizer (Warning) ---")

    warning_verdict = HallucinationVerdict(
        verdict="warning",
        mismatch_detected=True,
        mismatches=[{"raw_text": "15.2%", "claimed_value": 15.2}],
    )
    narrative = "The CAGR is 15.2% and prices are at ₹85,00,000."

    result = ResponseSanitizer.sanitize(narrative, warning_verdict)
    assert "unverified" in result.lower(), "Should flag unverified claims"
    assert "⚠️" in result, "Should include warning disclaimer"
    print(f"  ✓ Warning response flagged with disclaimer")

    return True


def test_response_sanitizer_rejection():
    """Test sanitizer rejects hallucinated responses."""
    print("\n--- Test 7: Response Sanitizer (Rejection) ---")

    hallucination_verdict = HallucinationVerdict(
        verdict="hallucination",
        mismatch_detected=True,
        action_taken="rejected",
    )
    narrative = "The CAGR is 25.3% and the market is booming."

    result = ResponseSanitizer.sanitize(narrative, hallucination_verdict)
    assert "cannot provide" in result.lower() or "apologize" in result.lower(), \
        "Should reject with apology"
    assert narrative not in result, "Original hallucinated text should not appear"
    print(f"  ✓ Hallucinated response rejected")
    print(f"  ✓ Replacement: {result[:80]}...")

    return True


def test_system_prompts():
    """Test system prompts contain required constraints."""
    print("\n--- Test 8: System Prompt Constraints ---")

    required_phrases = [
        "NEVER fabricate",
        "tool outputs",
        "Data not available",
        "NEVER extrapolate",
    ]

    for phrase in required_phrases:
        assert phrase in SYSTEM_PROMPT_BASE, f"Missing: '{phrase}'"
        print(f"  ✓ Contains: '{phrase}'")

    assert "cagr_microservice" in SYSTEM_PROMPT_FINANCIAL, "Financial prompt missing CAGR reference"
    assert "liquidity_microservice" in SYSTEM_PROMPT_FINANCIAL, "Financial prompt missing liquidity reference"
    print(f"  ✓ Financial prompt references all microservices")

    return True


def test_tool_definitions():
    """Test tool definitions are complete and well-formed."""
    print("\n--- Test 9: Tool Definitions ---")

    assert len(TOOL_DEFINITIONS) == 6, f"Expected 6 tools, got {len(TOOL_DEFINITIONS)}"

    expected_tools = {
        "compute_cagr", "compute_liquidity", "compute_absorption",
        "compute_distance_decay", "compute_forecast", "compute_risk",
    }

    actual_tools = {t["function"]["name"] for t in TOOL_DEFINITIONS}
    assert expected_tools == actual_tools, f"Tool mismatch: {expected_tools - actual_tools}"

    for tool in TOOL_DEFINITIONS:
        func = tool["function"]
        assert "description" in func, f"Missing description for {func['name']}"
        assert "USE THIS" in func["description"], f"Tool {func['name']} must include 'USE THIS' instruction"
        assert "parameters" in func, f"Missing parameters for {func['name']}"
        print(f"  ✓ {func['name']}: well-formed with USE THIS instruction")

    return True


def test_judge_with_retrieved_data():
    """Test judge cross-references against database records too."""
    print("\n--- Test 10: Judge with Retrieved Data ---")

    judge = HallucinationJudge()

    tool_outputs = {"cagr": {"cagr_percent": 8.45}}

    retrieved_data = [
        {"title": "3BHK Apartment", "price": 7500000, "bedrooms": 3, "locality": "Adyar"},
        {"title": "2BHK Apartment", "price": 5200000, "bedrooms": 2, "locality": "T Nagar"},
    ]

    # Narrative mentions prices from retrieved data — should be clean
    narrative = (
        "I found a 3 BHK apartment in Adyar priced at ₹75,00,000. "
        "CAGR for the area is 8.45%."
    )

    verdict = judge.verify(narrative, tool_outputs, retrieved_data)
    assert verdict.verdict == "clean", f"Expected clean, got {verdict.verdict}"
    print(f"  ✓ Verdict: {verdict.verdict}")
    print(f"  ✓ Cross-referenced against {len(retrieved_data)} DB records")

    return True


def test_deterministic_judge():
    """Test that the judge produces identical results for identical inputs."""
    print("\n--- Test 11: Judge Determinism ---")

    tool_outputs = {
        "cagr": {"cagr": 0.0845, "cagr_percent": 8.45},
        "properties": [{"price": 8500000}],
    }
    narrative = "The CAGR is 8.45% and price is ₹85,00,000. Also saw 15.2% growth."

    results = []
    for _ in range(10):
        judge = HallucinationJudge()
        verdict = judge.verify(narrative, tool_outputs)
        results.append((verdict.verdict, verdict.total_claims, verdict.verified_claims, verdict.unverified_claims))

    # All runs should produce identical verdicts
    assert len(set(results)) == 1, f"Judge not deterministic: {set(results)}"
    print(f"  ✓ 10 runs identical: {results[0]}")

    return True


if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 5 VALIDATION — ZERO-HALLUCINATION ENFORCEMENT")
    print("=" * 60)

    tests = [
        ("Numeric Extraction", test_numeric_extraction),
        ("Tool Value Extraction", test_tool_value_extraction),
        ("Clean Narrative", test_clean_narrative),
        ("Hallucinated Narrative", test_hallucinated_narrative),
        ("Sanitizer Clean", test_response_sanitizer_clean),
        ("Sanitizer Warning", test_response_sanitizer_warning),
        ("Sanitizer Rejection", test_response_sanitizer_rejection),
        ("System Prompts", test_system_prompts),
        ("Tool Definitions", test_tool_definitions),
        ("Judge + DB Records", test_judge_with_retrieved_data),
        ("Judge Determinism", test_deterministic_judge),
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

    # Save results
    state_dir = os.path.join(os.path.dirname(__file__), "..", "state")
    os.makedirs(state_dir, exist_ok=True)
    with open(os.path.join(state_dir, "phase5_validation.json"), "w") as f:
        json.dump({"tests": results, "status": overall}, f, indent=2)

    if not all_pass:
        sys.exit(1)
