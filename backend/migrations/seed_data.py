"""
Seed Migration Script — Moves hardcoded dicts → Supabase tables.

Run: python -m migrations.seed_data

This generates and executes INSERT statements to populate:
  1. guideline_values (from TN_GUIDELINE_VALUES_2024)
  2. locality_metadata (from ZONE_TIERS + LOCALITY_FEATURE_MAP + INFRASTRUCTURE_PREMIUMS)
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import get_db_context
from sqlalchemy import text


# ─────────────────────────────────────────────────────────────────────
# SOURCE DATA: Copied from govt_data_service.py (to be deprecated)
# ─────────────────────────────────────────────────────────────────────

TN_GUIDELINE_VALUES_2024 = {
    "chennai": {
        "anna_nagar": {"min": 8500, "max": 12000}, "adyar": {"min": 9000, "max": 14000},
        "t_nagar": {"min": 10000, "max": 18000}, "velachery": {"min": 5500, "max": 8500},
        "sholinganallur": {"min": 4500, "max": 7000}, "perambur": {"min": 3500, "max": 5500},
        "ambattur": {"min": 3000, "max": 5000}, "porur": {"min": 4500, "max": 7000},
        "pallavaram": {"min": 3500, "max": 5500}, "chromepet": {"min": 3500, "max": 5500},
        "tambaram": {"min": 2800, "max": 4500}, "avadi": {"min": 1800, "max": 3200},
        "thiruvallur": {"min": 1200, "max": 2500}, "poonamallee": {"min": 2500, "max": 4000},
        "sriperumbudur": {"min": 1500, "max": 2800}, "guduvanchery": {"min": 2000, "max": 3500},
        "perungalathur": {"min": 2500, "max": 4000}, "medavakkam": {"min": 4000, "max": 6500},
        "urapakkam": {"min": 2200, "max": 3800}, "vandalur": {"min": 1800, "max": 3200},
        "kelambakkam": {"min": 2800, "max": 4500}, "omr": {"min": 4000, "max": 7000},
        "ecr": {"min": 5000, "max": 9000}, "injambakkam": {"min": 5000, "max": 8000},
        "nungambakkam": {"min": 9500, "max": 15000}, "mylapore": {"min": 7500, "max": 12000},
        "kodambakkam": {"min": 6000, "max": 9500}, "ashok_nagar": {"min": 6500, "max": 10000},
        "besant_nagar": {"min": 8000, "max": 13000}, "thiruvanmiyur": {"min": 6000, "max": 9500},
        "perungudi": {"min": 4500, "max": 7500}, "siruseri": {"min": 3000, "max": 5000},
        "navalur": {"min": 3500, "max": 5500}, "madambakkam": {"min": 2500, "max": 4000},
        "kovilambakkam": {"min": 3500, "max": 5500}, "selaiyur": {"min": 2800, "max": 4500},
        "irumbuliyur": {"min": 2000, "max": 3500}, "kilkattalai": {"min": 2200, "max": 3800},
        "virugambakkam": {"min": 5000, "max": 7500}, "koyambedu": {"min": 5500, "max": 8500},
        "mogappair": {"min": 4500, "max": 7000}, "kolathur": {"min": 3500, "max": 5500},
        "villivakkam": {"min": 3500, "max": 5500}, "royapuram": {"min": 3000, "max": 5000},
        "tondiarpet": {"min": 3000, "max": 4800}, "manali": {"min": 2000, "max": 3500},
        "tiruvottiyur": {"min": 2500, "max": 4000},
    },
    "coimbatore": {
        "rs_puram": {"min": 4000, "max": 7000}, "gandhipuram": {"min": 5000, "max": 9000},
        "peelamedu": {"min": 3500, "max": 6000}, "saibaba_colony": {"min": 3500, "max": 6000},
        "singanallur": {"min": 2500, "max": 4500}, "race_course": {"min": 4500, "max": 8000},
        "podanur": {"min": 2000, "max": 3500}, "kuniyamuthur": {"min": 1800, "max": 3000},
        "ganapathy": {"min": 2800, "max": 4500}, "vadavalli": {"min": 2500, "max": 4000},
    },
    "madurai": {
        "anna_nagar_madurai": {"min": 2500, "max": 4500}, "ss_colony": {"min": 3000, "max": 5000},
        "tallakulam": {"min": 3500, "max": 6000}, "koodal_nagar": {"min": 2000, "max": 3500},
        "bypass_road": {"min": 1800, "max": 3200},
    },
    "trichy": {
        "thillai_nagar": {"min": 2500, "max": 4500}, "cantonment": {"min": 2000, "max": 4000},
        "ariyamangalam": {"min": 1500, "max": 2800}, "k_k_nagar_trichy": {"min": 2000, "max": 3500},
        "srirangam": {"min": 1800, "max": 3200}, "woraiyur": {"min": 1500, "max": 2800},
    },
    "salem": {
        "fairlands": {"min": 1800, "max": 3500}, "alagapuram": {"min": 1500, "max": 2800},
        "five_roads": {"min": 2000, "max": 3800}, "kitchipalayam": {"min": 1200, "max": 2500},
    },
    "tirunelveli": {
        "palayamkottai": {"min": 1500, "max": 3000}, "melapalayam": {"min": 1200, "max": 2500},
        "vannarpettai": {"min": 1000, "max": 2000},
    },
    "vellore": {
        "katpadi": {"min": 1200, "max": 2500}, "sathuvachari": {"min": 1500, "max": 2800},
        "gandhi_nagar_vellore": {"min": 1800, "max": 3200},
    },
    "erode": {"erode_town": {"min": 1500, "max": 3000}, "perundurai": {"min": 800, "max": 1800}},
    "tiruppur": {"tiruppur_town": {"min": 1800, "max": 3500}, "palladam": {"min": 800, "max": 1800}},
    "karur": {"karur_town": {"min": 1200, "max": 2500}},
    "kancheepuram": {
        "kancheepuram_town": {"min": 1500, "max": 3000}, "chengalpattu": {"min": 2000, "max": 3500},
        "maraimalai_nagar": {"min": 2500, "max": 4000},
    },
    "puducherry": {
        "white_town": {"min": 4000, "max": 8000}, "reddiarpalayam": {"min": 2500, "max": 4500},
        "villianur": {"min": 1500, "max": 3000},
    },
}

ZONE_TIERS = {
    "anna_nagar": "A", "adyar": "A", "t_nagar": "A", "nungambakkam": "A",
    "mylapore": "A", "besant_nagar": "A", "ashok_nagar": "A",
    "velachery": "A", "kodambakkam": "A", "thiruvanmiyur": "A", "ecr": "A",
    "sholinganallur": "B", "perambur": "B", "porur": "B", "chromepet": "B",
    "pallavaram": "B", "medavakkam": "B", "omr": "B", "perungudi": "B",
    "virugambakkam": "B", "koyambedu": "B", "mogappair": "B", "kolathur": "B",
    "villivakkam": "B", "navalur": "B", "siruseri": "B", "kelambakkam": "B",
    "kovilambakkam": "B", "injambakkam": "B",
    "ambattur": "B", "tambaram": "B", "selaiyur": "B", "kilkattalai": "B",
    "madambakkam": "B", "perungalathur": "B",
    "avadi": "C", "poonamallee": "C", "guduvanchery": "C", "urapakkam": "C",
    "vandalur": "C", "irumbuliyur": "C", "royapuram": "C", "tondiarpet": "C",
    "manali": "C", "tiruvottiyur": "C",
    "thiruvallur": "D", "sriperumbudur": "D",
}

LOCALITY_FEATURES = {
    "anna_nagar": ["Metro Station", "Commercial Hub", "Residential Premium"],
    "adyar": ["Educational Hub", "Residential Premium", "River Proximity"],
    "t_nagar": ["Commercial Hub", "Metro Station", "High Density"],
    "velachery": ["Metro Station", "IT Proximity", "Residential"],
    "sholinganallur": ["IT Corridor", "OMR", "Corporate Hub"],
    "porur": ["Hospital Hub", "Highway Access", "Growing Corridor"],
    "omr": ["IT Corridor", "Tech Park", "SEZ Proximity"],
    "ecr": ["Beach Proximity", "Tourism", "Lifestyle"],
    "tambaram": ["Railway Junction", "Educational", "Suburban"],
    "chromepet": ["Railway Hub", "Industrial Proximity", "Suburban"],
}

INFRA_PREMIUMS = {
    "anna_nagar": {"metro": 0.12, "it_corridor": 0.0, "highway": 0.05, "commercial": 0.10},
    "adyar": {"metro": 0.0, "it_corridor": 0.0, "highway": 0.0, "commercial": 0.08},
    "t_nagar": {"metro": 0.10, "it_corridor": 0.0, "highway": 0.0, "commercial": 0.15},
    "velachery": {"metro": 0.10, "it_corridor": 0.05, "highway": 0.0, "commercial": 0.05},
    "sholinganallur": {"metro": 0.0, "it_corridor": 0.18, "highway": 0.0, "commercial": 0.08},
    "porur": {"metro": 0.0, "it_corridor": 0.0, "highway": 0.08, "commercial": 0.05},
    "omr": {"metro": 0.0, "it_corridor": 0.20, "highway": 0.0, "commercial": 0.10},
}


async def seed_guideline_values():
    """Insert guideline values into guideline_values table."""
    print("Seeding guideline_values...")
    count = 0
    async with get_db_context() as session:
        for district, localities in TN_GUIDELINE_VALUES_2024.items():
            for locality, vals in localities.items():
                await session.execute(
                    text("""
                        INSERT INTO guideline_values (district, locality, asset_type, min_per_sqft, max_per_sqft, effective_date)
                        VALUES (:district, :locality, 'land', :min_val, :max_val, '2024-07-01')
                        ON CONFLICT (district, locality, asset_type, effective_date) DO UPDATE
                        SET min_per_sqft = EXCLUDED.min_per_sqft, max_per_sqft = EXCLUDED.max_per_sqft
                    """),
                    {"district": district, "locality": locality,
                     "min_val": vals["min"], "max_val": vals["max"]}
                )
                count += 1
    print(f"  ✅ Inserted {count} guideline value records")


async def seed_locality_metadata():
    """Insert locality metadata into locality_metadata table."""
    print("Seeding locality_metadata...")
    count = 0
    async with get_db_context() as session:
        # Build combined set of all localities from all sources
        all_localities = set()
        for district, locs in TN_GUIDELINE_VALUES_2024.items():
            for loc in locs:
                all_localities.add((district, loc))

        for district, locality in all_localities:
            zone = ZONE_TIERS.get(locality, "C")
            features = LOCALITY_FEATURES.get(locality, [])
            infra = INFRA_PREMIUMS.get(locality, {})
            pop_tier = "metro" if district == "chennai" else "urban"

            import json as _json
            await session.execute(
                text("""
                    INSERT INTO locality_metadata (locality, district, zone_tier, population_tier, features, infra_premium)
                    VALUES (:locality, :district, :zone, :pop_tier, :features, CAST(:infra AS jsonb))
                    ON CONFLICT (locality, district) DO UPDATE
                    SET zone_tier = EXCLUDED.zone_tier,
                        population_tier = EXCLUDED.population_tier,
                        features = EXCLUDED.features,
                        infra_premium = EXCLUDED.infra_premium,
                        updated_at = NOW()
                """),
                {
                    "locality": locality, "district": district,
                    "zone": zone, "pop_tier": pop_tier,
                    "features": features,
                    "infra": _json.dumps(infra) if infra else "{}",
                }
            )
            count += 1
    print(f"  ✅ Inserted {count} locality metadata records")


async def seed_sample_transactions():
    """Insert sample registry transactions for testing.
    In production, these come from actual tnreginet data."""
    print("Seeding sample registry_transactions...")
    count = 0

    # Sample transactions — demonstrating what real data looks like
    samples = [
        # Anna Nagar — 5 transactions (enables IQR)
        ("chennai", "anna_nagar", "land", 2400, 2_16_00_000, "2024-08-15", "A"),
        ("chennai", "anna_nagar", "land", 1200, 1_20_00_000, "2024-09-10", "A"),
        ("chennai", "anna_nagar", "land", 2400, 2_40_00_000, "2024-10-20", "A"),
        ("chennai", "anna_nagar", "land", 1800, 1_62_00_000, "2024-11-05", "A"),
        ("chennai", "anna_nagar", "land", 2400, 2_64_00_000, "2025-01-12", "A"),
        # Velachery — 3 transactions (Min/Max/Median)
        ("chennai", "velachery", "land", 2400, 1_44_00_000, "2024-08-20", "A"),
        ("chennai", "velachery", "land", 1200, 84_00_000, "2024-10-01", "A"),
        ("chennai", "velachery", "land", 2400, 1_68_00_000, "2025-02-15", "A"),
        # Porur — 2 transactions (Min/Max only)
        ("chennai", "porur", "land", 2400, 1_20_00_000, "2024-09-20", "B"),
        ("chennai", "porur", "land", 1200, 72_00_000, "2025-01-05", "B"),
        # Tambaram — 1 transaction (observed price only)
        ("chennai", "tambaram", "land", 2400, 84_00_000, "2024-12-10", "B"),
    ]

    async with get_db_context() as session:
        for district, locality, asset, area, sale_val, reg_date, zone in samples:
            await session.execute(
                text("""
                    INSERT INTO registry_transactions
                        (district, locality, asset_type, area_sqft, sale_value, registration_date, zone_tier, data_source)
                    VALUES (:district, :locality, :asset, :area, :sale_val, :reg_date, :zone, 'sample_seed')
                """),
                {
                    "district": district, "locality": locality,
                    "asset": asset, "area": area, "sale_val": sale_val,
                    "reg_date": reg_date, "zone": zone,
                }
            )
            count += 1
    print(f"  ✅ Inserted {count} sample transaction records")


async def verify_seed():
    """Verify seeded data."""
    print("\nVerifying seed data...")
    async with get_db_context() as session:
        gv = await session.execute(text("SELECT COUNT(*) FROM guideline_values"))
        print(f"  guideline_values: {gv.scalar()} rows")

        lm = await session.execute(text("SELECT COUNT(*) FROM locality_metadata"))
        print(f"  locality_metadata: {lm.scalar()} rows")

        rt = await session.execute(text("SELECT COUNT(*) FROM registry_transactions"))
        print(f"  registry_transactions: {rt.scalar()} rows")

        # Test valuation stats
        stats = await session.execute(text("""
            SELECT * FROM compute_valuation_stats('anna_nagar', 'land', 24)
        """))
        row = stats.fetchone()
        if row:
            print(f"\n  Anna Nagar valuation stats:")
            print(f"    Comparable count: {row[0]}")
            print(f"    Min: {row[1]}, Max: {row[2]}, Median: {row[3]}")
            print(f"    Q1: {row[4]}, Q3: {row[5]}")
            print(f"    StdDev: {row[6]}, CoV: {row[7]}")
            print(f"    Date range: {row[8]} to {row[9]}")


async def main():
    print("=" * 60)
    print("PURITYPROP RAG SEED MIGRATION")
    print("=" * 60)

    await seed_guideline_values()
    await seed_locality_metadata()
    await seed_sample_transactions()
    await verify_seed()

    print("\n" + "=" * 60)
    print("SEED COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
