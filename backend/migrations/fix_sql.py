"""Fix SQL function type mismatch and add direct fallback query."""
import asyncio
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
from app.core.database import get_db_context
from sqlalchemy import text

async def fix_sql_function():
    print("Fixing compute_valuation_stats function...")
    async with get_db_context() as session:
        # Drop and recreate with correct return types (double precision for PERCENTILE_CONT)
        await session.execute(text("DROP FUNCTION IF EXISTS compute_valuation_stats(TEXT, TEXT, INT)"))
        await session.execute(text("""
            CREATE OR REPLACE FUNCTION compute_valuation_stats(
                p_locality TEXT, p_asset_type TEXT, p_months INT DEFAULT 24
            )
            RETURNS TABLE (
                comparable_count BIGINT,
                min_price NUMERIC,
                max_price NUMERIC,
                median_price DOUBLE PRECISION,
                q1_price DOUBLE PRECISION,
                q3_price DOUBLE PRECISION,
                std_dev DOUBLE PRECISION,
                cov DOUBLE PRECISION,
                earliest_date DATE,
                latest_date DATE
            )
            AS $$
            BEGIN
                RETURN QUERY
                SELECT
                    COUNT(*)::BIGINT,
                    MIN(rt.price_per_sqft),
                    MAX(rt.price_per_sqft),
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY rt.price_per_sqft),
                    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY rt.price_per_sqft),
                    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY rt.price_per_sqft),
                    STDDEV(rt.price_per_sqft)::DOUBLE PRECISION,
                    CASE WHEN AVG(rt.price_per_sqft) > 0
                         THEN (STDDEV(rt.price_per_sqft) / AVG(rt.price_per_sqft))::DOUBLE PRECISION
                         ELSE 0::DOUBLE PRECISION END,
                    MIN(rt.registration_date),
                    MAX(rt.registration_date)
                FROM registry_transactions rt
                WHERE rt.locality ILIKE '%' || p_locality || '%'
                  AND rt.asset_type = p_asset_type
                  AND rt.registration_date >= (CURRENT_DATE - (p_months || ' months')::INTERVAL)
                  AND rt.is_outlier = FALSE;
            END;
            $$ LANGUAGE plpgsql STABLE
        """))
        print("  Function recreated with DOUBLE PRECISION return types")

        # Quick test
        r = await session.execute(text(
            "SELECT * FROM compute_valuation_stats('fairlands', 'land', 48)"
        ))
        row = r.fetchone()
        if row:
            print(f"  Test: fairlands land -> {row[0]} comps, min={row[1]}, max={row[2]}, median={row[3]}")
        else:
            print("  Test: no results for fairlands")

if __name__ == "__main__":
    asyncio.run(fix_sql_function())
