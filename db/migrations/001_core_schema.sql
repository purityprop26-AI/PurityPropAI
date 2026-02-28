-- ============================================
-- SUPABASE-NATIVE REAL ESTATE INTELLIGENCE SYSTEM
-- Migration 001: Core Schema
-- ============================================
-- Extensions verification (should already be enabled by Terraform)
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gin;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- ENUM Types
-- ============================================
DO $$ BEGIN
    CREATE TYPE property_type AS ENUM (
        'apartment', 'villa', 'plot', 'house',
        'commercial', 'office', 'warehouse', 'penthouse',
        'studio', 'farmhouse', 'land'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE property_status AS ENUM (
        'available', 'sold', 'rented', 'under_construction',
        'upcoming', 'reserved', 'delisted'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE listing_type AS ENUM ('sale', 'rent', 'lease', 'auction');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE data_source AS ENUM (
        'manual', 'scraper', 'api', 'partner', 'user_submitted'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ============================================
-- Core Properties Table
-- ============================================
CREATE TABLE IF NOT EXISTS properties (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Basic information
    title TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    description TEXT,
    property_type property_type NOT NULL DEFAULT 'apartment',
    listing_type listing_type NOT NULL DEFAULT 'sale',
    status property_status NOT NULL DEFAULT 'available',

    -- Pricing
    price NUMERIC(15, 2) NOT NULL,
    price_per_sqft NUMERIC(10, 2),
    currency VARCHAR(3) NOT NULL DEFAULT 'INR',

    -- Area
    carpet_area_sqft NUMERIC(10, 2),
    built_up_area_sqft NUMERIC(10, 2),
    super_built_up_area_sqft NUMERIC(10, 2),
    plot_area_sqft NUMERIC(10, 2),

    -- Location (structured)
    address_line1 TEXT,
    address_line2 TEXT,
    locality TEXT NOT NULL,
    sub_locality TEXT,
    city TEXT NOT NULL DEFAULT 'Chennai',
    state TEXT NOT NULL DEFAULT 'Tamil Nadu',
    pincode VARCHAR(10),
    country VARCHAR(3) NOT NULL DEFAULT 'IND',

    -- Spatial (PostGIS)
    location GEOMETRY(Point, 4326),
    boundary GEOMETRY(Polygon, 4326),

    -- Structured details
    bedrooms SMALLINT,
    bathrooms SMALLINT,
    balconies SMALLINT,
    floor_number SMALLINT,
    total_floors SMALLINT,
    parking_slots SMALLINT DEFAULT 0,
    furnishing VARCHAR(20),
    facing VARCHAR(20),
    age_of_property SMALLINT,

    -- JSONB attributes (flexible schema)
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    amenities JSONB NOT NULL DEFAULT '[]'::jsonb,
    nearby_places JSONB NOT NULL DEFAULT '[]'::jsonb,
    price_history JSONB NOT NULL DEFAULT '[]'::jsonb,
    images JSONB NOT NULL DEFAULT '[]'::jsonb,

    -- Vector embedding (for semantic search)
    embedding vector(384),

    -- Metadata
    data_source data_source DEFAULT 'manual',
    source_url TEXT,
    builder_name TEXT,
    project_name TEXT,
    rera_id VARCHAR(50),
    is_verified BOOLEAN DEFAULT FALSE,
    is_featured BOOLEAN DEFAULT FALSE,
    view_count INTEGER DEFAULT 0,
    inquiry_count INTEGER DEFAULT 0,

    -- Timestamps
    listed_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    sold_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- ============================================
-- Market Analytics Table
-- ============================================
CREATE TABLE IF NOT EXISTS market_analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    locality TEXT NOT NULL,
    city TEXT NOT NULL DEFAULT 'Chennai',
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,

    -- Market metrics (all computed by microservices)
    avg_price_per_sqft NUMERIC(10, 2),
    median_price NUMERIC(15, 2),
    total_listings INTEGER,
    total_sold INTEGER,
    absorption_rate NUMERIC(5, 4),
    liquidity_score NUMERIC(5, 4),
    cagr NUMERIC(8, 6),
    price_volatility NUMERIC(8, 6),
    demand_supply_ratio NUMERIC(8, 4),
    inventory_months NUMERIC(6, 2),

    -- Forecast data
    forecast_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    risk_assessment JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- Spatial
    centroid GEOMETRY(Point, 4326),

    -- Metadata
    computed_at TIMESTAMPTZ DEFAULT NOW(),
    model_version VARCHAR(20),
    confidence_score NUMERIC(5, 4),

    UNIQUE(locality, city, period_start, period_end)
);

-- ============================================
-- Search Queries Log (for analytics)
-- ============================================
CREATE TABLE IF NOT EXISTS search_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID,
    query_text TEXT NOT NULL,
    query_embedding vector(384),
    filters JSONB DEFAULT '{}'::jsonb,
    result_count INTEGER,
    latency_ms NUMERIC(10, 2),
    retrieval_method VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- Forecast Audit Trail
-- ============================================
CREATE TABLE IF NOT EXISTS forecast_audit (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    locality TEXT NOT NULL,
    forecast_type VARCHAR(30) NOT NULL,
    input_params JSONB NOT NULL,
    output_result JSONB NOT NULL,
    model_version VARCHAR(20),
    mape NUMERIC(8, 6),
    execution_time_ms NUMERIC(10, 2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- Hallucination Detection Log
-- ============================================
CREATE TABLE IF NOT EXISTS hallucination_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    request_id UUID NOT NULL,
    narrative_output TEXT,
    tool_outputs JSONB,
    retrieved_data JSONB,
    mismatch_detected BOOLEAN DEFAULT FALSE,
    mismatch_details JSONB,
    judge_verdict VARCHAR(20),
    action_taken VARCHAR(30),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
