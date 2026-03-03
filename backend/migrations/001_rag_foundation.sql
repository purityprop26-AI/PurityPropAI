-- ═══════════════════════════════════════════════════════════════════════
-- PURITYPROP RAG FOUNDATION — Supabase PostgreSQL Migration 001
-- Run this in Supabase Dashboard → SQL Editor
-- ═══════════════════════════════════════════════════════════════════════

-- 1. Ensure extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ═══════════════════════════════════════════════════════════════════════
-- TABLE: registry_transactions (AUTHORITATIVE — all pricing derives from here)
-- ═══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS registry_transactions (
    id                  UUID DEFAULT gen_random_uuid() PRIMARY KEY,

    -- Location
    district            TEXT NOT NULL,
    locality            TEXT NOT NULL,
    micro_market        TEXT,                    -- e.g. 'Anna Nagar East Block 2'
    block               TEXT,
    pin_code            TEXT,

    -- Transaction
    asset_type          TEXT NOT NULL CHECK (asset_type IN ('land', 'apartment', 'villa', 'commercial')),
    area_sqft           NUMERIC(12, 2) NOT NULL CHECK (area_sqft > 0),
    sale_value          NUMERIC(15, 2) NOT NULL CHECK (sale_value > 0),
    price_per_sqft      NUMERIC(10, 2) GENERATED ALWAYS AS (sale_value / NULLIF(area_sqft, 0)) STORED,
    guideline_value     NUMERIC(10, 2),          -- Govt guideline at time of registration

    -- Registry metadata
    registration_date   DATE NOT NULL,
    document_number     TEXT,
    sub_registrar       TEXT,

    -- Geospatial
    geom                GEOMETRY(POINT, 4326),
    geo_hash            TEXT,

    -- Classification
    zone_tier           TEXT CHECK (zone_tier IN ('A', 'B', 'C', 'D')),
    data_source         TEXT NOT NULL DEFAULT 'tnreginet',
    source_confidence   TEXT NOT NULL DEFAULT 'authoritative'
                        CHECK (source_confidence IN ('authoritative', 'calibration', 'secondary')),

    -- Structured metadata
    road_width_ft       NUMERIC(6, 2),
    zoning              TEXT,                    -- residential / mixed / commercial
    amenities           JSONB DEFAULT '{}',

    -- Vector embedding
    embedding           vector(384),

    -- Audit
    is_outlier          BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ═══════════════════════════════════════════════════════════════════════
-- TABLE: guideline_values (Government Published — Floor Reference)
-- ═══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS guideline_values (
    id                  UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    district            TEXT NOT NULL,
    locality            TEXT NOT NULL,
    zone_number         TEXT,
    asset_type          TEXT NOT NULL CHECK (asset_type IN ('land', 'apartment', 'villa', 'commercial')),

    min_per_sqft        NUMERIC(10, 2) NOT NULL,
    max_per_sqft        NUMERIC(10, 2) NOT NULL,

    effective_date      DATE NOT NULL,
    revision_cycle      TEXT DEFAULT 'annual',
    source_url          TEXT DEFAULT 'https://tnreginet.gov.in',

    created_at          TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (district, locality, asset_type, effective_date)
);

-- ═══════════════════════════════════════════════════════════════════════
-- TABLE: web_collected_prices (Secondary — CALIBRATION ONLY)
-- ═══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS web_collected_prices (
    id                  UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    district            TEXT NOT NULL,
    locality            TEXT NOT NULL,
    asset_type          TEXT NOT NULL,

    avg_price_sqft      NUMERIC(10, 2) NOT NULL,
    min_price_sqft      NUMERIC(10, 2),
    max_price_sqft      NUMERIC(10, 2),
    sample_count        INT,

    source_portal       TEXT NOT NULL,            -- '99acres', 'magicbricks', 'manual_survey'
    collection_date     DATE NOT NULL,
    collector           TEXT,

    -- Calibration
    registry_divergence_pct  NUMERIC(8, 4),
    is_validated        BOOLEAN DEFAULT FALSE,
    validation_note     TEXT,

    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ═══════════════════════════════════════════════════════════════════════
-- TABLE: locality_metadata (Zone Tiers, Features, Infrastructure)
-- ═══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS locality_metadata (
    id                  UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    locality            TEXT NOT NULL,
    district            TEXT NOT NULL,
    zone_tier           TEXT NOT NULL CHECK (zone_tier IN ('A', 'B', 'C', 'D')),
    population_tier     TEXT CHECK (population_tier IN ('metro', 'urban', 'semi_urban', 'rural')),

    -- Infrastructure
    metro_proximity_km  NUMERIC(6, 2),
    it_corridor         BOOLEAN DEFAULT FALSE,
    highway_access      TEXT[],
    features            TEXT[],

    -- Premium factors (JSONB)
    infra_premium       JSONB DEFAULT '{}',       -- {"metro": 0.12, "it": 0.18}

    -- Centroid for geo queries
    geom_centroid       GEOMETRY(POINT, 4326),

    updated_at          TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (locality, district)
);

-- ═══════════════════════════════════════════════════════════════════════
-- INDEXES (Each with justification)
-- ═══════════════════════════════════════════════════════════════════════

-- 1. HNSW Vector Index — Semantic similarity search for RAG
CREATE INDEX IF NOT EXISTS idx_rt_embedding_hnsw
    ON registry_transactions
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 200);

-- 2. GiST Spatial Index — "Find all within X km"
CREATE INDEX IF NOT EXISTS idx_rt_geom
    ON registry_transactions
    USING GIST (geom);

-- 3. Primary query pattern — locality + asset + date
CREATE INDEX IF NOT EXISTS idx_rt_lookup
    ON registry_transactions (locality, asset_type, registration_date DESC);

-- 4. Partial index — clean (non-outlier) transactions only
CREATE INDEX IF NOT EXISTS idx_rt_clean
    ON registry_transactions (locality, asset_type, price_per_sqft)
    WHERE is_outlier = FALSE;

-- 5. Trigram for fuzzy locality matching
CREATE INDEX IF NOT EXISTS idx_rt_locality_trgm
    ON registry_transactions
    USING GIN (locality gin_trgm_ops);

-- 6. District-level partition query
CREATE INDEX IF NOT EXISTS idx_rt_district
    ON registry_transactions (district, locality);

-- 7. Guideline lookup
CREATE INDEX IF NOT EXISTS idx_gv_lookup
    ON guideline_values (district, locality, asset_type, effective_date DESC);

-- 8. Locality metadata lookup
CREATE INDEX IF NOT EXISTS idx_lm_lookup
    ON locality_metadata (locality, district);

-- ═══════════════════════════════════════════════════════════════════════
-- ROW LEVEL SECURITY
-- ═══════════════════════════════════════════════════════════════════════

ALTER TABLE registry_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE guideline_values ENABLE ROW LEVEL SECURITY;
ALTER TABLE web_collected_prices ENABLE ROW LEVEL SECURITY;
ALTER TABLE locality_metadata ENABLE ROW LEVEL SECURITY;

-- Authenticated users can READ all data
CREATE POLICY "authenticated_read_rt" ON registry_transactions FOR SELECT
    USING (true);
CREATE POLICY "authenticated_read_gv" ON guideline_values FOR SELECT
    USING (true);
CREATE POLICY "authenticated_read_wc" ON web_collected_prices FOR SELECT
    USING (true);
CREATE POLICY "authenticated_read_lm" ON locality_metadata FOR SELECT
    USING (true);

-- Only service_role can INSERT/UPDATE (backend only)
CREATE POLICY "service_write_rt" ON registry_transactions FOR ALL
    USING (auth.role() = 'service_role');
CREATE POLICY "service_write_gv" ON guideline_values FOR ALL
    USING (auth.role() = 'service_role');
CREATE POLICY "service_write_wc" ON web_collected_prices FOR ALL
    USING (auth.role() = 'service_role');
CREATE POLICY "service_write_lm" ON locality_metadata FOR ALL
    USING (auth.role() = 'service_role');

-- ═══════════════════════════════════════════════════════════════════════
-- FUNCTIONS: Hybrid search + valuation
-- ═══════════════════════════════════════════════════════════════════════

-- Hybrid search: vector + scalar + geo
CREATE OR REPLACE FUNCTION hybrid_search(
    query_embedding vector(384),
    p_locality TEXT,
    p_asset_type TEXT,
    p_months INT DEFAULT 24,
    p_limit INT DEFAULT 50
)
RETURNS TABLE (
    id UUID,
    locality TEXT,
    asset_type TEXT,
    area_sqft NUMERIC,
    sale_value NUMERIC,
    price_per_sqft NUMERIC,
    registration_date DATE,
    zone_tier TEXT,
    similarity FLOAT,
    data_source TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        rt.id,
        rt.locality,
        rt.asset_type,
        rt.area_sqft,
        rt.sale_value,
        rt.price_per_sqft,
        rt.registration_date,
        rt.zone_tier,
        1 - (rt.embedding <=> query_embedding) AS similarity,
        rt.data_source
    FROM registry_transactions rt
    WHERE rt.locality ILIKE '%' || p_locality || '%'
      AND rt.asset_type = p_asset_type
      AND rt.registration_date >= (CURRENT_DATE - (p_months || ' months')::INTERVAL)
      AND rt.is_outlier = FALSE
    ORDER BY rt.embedding <=> query_embedding
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql STABLE;

-- Valuation stats: median, IQR, stddev, count
CREATE OR REPLACE FUNCTION compute_valuation_stats(
    p_locality TEXT,
    p_asset_type TEXT,
    p_months INT DEFAULT 24
)
RETURNS TABLE (
    comparable_count BIGINT,
    min_price NUMERIC,
    max_price NUMERIC,
    median_price NUMERIC,
    q1_price NUMERIC,
    q3_price NUMERIC,
    std_dev NUMERIC,
    cov NUMERIC,
    earliest_date DATE,
    latest_date DATE
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::BIGINT AS comparable_count,
        MIN(rt.price_per_sqft) AS min_price,
        MAX(rt.price_per_sqft) AS max_price,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY rt.price_per_sqft) AS median_price,
        PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY rt.price_per_sqft) AS q1_price,
        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY rt.price_per_sqft) AS q3_price,
        STDDEV(rt.price_per_sqft) AS std_dev,
        CASE WHEN PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY rt.price_per_sqft) > 0
            THEN STDDEV(rt.price_per_sqft) / PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY rt.price_per_sqft)
            ELSE 0
        END AS cov,
        MIN(rt.registration_date) AS earliest_date,
        MAX(rt.registration_date) AS latest_date
    FROM registry_transactions rt
    WHERE rt.locality ILIKE '%' || p_locality || '%'
      AND rt.asset_type = p_asset_type
      AND rt.registration_date >= (CURRENT_DATE - (p_months || ' months')::INTERVAL)
      AND rt.is_outlier = FALSE;
END;
$$ LANGUAGE plpgsql STABLE;

-- Geo-radius search
CREATE OR REPLACE FUNCTION search_by_radius(
    p_lat DOUBLE PRECISION,
    p_lng DOUBLE PRECISION,
    p_radius_km DOUBLE PRECISION DEFAULT 2.0,
    p_asset_type TEXT DEFAULT 'land',
    p_limit INT DEFAULT 50
)
RETURNS TABLE (
    id UUID,
    locality TEXT,
    price_per_sqft NUMERIC,
    registration_date DATE,
    distance_km DOUBLE PRECISION
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        rt.id,
        rt.locality,
        rt.price_per_sqft,
        rt.registration_date,
        ST_Distance(
            rt.geom::geography,
            ST_SetSRID(ST_MakePoint(p_lng, p_lat), 4326)::geography
        ) / 1000.0 AS distance_km
    FROM registry_transactions rt
    WHERE ST_DWithin(
        rt.geom::geography,
        ST_SetSRID(ST_MakePoint(p_lng, p_lat), 4326)::geography,
        p_radius_km * 1000  -- meters
    )
    AND rt.asset_type = p_asset_type
    AND rt.is_outlier = FALSE
    ORDER BY distance_km
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql STABLE;
