"""
Database Migration Runner
Executes SQL migration files against Supabase PostgreSQL in order.
Validates schema and index creation with EXPLAIN ANALYZE.
"""
import asyncio
import asyncpg
import json
import os
import sys
import glob
from pathlib import Path


MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "migrations")
STATE_DIR = os.path.join(os.path.dirname(__file__), "..", "state")


async def run_migrations():
    """Execute all migration files in order."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set", file=sys.stderr)
        sys.exit(1)

    results = {
        "migrations_run": [],
        "errors": [],
        "validation": {}
    }

    try:
        conn = await asyncpg.connect(db_url, ssl="require")
        print("Connected to Supabase PostgreSQL\n")

        # Get migration files sorted
        migration_files = sorted(glob.glob(os.path.join(MIGRATIONS_DIR, "*.sql")))
        if not migration_files:
            print("ERROR: No migration files found", file=sys.stderr)
            sys.exit(1)

        print(f"Found {len(migration_files)} migration files\n")

        for mig_file in migration_files:
            filename = os.path.basename(mig_file)
            print(f"--- Executing: {filename} ---")
            try:
                with open(mig_file, "r", encoding="utf-8") as f:
                    sql = f.read()

                await conn.execute(sql)
                results["migrations_run"].append({"file": filename, "status": "success"})
                print(f"  ✓ {filename} applied successfully\n")

            except Exception as e:
                err_msg = f"{filename}: {str(e)}"
                # Check if it's a "already exists" type error - still OK
                if "already exists" in str(e).lower():
                    results["migrations_run"].append({"file": filename, "status": "already_applied"})
                    print(f"  ~ {filename} already applied (skipped)\n")
                else:
                    results["errors"].append(err_msg)
                    print(f"  ✗ ERROR: {err_msg}\n", file=sys.stderr)

        # ============================================
        # VALIDATION
        # ============================================
        print("\n=== SCHEMA VALIDATION ===\n")

        # 1. Verify tables exist
        tables = await conn.fetch("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        table_names = [t["table_name"] for t in tables]
        required_tables = {"properties", "market_analytics", "search_logs", "forecast_audit", "hallucination_logs"}
        missing_tables = required_tables - set(table_names)
        results["validation"]["tables"] = {
            "found": table_names,
            "required_present": len(missing_tables) == 0,
            "missing": list(missing_tables)
        }
        print(f"Tables: {table_names}")
        if missing_tables:
            print(f"  MISSING: {missing_tables}", file=sys.stderr)

        # 2. Verify columns on properties
        columns = await conn.fetch("""
            SELECT column_name, data_type, udt_name
            FROM information_schema.columns
            WHERE table_name = 'properties'
            ORDER BY ordinal_position
        """)
        col_info = {c["column_name"]: c["udt_name"] for c in columns}
        results["validation"]["properties_columns"] = col_info

        # Verify critical column types
        assert col_info.get("embedding") == "vector", "embedding column must be vector type"
        assert col_info.get("location") == "geometry", "location column must be geometry type"
        assert col_info.get("attributes") == "jsonb", "attributes column must be jsonb type"
        print(f"  Properties columns: {len(col_info)} columns verified")
        print(f"    embedding: {col_info.get('embedding')}")
        print(f"    location: {col_info.get('location')}")
        print(f"    attributes: {col_info.get('attributes')}")

        # 3. Verify indexes
        indexes = await conn.fetch("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'properties'
            ORDER BY indexname
        """)
        idx_names = [i["indexname"] for i in indexes]
        results["validation"]["indexes"] = idx_names

        required_indexes = {
            "idx_properties_embedding_hnsw",
            "idx_properties_location_gist",
            "idx_properties_attributes_gin",
            "idx_properties_fts",
            "idx_properties_price",
            "idx_properties_city_locality"
        }
        found_required = required_indexes.intersection(set(idx_names))
        missing_idx = required_indexes - set(idx_names)
        print(f"\n  Indexes on properties: {len(idx_names)} total")
        print(f"    Required indexes found: {len(found_required)}/{len(required_indexes)}")
        if missing_idx:
            print(f"    MISSING indexes: {missing_idx}", file=sys.stderr)
            results["errors"].append(f"Missing indexes: {list(missing_idx)}")

        # 4. EXPLAIN ANALYZE - verify index usage (no sequential scans)
        print("\n=== EXPLAIN ANALYZE VALIDATION ===\n")

        # Insert a test row for EXPLAIN ANALYZE
        test_id = await conn.fetchval("""
            INSERT INTO properties (title, slug, property_type, listing_type, price, locality, city, location, attributes, embedding)
            VALUES (
                'Test Validation Property',
                'test-validation-property-' || extract(epoch from now())::text,
                'apartment', 'sale', 5000000.00,
                'Adyar', 'Chennai',
                ST_SetSRID(ST_MakePoint(80.2573, 13.0067), 4326),
                '{"bhk": 2, "parking": true}'::jsonb,
                ('[' || array_to_string(array(SELECT random() FROM generate_series(1, 384)), ',') || ']')::vector
            )
            RETURNING id
        """)

        # Test spatial query with EXPLAIN ANALYZE
        explain_spatial = await conn.fetch("""
            EXPLAIN ANALYZE
            SELECT id, title FROM properties
            WHERE ST_DWithin(
                location::geography,
                ST_SetSRID(ST_MakePoint(80.2573, 13.0067), 4326)::geography,
                5000
            )
        """)
        spatial_plan = "\n".join([r["QUERY PLAN"] for r in explain_spatial])
        has_seq_scan_spatial = "Seq Scan" in spatial_plan and "Index" not in spatial_plan
        results["validation"]["spatial_query"] = {
            "uses_index": not has_seq_scan_spatial,
            "plan": spatial_plan
        }
        print(f"  Spatial query: {'✓ Index scan' if not has_seq_scan_spatial else '✗ Sequential scan'}")

        # Test JSONB query with EXPLAIN ANALYZE
        explain_jsonb = await conn.fetch("""
            EXPLAIN ANALYZE
            SELECT id, title FROM properties
            WHERE attributes @> '{"bhk": 2}'::jsonb
        """)
        jsonb_plan = "\n".join([r["QUERY PLAN"] for r in explain_jsonb])
        has_seq_scan_jsonb = "Seq Scan" in jsonb_plan and "Bitmap" not in jsonb_plan
        results["validation"]["jsonb_query"] = {
            "uses_index": not has_seq_scan_jsonb,
            "plan": jsonb_plan
        }
        print(f"  JSONB query: {'✓ Index/Bitmap scan' if not has_seq_scan_jsonb else '✗ Sequential scan'}")

        # Clean up test row
        await conn.execute("DELETE FROM properties WHERE id = $1", test_id)

        # 5. Verify functions
        functions = await conn.fetch("""
            SELECT routine_name
            FROM information_schema.routines
            WHERE routine_schema = 'public'
            AND routine_type = 'FUNCTION'
            ORDER BY routine_name
        """)
        func_names = [f["routine_name"] for f in functions]
        results["validation"]["functions"] = func_names
        print(f"\n  Functions: {[f for f in func_names if f in ['hybrid_property_search', 'get_nearby_properties', 'update_updated_at_column', 'generate_property_slug', 'calculate_price_per_sqft']]}")

        await conn.close()

        # Determine overall status
        if results["errors"]:
            results["status"] = "partial"
        else:
            results["status"] = "success"

    except AssertionError as e:
        results["status"] = "failed"
        results["errors"].append(f"Validation assertion failed: {str(e)}")
        print(f"\nASSERTION FAILED: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        results["status"] = "failed"
        results["errors"].append(str(e))
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Write schema version
    version_file = os.path.join(MIGRATIONS_DIR, "..", "schema_version.txt")
    with open(version_file, "w") as f:
        f.write(f"version: 003\nmigrations: {len(results['migrations_run'])}\nstatus: {results['status']}\n")

    # Write results
    os.makedirs(STATE_DIR, exist_ok=True)
    output_path = os.path.join(STATE_DIR, "phase2_schema.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nResults written to {output_path}")
    print(f"Schema version written to {version_file}")
    print(f"\nOverall status: {results['status']}")

    if results["status"] == "failed":
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_migrations())
