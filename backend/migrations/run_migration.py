"""Run simplified SQL migration to create RAG tables."""
import asyncio
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from app.core.database import get_db_context
from sqlalchemy import text

STATEMENTS = [
    "CREATE EXTENSION IF NOT EXISTS vector",
    "CREATE EXTENSION IF NOT EXISTS pg_trgm",
    # registry_transactions
    """CREATE TABLE IF NOT EXISTS registry_transactions (
        id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
        district TEXT NOT NULL,
        locality TEXT NOT NULL,
        micro_market TEXT,
        block TEXT,
        pin_code TEXT,
        asset_type TEXT NOT NULL CHECK (asset_type IN ('land','apartment','villa','commercial')),
        area_sqft NUMERIC(12,2) NOT NULL CHECK (area_sqft > 0),
        sale_value NUMERIC(15,2) NOT NULL CHECK (sale_value > 0),
        price_per_sqft NUMERIC(10,2) GENERATED ALWAYS AS (sale_value / NULLIF(area_sqft, 0)) STORED,
        guideline_value NUMERIC(10,2),
        registration_date DATE NOT NULL,
        document_number TEXT,
        sub_registrar TEXT,
        geo_hash TEXT,
        zone_tier TEXT CHECK (zone_tier IS NULL OR zone_tier IN ('A','B','C','D')),
        data_source TEXT NOT NULL DEFAULT 'tnreginet',
        source_confidence TEXT NOT NULL DEFAULT 'authoritative' CHECK (source_confidence IN ('authoritative','calibration','secondary')),
        road_width_ft NUMERIC(6,2),
        zoning TEXT,
        amenities JSONB DEFAULT '{}',
        embedding vector(384),
        is_outlier BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    )""",
    # guideline_values
    """CREATE TABLE IF NOT EXISTS guideline_values (
        id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
        district TEXT NOT NULL,
        locality TEXT NOT NULL,
        zone_number TEXT,
        asset_type TEXT NOT NULL CHECK (asset_type IN ('land','apartment','villa','commercial')),
        min_per_sqft NUMERIC(10,2) NOT NULL,
        max_per_sqft NUMERIC(10,2) NOT NULL,
        effective_date DATE NOT NULL,
        revision_cycle TEXT DEFAULT 'annual',
        source_url TEXT DEFAULT 'https://tnreginet.gov.in',
        created_at TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE (district, locality, asset_type, effective_date)
    )""",
    # web_collected_prices
    """CREATE TABLE IF NOT EXISTS web_collected_prices (
        id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
        district TEXT NOT NULL,
        locality TEXT NOT NULL,
        asset_type TEXT NOT NULL,
        avg_price_sqft NUMERIC(10,2) NOT NULL,
        min_price_sqft NUMERIC(10,2),
        max_price_sqft NUMERIC(10,2),
        sample_count INT,
        source_portal TEXT NOT NULL,
        collection_date DATE NOT NULL,
        collector TEXT,
        registry_divergence_pct NUMERIC(8,4),
        is_validated BOOLEAN DEFAULT FALSE,
        validation_note TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )""",
    # locality_metadata
    """CREATE TABLE IF NOT EXISTS locality_metadata (
        id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
        locality TEXT NOT NULL,
        district TEXT NOT NULL,
        zone_tier TEXT NOT NULL CHECK (zone_tier IN ('A','B','C','D')),
        population_tier TEXT CHECK (population_tier IS NULL OR population_tier IN ('metro','urban','semi_urban','rural')),
        metro_proximity_km NUMERIC(6,2),
        it_corridor BOOLEAN DEFAULT FALSE,
        highway_access TEXT[],
        features TEXT[],
        infra_premium JSONB DEFAULT '{}',
        updated_at TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE (locality, district)
    )""",
    # Indexes
    "CREATE INDEX IF NOT EXISTS idx_rt_lookup ON registry_transactions (locality, asset_type, registration_date DESC)",
    "CREATE INDEX IF NOT EXISTS idx_rt_clean ON registry_transactions (locality, asset_type, price_per_sqft) WHERE is_outlier = FALSE",
    "CREATE INDEX IF NOT EXISTS idx_rt_district ON registry_transactions (district, locality)",
    "CREATE INDEX IF NOT EXISTS idx_gv_lookup ON guideline_values (district, locality, asset_type, effective_date DESC)",
    "CREATE INDEX IF NOT EXISTS idx_lm_lookup ON locality_metadata (locality, district)",
    # Trigram index
    "CREATE INDEX IF NOT EXISTS idx_rt_locality_trgm ON registry_transactions USING GIN (locality gin_trgm_ops)",
    # SQL function: compute_valuation_stats
    """CREATE OR REPLACE FUNCTION compute_valuation_stats(p_locality TEXT, p_asset_type TEXT, p_months INT DEFAULT 24)
    RETURNS TABLE (comparable_count BIGINT, min_price NUMERIC, max_price NUMERIC, median_price NUMERIC,
                   q1_price NUMERIC, q3_price NUMERIC, std_dev NUMERIC, cov NUMERIC,
                   earliest_date DATE, latest_date DATE)
    AS $$
    BEGIN RETURN QUERY
        SELECT COUNT(*)::BIGINT, MIN(rt.price_per_sqft), MAX(rt.price_per_sqft),
               PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY rt.price_per_sqft),
               PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY rt.price_per_sqft),
               PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY rt.price_per_sqft),
               STDDEV(rt.price_per_sqft),
               CASE WHEN PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY rt.price_per_sqft) > 0
                    THEN STDDEV(rt.price_per_sqft) / PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY rt.price_per_sqft)
                    ELSE 0 END,
               MIN(rt.registration_date), MAX(rt.registration_date)
        FROM registry_transactions rt
        WHERE rt.locality ILIKE '%' || p_locality || '%'
          AND rt.asset_type = p_asset_type
          AND rt.registration_date >= (CURRENT_DATE - (p_months || ' months')::INTERVAL)
          AND rt.is_outlier = FALSE;
    END; $$ LANGUAGE plpgsql STABLE""",
]

async def run_migration():
    print("Running RAG Foundation Migration...")
    async with get_db_context() as session:
        for i, stmt in enumerate(STATEMENTS):
            try:
                await session.execute(text(stmt))
                label = stmt.strip()[:60].replace('\n', ' ')
                print(f"  [{i+1}/{len(STATEMENTS)}] OK: {label}...")
            except Exception as e:
                print(f"  [{i+1}/{len(STATEMENTS)}] ERROR: {str(e)[:100]}")
    print("Migration complete!")

    # Verify
    async with get_db_context() as session:
        r = await session.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' "
            "AND table_name IN ('registry_transactions','guideline_values','locality_metadata','web_collected_prices') "
            "ORDER BY table_name"
        ))
        tables = [row[0] for row in r.fetchall()]
        print(f"Tables created: {tables}")

if __name__ == "__main__":
    asyncio.run(run_migration())
