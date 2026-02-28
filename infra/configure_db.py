"""
Supabase PostgreSQL Database Configuration Script
Configures extensions, HNSW settings, and performance tuning.
Called by Terraform during infrastructure provisioning.
"""
import asyncio
import asyncpg
import json
import sys
import os


async def configure_database():
    """Apply database configuration to Supabase PostgreSQL."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL environment variable not set", file=sys.stderr)
        sys.exit(1)

    results = {
        "extensions": [],
        "config_applied": [],
        "errors": []
    }

    try:
        conn = await asyncpg.connect(db_url, ssl="require")
        print("Connected to Supabase PostgreSQL")

        # Verify extensions
        extensions = await conn.fetch("SELECT extname, extversion FROM pg_extension ORDER BY extname")
        results["extensions"] = [
            {"name": row["extname"], "version": row["extversion"]}
            for row in extensions
        ]
        print(f"Extensions installed: {[r['name'] for r in results['extensions']]}")

        # Required extensions check
        required = {"vector", "postgis", "pg_trgm", "btree_gin"}
        installed = {row["extname"] for row in extensions}
        missing = required - installed
        if missing:
            print(f"WARNING: Missing extensions: {missing}", file=sys.stderr)
            results["errors"].append(f"Missing extensions: {list(missing)}")

        # Apply database-level configuration
        db_configs = [
            ("work_mem", "256MB"),
            ("maintenance_work_mem", "512MB"),
        ]

        for param, value in db_configs:
            try:
                await conn.execute(f"ALTER DATABASE postgres SET {param} = '{value}'")
                results["config_applied"].append(f"{param}={value}")
                print(f"  SET {param} = {value}")
            except Exception as e:
                err_msg = f"Failed to set {param}: {e}"
                print(f"  WARNING: {err_msg}", file=sys.stderr)
                results["errors"].append(err_msg)

        # Verify hnsw.iterative_scan works at session level
        # (Supabase restricts ALTER DATABASE for this param)
        try:
            await conn.execute("SET hnsw.iterative_scan = relaxed_order")
            results["config_applied"].append("hnsw.iterative_scan=relaxed_order (session)")
            print("  SET hnsw.iterative_scan = relaxed_order (session-level OK)")
        except Exception as e:
            err_msg = f"hnsw.iterative_scan session set failed: {e}"
            print(f"  WARNING: {err_msg}", file=sys.stderr)
            results["errors"].append(err_msg)

        # Verify PostGIS
        try:
            version = await conn.fetchval("SELECT PostGIS_Version()")
            print(f"PostGIS version: {version}")
            results["postgis_version"] = version
        except Exception:
            results["errors"].append("PostGIS function not available")

        # Verify pgvector
        try:
            await conn.execute("SELECT '[1,2,3]'::vector")
            print("pgvector: operational")
            results["pgvector_operational"] = True
        except Exception:
            results["errors"].append("pgvector not operational")
            results["pgvector_operational"] = False

        await conn.close()
        results["status"] = "success" if not results["errors"] else "partial"

    except Exception as e:
        results["status"] = "failed"
        results["errors"].append(str(e))
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Write results
    output_path = os.path.join(os.path.dirname(__file__), "..", "state", "phase1_db_config.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nConfiguration results written to {output_path}")
    print(json.dumps(results, indent=2))

    if results["status"] == "failed":
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(configure_database())
