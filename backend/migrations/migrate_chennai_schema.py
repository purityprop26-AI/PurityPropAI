"""
PurityProp — Chennai ETL: Database Schema Migration
=====================================================

Creates new normalized tables for the Chennai ETL pipeline:
  - cities
  - regions
  - localities
  - property_price_trends
  - locality_rag_summaries

Seeds cities and regions for all 4 districts.

Run: python -m migrations.migrate_chennai_schema
"""

from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from sqlalchemy import text
from app.core.database import get_db_context


# ─────────────────────────────────────────────────────────────────────
# SCHEMA DDL
# ─────────────────────────────────────────────────────────────────────

SCHEMA_SQL = """
-- Cities
CREATE TABLE IF NOT EXISTS cities (
    city_id     SERIAL PRIMARY KEY,
    city_name   VARCHAR(100) NOT NULL UNIQUE,
    state       VARCHAR(100) NOT NULL DEFAULT 'Tamil Nadu',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Regions (sub-areas within a city)
CREATE TABLE IF NOT EXISTS regions (
    region_id   SERIAL PRIMARY KEY,
    city_id     INTEGER NOT NULL REFERENCES cities(city_id) ON DELETE CASCADE,
    region_name VARCHAR(150) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (city_id, region_name)
);

-- Localities (granular areas within a region)
CREATE TABLE IF NOT EXISTS localities (
    locality_id   SERIAL PRIMARY KEY,
    region_id     INTEGER NOT NULL REFERENCES regions(region_id) ON DELETE CASCADE,
    locality_name VARCHAR(200) NOT NULL,
    zone_tier     VARCHAR(5),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (region_id, locality_name)
);

-- Property Price Trends (year-wise structured pricing)
CREATE TABLE IF NOT EXISTS property_price_trends (
    id                SERIAL PRIMARY KEY,
    locality_id       INTEGER NOT NULL REFERENCES localities(locality_id) ON DELETE CASCADE,
    year              INTEGER NOT NULL CHECK (year BETWEEN 2020 AND 2035),
    land_price_min    NUMERIC(12,2),
    land_price_max    NUMERIC(12,2),
    land_price_avg    NUMERIC(12,2),
    apartment_price   NUMERIC(12,2),
    market_price      NUMERIC(12,2),
    guideline_price   NUMERIC(12,2),
    ground_value      NUMERIC(14,2),
    negotiation_min   NUMERIC(5,2),
    negotiation_max   NUMERIC(5,2),
    data_type         VARCHAR(20) NOT NULL DEFAULT 'observed'
                      CHECK (data_type IN ('observed', 'forecast')),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (locality_id, year, data_type)
);

-- Locality RAG Summaries (for vector search)
CREATE TABLE IF NOT EXISTS locality_rag_summaries (
    id              SERIAL PRIMARY KEY,
    locality_name   VARCHAR(200) NOT NULL,
    region          VARCHAR(150),
    city            VARCHAR(100),
    text_summary    TEXT NOT NULL,
    embedding       vector(384),
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (locality_name, city)
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_ppt_locality_year ON property_price_trends(locality_id, year);
CREATE INDEX IF NOT EXISTS idx_ppt_data_type ON property_price_trends(data_type);
CREATE INDEX IF NOT EXISTS idx_localities_name ON localities(locality_name);
CREATE INDEX IF NOT EXISTS idx_regions_city ON regions(city_id);
CREATE INDEX IF NOT EXISTS idx_rag_summaries_locality ON locality_rag_summaries(locality_name);
"""


# ─────────────────────────────────────────────────────────────────────
# SEED DATA
# ─────────────────────────────────────────────────────────────────────

CITIES = [
    "Chennai",
    "Coimbatore",
    "Salem",
    "Madurai",
]

REGIONS = {
    "Chennai": [
        "South Chennai",
        "North Chennai",
        "Central Chennai",
        "East Chennai",
        "West Chennai",
    ],
    "Coimbatore": [
        "Coimbatore Central",
        "Coimbatore South",
        "Coimbatore North",
        "Coimbatore East",
        "Coimbatore West",
    ],
    "Salem": [
        "Salem City",
        "Salem East",
        "Salem West",
    ],
    "Madurai": [
        "Madurai Central",
        "Madurai South",
        "Madurai North",
        "Madurai East",
        "Madurai West",
    ],
}

# Chennai region → locality mapping (used during ingestion)
CHENNAI_REGION_MAP = {
    "South Chennai": [
        "thoraipakkam", "sholinganallur", "perungudi", "velachery",
        "adambakkam", "nanganallur", "pallikaranai", "medavakkam",
        "madipakkam", "adyar", "besant_nagar", "thiruvanmiyur",
        "guindy", "saidapet", "chromepet", "tambaram", "pallavaram",
        "selaiyur", "kovilambakkam", "madambakkam", "mambakkam",
        "guduvanchery", "urapakkam", "vandalur", "irumbuliyur",
        "siruseri", "navalur", "karapakkam", "padur", "kelambakkam",
        "oragadam", "maraimalai_nagar",
    ],
    "North Chennai": [
        "royapuram", "tondiarpet", "manali", "tiruvottiyur",
        "washermanpet", "sowcarpet", "george_town", "harbour",
        "ennore", "minjur", "madhavaram", "puzhal", "kolathur",
        "villivakkam", "perambur", "ayanavaram", "padi",
    ],
    "Central Chennai": [
        "anna_nagar", "t_nagar", "nungambakkam", "mylapore",
        "kodambakkam", "ashok_nagar", "west_mambalam", "chetpet",
        "kilpauk", "egmore", "teynampet", "alwarpet", "mandaveli",
        "raja_annamalai_puram", "gopalapuram",
    ],
    "East Chennai": [
        "omr", "ecr", "palavakkam", "neelankarai", "injambakkam",
        "uthandi", "kovalam", "kottivakkam", "kanathur",
        "semmencherry", "sholinganallur",
    ],
    "West Chennai": [
        "porur", "ramapuram", "valasaravakkam", "virugambakkam",
        "mogappair", "ambattur", "avadi", "poonamallee",
        "kundrathur", "mangadu", "maduravoyal", "nerkundram",
        "koyambedu", "vadapalani", "ashok_nagar",
    ],
}


async def create_schema():
    """Execute DDL to create new tables."""
    print("Creating schema...")
    async with get_db_context() as session:
        # Execute each statement separately
        for stmt in SCHEMA_SQL.split(';'):
            stmt = stmt.strip()
            if stmt and not stmt.startswith('--'):
                try:
                    await session.execute(text(stmt))
                except Exception as e:
                    # Skip if already exists
                    if 'already exists' not in str(e).lower():
                        print(f"  Warning: {e}")
    print("  ✅ Schema created")


async def seed_cities_and_regions():
    """Seed cities and regions."""
    print("Seeding cities and regions...")
    async with get_db_context() as session:
        for city_name in CITIES:
            try:
                await session.execute(
                    text("""
                        INSERT INTO cities (city_name) VALUES (:name)
                        ON CONFLICT (city_name) DO NOTHING
                    """),
                    {"name": city_name}
                )
            except Exception as e:
                print(f"  City insert warning: {e}")

        # Get city IDs
        result = await session.execute(text("SELECT city_id, city_name FROM cities"))
        city_map = {row[1]: row[0] for row in result.fetchall()}

        for city_name, region_list in REGIONS.items():
            city_id = city_map.get(city_name)
            if not city_id:
                print(f"  City '{city_name}' not found, skipping regions")
                continue
            for region_name in region_list:
                try:
                    await session.execute(
                        text("""
                            INSERT INTO regions (city_id, region_name)
                            VALUES (:city_id, :name)
                            ON CONFLICT (city_id, region_name) DO NOTHING
                        """),
                        {"city_id": city_id, "name": region_name}
                    )
                except Exception as e:
                    print(f"  Region insert warning: {e}")

    print("  ✅ Cities and regions seeded")


async def verify_schema():
    """Verify tables exist and have data."""
    print("\nVerification:")
    async with get_db_context() as session:
        for table in ['cities', 'regions', 'localities', 'property_price_trends', 'locality_rag_summaries']:
            try:
                r = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                print(f"  {table}: {r.scalar()} rows")
            except Exception as e:
                print(f"  {table}: ERROR - {e}")


async def main():
    print("=" * 60)
    print("PURITYPROP — CHENNAI ETL SCHEMA MIGRATION")
    print("=" * 60)

    await create_schema()
    await seed_cities_and_regions()
    await verify_schema()

    print("\n" + "=" * 60)
    print("MIGRATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
