-- ============================================
-- SUPABASE-NATIVE REAL ESTATE INTELLIGENCE SYSTEM
-- Migration 003: Functions & Triggers
-- ============================================

-- ============================================
-- Auto-update updated_at trigger
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_properties_updated_at ON properties;
CREATE TRIGGER trg_properties_updated_at
    BEFORE UPDATE ON properties
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_market_analytics_updated_at ON market_analytics;
CREATE TRIGGER trg_market_analytics_updated_at
    BEFORE UPDATE ON market_analytics
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- Auto-generate slug from title
-- ============================================
CREATE OR REPLACE FUNCTION generate_property_slug()
RETURNS TRIGGER AS $$
DECLARE
    base_slug TEXT;
    final_slug TEXT;
    counter INTEGER := 0;
BEGIN
    IF NEW.slug IS NULL OR NEW.slug = '' THEN
        base_slug := lower(regexp_replace(
            regexp_replace(NEW.title, '[^a-zA-Z0-9\s]', '', 'g'),
            '\s+', '-', 'g'
        ));
        final_slug := base_slug;
        LOOP
            EXIT WHEN NOT EXISTS (
                SELECT 1 FROM properties WHERE slug = final_slug AND id != NEW.id
            );
            counter := counter + 1;
            final_slug := base_slug || '-' || counter;
        END LOOP;
        NEW.slug := final_slug;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_properties_slug ON properties;
CREATE TRIGGER trg_properties_slug
    BEFORE INSERT OR UPDATE OF title ON properties
    FOR EACH ROW
    EXECUTE FUNCTION generate_property_slug();

-- ============================================
-- Auto-calculate price_per_sqft
-- ============================================
CREATE OR REPLACE FUNCTION calculate_price_per_sqft()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.carpet_area_sqft IS NOT NULL AND NEW.carpet_area_sqft > 0 THEN
        NEW.price_per_sqft := NEW.price / NEW.carpet_area_sqft;
    ELSIF NEW.built_up_area_sqft IS NOT NULL AND NEW.built_up_area_sqft > 0 THEN
        NEW.price_per_sqft := NEW.price / NEW.built_up_area_sqft;
    ELSIF NEW.super_built_up_area_sqft IS NOT NULL AND NEW.super_built_up_area_sqft > 0 THEN
        NEW.price_per_sqft := NEW.price / NEW.super_built_up_area_sqft;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_properties_price_per_sqft ON properties;
CREATE TRIGGER trg_properties_price_per_sqft
    BEFORE INSERT OR UPDATE OF price, carpet_area_sqft, built_up_area_sqft, super_built_up_area_sqft ON properties
    FOR EACH ROW
    EXECUTE FUNCTION calculate_price_per_sqft();

-- ============================================
-- Hybrid search function (vector + full-text + spatial)
-- ============================================
CREATE OR REPLACE FUNCTION hybrid_property_search(
    query_embedding vector(384) DEFAULT NULL,
    search_text TEXT DEFAULT NULL,
    filter_city TEXT DEFAULT 'Chennai',
    filter_type property_type DEFAULT NULL,
    filter_min_price NUMERIC DEFAULT NULL,
    filter_max_price NUMERIC DEFAULT NULL,
    filter_bedrooms SMALLINT DEFAULT NULL,
    filter_locality TEXT DEFAULT NULL,
    search_lat DOUBLE PRECISION DEFAULT NULL,
    search_lng DOUBLE PRECISION DEFAULT NULL,
    search_radius_km DOUBLE PRECISION DEFAULT 5.0,
    result_limit INTEGER DEFAULT 20,
    result_offset INTEGER DEFAULT 0
)
RETURNS TABLE (
    property_id UUID,
    title TEXT,
    price NUMERIC,
    locality TEXT,
    city TEXT,
    property_type property_type,
    vector_score REAL,
    text_score REAL,
    distance_km DOUBLE PRECISION,
    combined_score DOUBLE PRECISION,
    attributes JSONB
) AS $$
BEGIN
    RETURN QUERY
    WITH scored AS (
        SELECT
            p.id AS property_id,
            p.title,
            p.price,
            p.locality,
            p.city,
            p.property_type,
            -- Vector similarity (inner product, higher = better)
            CASE
                WHEN query_embedding IS NOT NULL AND p.embedding IS NOT NULL
                THEN (p.embedding <#> query_embedding) * -1
                ELSE 0
            END::REAL AS vector_score,
            -- Full-text relevance
            CASE
                WHEN search_text IS NOT NULL
                THEN ts_rank(
                    to_tsvector('english',
                        coalesce(p.title, '') || ' ' ||
                        coalesce(p.description, '') || ' ' ||
                        coalesce(p.locality, '')
                    ),
                    plainto_tsquery('english', search_text)
                )
                ELSE 0
            END::REAL AS text_score,
            -- Spatial distance
            CASE
                WHEN search_lat IS NOT NULL AND search_lng IS NOT NULL AND p.location IS NOT NULL
                THEN ST_DistanceSphere(
                    p.location,
                    ST_SetSRID(ST_MakePoint(search_lng, search_lat), 4326)
                ) / 1000.0
                ELSE NULL
            END AS distance_km,
            p.attributes
        FROM properties p
        WHERE
            p.deleted_at IS NULL
            AND p.status = 'available'
            AND (filter_city IS NULL OR p.city = filter_city)
            AND (filter_type IS NULL OR p.property_type = filter_type)
            AND (filter_min_price IS NULL OR p.price >= filter_min_price)
            AND (filter_max_price IS NULL OR p.price <= filter_max_price)
            AND (filter_bedrooms IS NULL OR p.bedrooms = filter_bedrooms)
            AND (filter_locality IS NULL OR p.locality ILIKE '%' || filter_locality || '%')
            AND (
                search_lat IS NULL OR search_lng IS NULL
                OR p.location IS NULL
                OR ST_DWithin(
                    p.location::geography,
                    ST_SetSRID(ST_MakePoint(search_lng, search_lat), 4326)::geography,
                    search_radius_km * 1000
                )
            )
            AND (
                search_text IS NULL
                OR to_tsvector('english',
                    coalesce(p.title, '') || ' ' ||
                    coalesce(p.description, '') || ' ' ||
                    coalesce(p.locality, '')
                ) @@ plainto_tsquery('english', search_text)
                OR p.title ILIKE '%' || search_text || '%'
            )
    )
    SELECT
        s.property_id,
        s.title,
        s.price,
        s.locality,
        s.city,
        s.property_type,
        s.vector_score,
        s.text_score,
        s.distance_km,
        -- Combined ranking (weighted fusion)
        (
            COALESCE(s.vector_score * 0.5, 0) +
            COALESCE(s.text_score * 0.3, 0) +
            COALESCE(1.0 / (1.0 + s.distance_km) * 0.2, 0)
        ) AS combined_score,
        s.attributes
    FROM scored s
    ORDER BY combined_score DESC
    LIMIT result_limit
    OFFSET result_offset;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================
-- Nearby properties function
-- ============================================
CREATE OR REPLACE FUNCTION get_nearby_properties(
    target_lat DOUBLE PRECISION,
    target_lng DOUBLE PRECISION,
    radius_km DOUBLE PRECISION DEFAULT 3.0,
    max_results INTEGER DEFAULT 10
)
RETURNS TABLE (
    property_id UUID,
    title TEXT,
    price NUMERIC,
    locality TEXT,
    distance_meters DOUBLE PRECISION
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id,
        p.title,
        p.price,
        p.locality,
        ST_DistanceSphere(
            p.location,
            ST_SetSRID(ST_MakePoint(target_lng, target_lat), 4326)
        ) AS distance_meters
    FROM properties p
    WHERE
        p.deleted_at IS NULL
        AND p.status = 'available'
        AND p.location IS NOT NULL
        AND ST_DWithin(
            p.location::geography,
            ST_SetSRID(ST_MakePoint(target_lng, target_lat), 4326)::geography,
            radius_km * 1000
        )
    ORDER BY distance_meters ASC
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql STABLE;
