-- ============================================
-- SUPABASE-NATIVE REAL ESTATE INTELLIGENCE SYSTEM
-- Migration 002: Indexes & Performance
-- ============================================

-- ============================================
-- HNSW Vector Index (for semantic similarity search)
-- ============================================
CREATE INDEX IF NOT EXISTS idx_properties_embedding_hnsw
ON properties
USING hnsw (embedding vector_ip_ops)
WITH (m = 16, ef_construction = 200);

-- ============================================
-- GiST Spatial Indexes (for PostGIS queries)
-- ============================================
CREATE INDEX IF NOT EXISTS idx_properties_location_gist
ON properties
USING gist (location);

CREATE INDEX IF NOT EXISTS idx_properties_boundary_gist
ON properties
USING gist (boundary);

CREATE INDEX IF NOT EXISTS idx_market_analytics_centroid_gist
ON market_analytics
USING gist (centroid);

-- ============================================
-- GIN JSONB Indexes (for attribute filtering)
-- ============================================
CREATE INDEX IF NOT EXISTS idx_properties_attributes_gin
ON properties
USING gin (attributes jsonb_path_ops);

CREATE INDEX IF NOT EXISTS idx_properties_amenities_gin
ON properties
USING gin (amenities jsonb_path_ops);

CREATE INDEX IF NOT EXISTS idx_properties_price_history_gin
ON properties
USING gin (price_history jsonb_path_ops);

CREATE INDEX IF NOT EXISTS idx_market_analytics_forecast_gin
ON market_analytics
USING gin (forecast_data jsonb_path_ops);

CREATE INDEX IF NOT EXISTS idx_market_analytics_risk_gin
ON market_analytics
USING gin (risk_assessment jsonb_path_ops);

-- ============================================
-- B-Tree Indexes (for scalar filtering)
-- ============================================
CREATE INDEX IF NOT EXISTS idx_properties_price
ON properties (price);

CREATE INDEX IF NOT EXISTS idx_properties_price_per_sqft
ON properties (price_per_sqft);

CREATE INDEX IF NOT EXISTS idx_properties_city_locality
ON properties (city, locality);

CREATE INDEX IF NOT EXISTS idx_properties_type_status
ON properties (property_type, status);

CREATE INDEX IF NOT EXISTS idx_properties_listing_type
ON properties (listing_type);

CREATE INDEX IF NOT EXISTS idx_properties_bedrooms
ON properties (bedrooms);

CREATE INDEX IF NOT EXISTS idx_properties_listed_at
ON properties (listed_at DESC);

CREATE INDEX IF NOT EXISTS idx_properties_slug
ON properties (slug);

CREATE INDEX IF NOT EXISTS idx_properties_pincode
ON properties (pincode);

CREATE INDEX IF NOT EXISTS idx_properties_builder
ON properties (builder_name) WHERE builder_name IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_properties_rera
ON properties (rera_id) WHERE rera_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_properties_featured
ON properties (is_featured) WHERE is_featured = TRUE;

CREATE INDEX IF NOT EXISTS idx_properties_verified
ON properties (is_verified) WHERE is_verified = TRUE;

CREATE INDEX IF NOT EXISTS idx_properties_not_deleted
ON properties (id) WHERE deleted_at IS NULL;

-- Market Analytics indexes
CREATE INDEX IF NOT EXISTS idx_market_analytics_locality_period
ON market_analytics (locality, period_start, period_end);

CREATE INDEX IF NOT EXISTS idx_market_analytics_computed_at
ON market_analytics (computed_at DESC);

-- Search logs indexes
CREATE INDEX IF NOT EXISTS idx_search_logs_created
ON search_logs (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_search_logs_user
ON search_logs (user_id) WHERE user_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_search_logs_embedding_hnsw
ON search_logs
USING hnsw (query_embedding vector_ip_ops)
WITH (m = 16, ef_construction = 100);

-- Forecast audit indexes
CREATE INDEX IF NOT EXISTS idx_forecast_audit_locality
ON forecast_audit (locality, forecast_type);

CREATE INDEX IF NOT EXISTS idx_forecast_audit_created
ON forecast_audit (created_at DESC);

-- Hallucination logs indexes
CREATE INDEX IF NOT EXISTS idx_hallucination_logs_request
ON hallucination_logs (request_id);

CREATE INDEX IF NOT EXISTS idx_hallucination_logs_mismatch
ON hallucination_logs (mismatch_detected) WHERE mismatch_detected = TRUE;

-- ============================================
-- Full-Text Search Index
-- ============================================
CREATE INDEX IF NOT EXISTS idx_properties_fts
ON properties
USING gin (
    to_tsvector('english',
        coalesce(title, '') || ' ' ||
        coalesce(description, '') || ' ' ||
        coalesce(locality, '') || ' ' ||
        coalesce(builder_name, '') || ' ' ||
        coalesce(project_name, '')
    )
);

-- ============================================
-- Trigram Index (for fuzzy search)
-- ============================================
CREATE INDEX IF NOT EXISTS idx_properties_title_trgm
ON properties
USING gin (title gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_properties_locality_trgm
ON properties
USING gin (locality gin_trgm_ops);

-- ============================================
-- Composite Indexes (for common query patterns)
-- ============================================
CREATE INDEX IF NOT EXISTS idx_properties_search_composite
ON properties (city, property_type, status, price)
WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_properties_location_active
ON properties USING gist (location)
WHERE deleted_at IS NULL AND status = 'available';
