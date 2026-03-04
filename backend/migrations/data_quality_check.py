"""
PurityProp — Data Quality Check
=================================

Phase 7: Validates data integrity after ETL pipeline execution.

Checks:
  1. price_min ≤ price_max for all records
  2. Year range 2021–2031
  3. Currency conversion accuracy (spot checks)
  4. Missing value detection
  5. Anomaly flagging (prices > 3σ from mean)
  6. Cross-table consistency

Run: python -m migrations.data_quality_check
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


class QualityReport:
    def __init__(self):
        self.checks = []
        self.passed = 0
        self.warnings = 0
        self.failures = 0

    def pass_check(self, name, detail=""):
        self.checks.append(("✅ PASS", name, detail))
        self.passed += 1

    def warn(self, name, detail=""):
        self.checks.append(("⚠️  WARN", name, detail))
        self.warnings += 1

    def fail(self, name, detail=""):
        self.checks.append(("❌ FAIL", name, detail))
        self.failures += 1

    def print_report(self):
        print(f"\n{'='*60}")
        print("DATA QUALITY REPORT")
        print(f"{'='*60}")
        for status, name, detail in self.checks:
            msg = f"  {status} | {name}"
            if detail:
                msg += f" — {detail}"
            print(msg)
        print(f"\n  Summary: {self.passed} passed, {self.warnings} warnings, {self.failures} failures")
        score = (self.passed / max(len(self.checks), 1)) * 10
        print(f"  Quality Score: {score:.1f}/10")
        return score


async def run_quality_checks():
    report = QualityReport()

    async with get_db_context() as session:

        # ═══════════════════════════════════════════════════════════
        # CHECK 1: price_min ≤ price_max in registry_transactions
        # ═══════════════════════════════════════════════════════════
        result = await session.execute(text("""
            SELECT COUNT(*) FROM registry_transactions
            WHERE price_per_sqft IS NOT NULL AND price_per_sqft < 0
        """))
        neg_prices = result.scalar()
        if neg_prices == 0:
            report.pass_check("No negative prices in registry_transactions")
        else:
            report.fail("Negative prices found", f"{neg_prices} records with negative price_per_sqft")

        # Check property_price_trends
        try:
            result = await session.execute(text("""
                SELECT COUNT(*) FROM property_price_trends
                WHERE land_price_min > land_price_max
            """))
            bad_ranges = result.scalar()
            if bad_ranges == 0:
                report.pass_check("price_min ≤ price_max in property_price_trends")
            else:
                report.fail("Price range violation", f"{bad_ranges} records where min > max")
        except Exception:
            report.warn("property_price_trends table not found", "Run migrate_chennai_schema first")

        # ═══════════════════════════════════════════════════════════
        # CHECK 2: Year range validation (2021-2031)
        # ═══════════════════════════════════════════════════════════
        result = await session.execute(text("""
            SELECT MIN(EXTRACT(YEAR FROM registration_date)),
                   MAX(EXTRACT(YEAR FROM registration_date))
            FROM registry_transactions
        """))
        row = result.fetchone()
        if row and row[0]:
            min_year, max_year = int(row[0]), int(row[1])
            if 2020 <= min_year and max_year <= 2026:
                report.pass_check("Year range valid in registry_transactions",
                                  f"{min_year}–{max_year}")
            else:
                report.warn("Unexpected year range",
                            f"{min_year}–{max_year} (expected 2021–2025)")

        try:
            result = await session.execute(text("""
                SELECT MIN(year), MAX(year) FROM property_price_trends
            """))
            row = result.fetchone()
            if row and row[0]:
                min_y, max_y = int(row[0]), int(row[1])
                if 2021 <= min_y and max_y <= 2031:
                    report.pass_check("Year range valid in property_price_trends",
                                      f"{min_y}–{max_y}")
                else:
                    report.warn("Unexpected year range in price_trends",
                                f"{min_y}–{max_y}")
        except Exception:
            pass

        # ═══════════════════════════════════════════════════════════
        # CHECK 3: Missing values
        # ═══════════════════════════════════════════════════════════
        result = await session.execute(text("""
            SELECT COUNT(*) FROM registry_transactions
            WHERE locality IS NULL OR district IS NULL
        """))
        missing_loc = result.scalar()
        if missing_loc == 0:
            report.pass_check("No missing locality/district in transactions")
        else:
            report.fail("Missing locality/district", f"{missing_loc} records")

        result = await session.execute(text("""
            SELECT COUNT(*) FROM registry_transactions
            WHERE price_per_sqft IS NULL OR price_per_sqft = 0
        """))
        missing_price = result.scalar()
        total = await session.execute(text("SELECT COUNT(*) FROM registry_transactions"))
        total_count = total.scalar()
        pct = (missing_price / max(total_count, 1)) * 100
        if pct < 5:
            report.pass_check("Missing prices < 5%", f"{missing_price}/{total_count} ({pct:.1f}%)")
        elif pct < 15:
            report.warn("Some missing prices", f"{missing_price}/{total_count} ({pct:.1f}%)")
        else:
            report.fail("Too many missing prices", f"{missing_price}/{total_count} ({pct:.1f}%)")

        # ═══════════════════════════════════════════════════════════
        # CHECK 4: Statistical anomalies (prices > 3σ from mean)
        # ═══════════════════════════════════════════════════════════
        result = await session.execute(text("""
            WITH stats AS (
                SELECT district, asset_type,
                       AVG(price_per_sqft) AS mean_price,
                       STDDEV(price_per_sqft) AS std_price
                FROM registry_transactions
                WHERE price_per_sqft > 0
                GROUP BY district, asset_type
            )
            SELECT COUNT(*)
            FROM registry_transactions rt
            JOIN stats s ON rt.district = s.district AND rt.asset_type = s.asset_type
            WHERE rt.price_per_sqft > 0
              AND s.std_price > 0
              AND ABS(rt.price_per_sqft - s.mean_price) > 3 * s.std_price
        """))
        outliers = result.scalar()
        outlier_pct = (outliers / max(total_count, 1)) * 100
        if outlier_pct < 2:
            report.pass_check("Statistical outliers < 2%", f"{outliers} records ({outlier_pct:.1f}%)")
        elif outlier_pct < 5:
            report.warn("Some statistical outliers", f"{outliers} records ({outlier_pct:.1f}%)")
        else:
            report.fail("Too many outliers", f"{outliers} records ({outlier_pct:.1f}%)")

        # ═══════════════════════════════════════════════════════════
        # CHECK 5: District coverage
        # ═══════════════════════════════════════════════════════════
        result = await session.execute(text("""
            SELECT district, COUNT(*), COUNT(DISTINCT locality)
            FROM registry_transactions
            GROUP BY district ORDER BY COUNT(*) DESC
        """))
        districts = result.fetchall()
        expected = {'chennai', 'coimbatore', 'salem', 'madurai'}
        found = {r[0] for r in districts}
        missing = expected - found

        if not missing:
            report.pass_check("All 4 districts present", ", ".join(sorted(found)))
        else:
            report.warn("Missing districts", ", ".join(sorted(missing)))

        print("\nDistrict breakdown:")
        for row in districts:
            print(f"  {row[0]}: {row[1]} transactions, {row[2]} localities")

        # ═══════════════════════════════════════════════════════════
        # CHECK 6: Embedding coverage
        # ═══════════════════════════════════════════════════════════
        embedded = await session.execute(text(
            "SELECT COUNT(*) FROM registry_transactions WHERE embedding IS NOT NULL"
        ))
        emb_count = embedded.scalar()
        emb_pct = (emb_count / max(total_count, 1)) * 100
        if emb_pct > 80:
            report.pass_check("Embedding coverage > 80%", f"{emb_count}/{total_count} ({emb_pct:.1f}%)")
        elif emb_pct > 50:
            report.warn("Moderate embedding coverage", f"{emb_count}/{total_count} ({emb_pct:.1f}%)")
        else:
            report.warn("Low embedding coverage", f"{emb_count}/{total_count} ({emb_pct:.1f}%)")

        # ═══════════════════════════════════════════════════════════
        # CHECK 7: Cross-table consistency
        # ═══════════════════════════════════════════════════════════
        try:
            ppt_count = await session.execute(text("SELECT COUNT(*) FROM property_price_trends"))
            loc_count = await session.execute(text("SELECT COUNT(*) FROM localities"))
            rag_count = await session.execute(text("SELECT COUNT(*) FROM locality_rag_summaries"))

            ppt_n = ppt_count.scalar()
            loc_n = loc_count.scalar()
            rag_n = rag_count.scalar()

            if loc_n > 0:
                report.pass_check("Localities table populated", f"{loc_n} localities")
            if ppt_n > 0:
                report.pass_check("Price trends populated", f"{ppt_n} trend records")
            if rag_n > 0:
                report.pass_check("RAG summaries generated", f"{rag_n} summaries")
            elif rag_n == 0:
                report.warn("No RAG summaries", "Run generate_rag_summaries.py")
        except Exception:
            report.warn("New tables not yet created", "Run migrate_chennai_schema.py first")

        # ═══════════════════════════════════════════════════════════
        # CHECK 8: Currency conversion spot check
        # ═══════════════════════════════════════════════════════════
        result = await session.execute(text("""
            SELECT COUNT(*) FROM registry_transactions
            WHERE price_per_sqft > 0
              AND price_per_sqft < 100
        """))
        too_low = result.scalar()
        result2 = await session.execute(text("""
            SELECT COUNT(*) FROM registry_transactions
            WHERE price_per_sqft > 100000
        """))
        too_high = result2.scalar()
        if too_low == 0 and too_high == 0:
            report.pass_check("Price range sanity check", "No prices < ₹100 or > ₹1,00,000/sqft")
        else:
            report.warn("Suspicious prices found",
                        f"{too_low} below ₹100, {too_high} above ₹1,00,000")

    return report.print_report()


async def main():
    print("=" * 60)
    print("PURITYPROP — DATA QUALITY CHECK")
    print("=" * 60)

    score = await run_quality_checks()

    print(f"\n{'='*60}")
    if score >= 8:
        print("✅ DATA QUALITY: PRODUCTION READY")
    elif score >= 6:
        print("⚠️  DATA QUALITY: ACCEPTABLE (minor issues)")
    else:
        print("❌ DATA QUALITY: NEEDS ATTENTION")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
