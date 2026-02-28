
import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.core.hallucination_adapter import HallucinationGuard

async def test_hallucination_detection():
    guard = HallucinationGuard()
    
    # Mock data (Ground Truth)
    source_data = [
        {"title": "Adyar Villa", "price": 15501, "carpet_area_sqft": 2053, "locality": "Adyar"}
    ]
    
    # Case 1: Truthful Summary
    truth_summary = "There is a villa in Adyar for 15,501 with 2053 sqft area."
    verified_tx, metadata = guard.verify(truth_summary, source_data)
    print(f"TRUTH TEST: Passed={metadata['passed']}, Verdict={metadata['verdict']}")
    
    # Case 2: Fabricated Number (Price)
    fake_summary = "There is a villa in Adyar for 99,000 with 2053 sqft area."
    sanitized_tx, metadata = guard.verify(fake_summary, source_data)
    print(f"FAKE PRICE TEST: Passed={metadata['passed']}, Verdict={metadata['verdict']}")
    print(f"Sanitized: {sanitized_tx[:100]}...")

    # Case 3: Fabricated Area
    fake_area = "There is a villa in Adyar for 15,501 with 5000 sqft area."
    _, metadata = guard.verify(fake_area, source_data)
    print(f"FAKE AREA TEST: Passed={metadata['passed']}, Verdict={metadata['verdict']}")

if __name__ == "__main__":
    asyncio.run(test_hallucination_detection())
