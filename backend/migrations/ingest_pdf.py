"""
PurityProp — Custom PDF Parser for TN Price Reports
=====================================================

Parses the specific PDF format from TN property reports:
  - Tier-based locality listings
  - Yearly price tables (2021-2031)
  - Columns: Year, Avg Land Price, Apartment Rate, Ground Value,
             Market Value, Negotiation Range, Guideline Value

Supports:
  - Coimbatore 100+ places PDF
  - Salem + Madurai City Corporation PDF

Run: python -m migrations.ingest_pdf
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
from datetime import date as date_type
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pdfplumber
from sqlalchemy import text
from app.core.database import get_db_context


# ─────────────────────────────────────────────────────────────────────
# PRICE PARSING UTILITIES
# ─────────────────────────────────────────────────────────────────────

def parse_price(text: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Parse price text like '₹5,800 – ₹6,800' or '₹12,500' into (min, max).
    Returns (None, None) if unparseable.
    """
    if not text:
        return None, None

    text = text.replace('\n', ' ').replace('\\n', ' ').strip()

    # Range pattern: ₹X,XXX – ₹Y,YYY
    range_match = re.findall(r'[\₹Rs.INR]*\s*([\d,]+(?:\.\d+)?)', text)
    if len(range_match) >= 2:
        try:
            v1 = float(range_match[0].replace(',', ''))
            v2 = float(range_match[1].replace(',', ''))
            return min(v1, v2), max(v1, v2)
        except ValueError:
            pass

    # Single value: ₹12,500
    if len(range_match) == 1:
        try:
            v = float(range_match[0].replace(',', ''))
            return v, v
        except ValueError:
            pass

    return None, None


def parse_year(text: str) -> Optional[int]:
    """Extract year from text."""
    if not text:
        return None
    match = re.search(r'(20[12]\d)', str(text))
    return int(match.group(1)) if match else None


def normalize_locality_name(name: str) -> str:
    """Normalize locality name for database."""
    name = name.lower().strip()
    # Remove common suffixes
    name = re.sub(r'\s*property price analysis.*', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*\(.*?\)', '', name)  # Remove parenthetical info
    name = re.sub(r'[^a-z0-9\s]', '', name)
    name = re.sub(r'\s+', '_', name.strip())
    return name


def detect_district(text: str, filename: str) -> str:
    """Detect district from page text or filename."""
    text_lower = (text + ' ' + filename).lower()
    if 'coimbatore' in text_lower or 'coimbatur' in text_lower:
        return 'coimbatore'
    if 'salem' in text_lower:
        return 'salem'
    if 'madurai' in text_lower:
        return 'madurai'
    if 'chennai' in text_lower:
        return 'chennai'
    if 'trichy' in text_lower or 'tiruchirappalli' in text_lower:
        return 'trichy'
    return 'unknown'


# ─────────────────────────────────────────────────────────────────────
# PDF TABLE PARSER
# ─────────────────────────────────────────────────────────────────────

def extract_all_price_data(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Extract all locality price data from a TN property report PDF.

    Returns list of records ready for database insertion.
    """
    filename = os.path.basename(pdf_path)
    records = []
    current_locality = None
    current_district = None

    print(f"\nProcessing: {filename}")

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        localities_found = 0

        for page_num, page in enumerate(pdf.pages):
            page_text = page.extract_text() or ''
            tables = page.extract_tables()

            # Try to detect locality name from text before the table
            locality_from_text = _extract_locality_from_text(page_text)
            if locality_from_text:
                current_locality = locality_from_text
                # Detect district
                detected = detect_district(page_text, filename)
                if detected != 'unknown':
                    current_district = detected

            if not current_district:
                current_district = detect_district(page_text, filename)

            # Process tables
            for table in tables:
                if not table or len(table) < 2:
                    continue

                # Check if this is a price table (has 'Year' header)
                header_str = ' '.join(str(c) for c in table[0] if c)
                if 'Year' not in header_str and 'year' not in header_str.lower():
                    continue

                localities_found += 1

                # Parse each row (skip header and projected years > 2024)
                for row in table[1:]:
                    year = parse_year(str(row[0]) if row[0] else '')
                    if not year or year > 2025:  # Only real data, not projections
                        continue

                    # Column mapping (based on observed format):
                    # [0]=Year, [1]=Land Price, [2]=Apartment Rate, [3]=Ground Value,
                    # [4]=Market Value, [5]=Negotiation, [6]=Guideline
                    land_min, land_max = parse_price(str(row[1]) if len(row) > 1 and row[1] else '')
                    apt_min, apt_max = parse_price(str(row[2]) if len(row) > 2 and row[2] else '')
                    guideline_min, guideline_max = parse_price(str(row[6]) if len(row) > 6 and row[6] else '')

                    # Create LAND transaction
                    if land_min and current_locality:
                        # Use midpoint of range for sale_value calculation
                        land_avg = (land_min + land_max) / 2
                        records.append({
                            'district': current_district or 'unknown',
                            'locality': current_locality,
                            'asset_type': 'land',
                            'area_sqft': 2400,
                            'sale_value': land_avg * 2400,
                            'registration_date': f'{year}-07-01',
                            'zone_tier': None,
                            'guideline_value': ((guideline_min + guideline_max) / 2) if guideline_min else None,
                            'data_source': 'pdf_import',
                            'price_min': land_min,
                            'price_max': land_max,
                        })

                    # Create APARTMENT transaction
                    if apt_min and current_locality:
                        apt_avg = (apt_min + apt_max) / 2
                        records.append({
                            'district': current_district or 'unknown',
                            'locality': current_locality,
                            'asset_type': 'apartment',
                            'area_sqft': 1200,  # Standard apartment
                            'sale_value': apt_avg * 1200,
                            'registration_date': f'{year}-07-01',
                            'zone_tier': None,
                            'guideline_value': ((guideline_min + guideline_max) / 2) if guideline_min else None,
                            'data_source': 'pdf_import',
                            'price_min': apt_min,
                            'price_max': apt_max,
                        })

            # Progress
            if (page_num + 1) % 50 == 0:
                print(f"  Page {page_num+1}/{total_pages} ({localities_found} localities, {len(records)} records)")

    print(f"  Total: {localities_found} localities, {len(records)} records extracted")
    return records


def _extract_locality_from_text(text: str) -> Optional[str]:
    """Extract locality name from page text."""
    # Pattern: "LOCALITY NAME Property Price Analysis (2021–2031)"
    # Or: "LOCALITY NAME – Property Price Analysis"
    match = re.search(
        r'^(.+?)\s*(?:–\s*)?Property Price Analysis',
        text, re.MULTILINE | re.IGNORECASE
    )
    if match:
        name = match.group(1).strip()
        # Clean up numbered prefix like "1. D.B. Road" → "D.B. Road"
        name = re.sub(r'^\d+\.\s*', '', name)
        return normalize_locality_name(name)

    # Fallback: "LOCALITY_NAME\nTier: ..."
    match2 = re.search(r'^([A-Z][A-Za-z\s.]+)\n.*Tier:', text, re.MULTILINE)
    if match2:
        return normalize_locality_name(match2.group(1))

    return None


# ─────────────────────────────────────────────────────────────────────
# ALSO INSERT GUIDELINE VALUES FROM PDF
# ─────────────────────────────────────────────────────────────────────

async def insert_guideline_values(records: List[Dict[str, Any]]) -> int:
    """Insert/update guideline values extracted from PDF."""
    inserted = 0

    # Group by locality + year → get latest guideline value
    guideline_map = {}
    for r in records:
        if r.get('guideline_value') and r['guideline_value'] > 0:
            key = (r['district'], r['locality'], r['asset_type'])
            year = r['registration_date'][:4]
            if key not in guideline_map or year >= guideline_map[key]['year']:
                guideline_map[key] = {
                    'year': year,
                    'value': r['guideline_value'],
                    'min': r.get('price_min', r['guideline_value']),
                    'max': r.get('price_max', r['guideline_value']),
                }

    async with get_db_context() as session:
        for (district, locality, asset_type), gv in guideline_map.items():
            try:
                await session.execute(
                    text("""
                        INSERT INTO guideline_values (district, locality, asset_type, min_per_sqft, max_per_sqft, effective_date)
                        VALUES (:district, :locality, :asset_type, :min_val, :max_val, :eff_date)
                        ON CONFLICT (district, locality, asset_type, effective_date) DO UPDATE
                        SET min_per_sqft = EXCLUDED.min_per_sqft, max_per_sqft = EXCLUDED.max_per_sqft
                    """),
                    {
                        'district': district, 'locality': locality,
                        'asset_type': asset_type,
                        'min_val': gv['min'], 'max_val': gv['max'],
                        'eff_date': date_type.fromisoformat(f"{gv['year']}-07-01"),
                    }
                )
                inserted += 1
            except Exception as e:
                print(f"  Guideline insert error: {e}")

    return inserted


# ─────────────────────────────────────────────────────────────────────
# DATABASE INSERT
# ─────────────────────────────────────────────────────────────────────

async def insert_transactions(records: List[Dict[str, Any]]) -> int:
    """Insert transaction records into registry_transactions."""
    inserted = 0

    async with get_db_context() as session:
        for r in records:
            try:
                if float(r['sale_value']) <= 0:
                    continue

                await session.execute(
                    text("""
                        INSERT INTO registry_transactions
                            (district, locality, asset_type, area_sqft, sale_value,
                             registration_date, zone_tier, guideline_value, data_source)
                        VALUES
                            (:district, :locality, :asset_type, :area_sqft, :sale_value,
                             :registration_date, :zone_tier, :guideline_value, :data_source)
                    """),
                    {
                        'district': r['district'],
                        'locality': r['locality'],
                        'asset_type': r['asset_type'],
                        'area_sqft': r['area_sqft'],
                        'sale_value': r['sale_value'],
                        'registration_date': date_type.fromisoformat(r['registration_date']),
                        'zone_tier': r.get('zone_tier'),
                        'guideline_value': r.get('guideline_value'),
                        'data_source': r['data_source'],
                    }
                )
                inserted += 1
            except Exception as e:
                pass  # Skip duplicates or errors silently

    return inserted


# ─────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────

async def main():
    data_dir = Path(__file__).parent.parent / 'data' / 'raw_pdf'

    print("=" * 60)
    print("PURITYPROP PDF INGESTION PIPELINE")
    print("=" * 60)

    if not data_dir.exists():
        print(f"No PDF directory found at: {data_dir}")
        return

    pdf_files = list(data_dir.glob('*.pdf'))
    print(f"Found {len(pdf_files)} PDF files")

    all_records = []
    for pdf_file in pdf_files:
        records = extract_all_price_data(str(pdf_file))
        all_records.extend(records)

    if not all_records:
        print("No records extracted from PDFs!")
        return

    # Summary
    districts = set(r['district'] for r in all_records)
    localities = set(r['locality'] for r in all_records)
    years = set(r['registration_date'][:4] for r in all_records)
    asset_types = set(r['asset_type'] for r in all_records)

    print(f"\n{'='*60}")
    print(f"EXTRACTION SUMMARY")
    print(f"{'='*60}")
    print(f"Total records: {len(all_records)}")
    print(f"Districts: {', '.join(sorted(districts))}")
    print(f"Unique localities: {len(localities)}")
    print(f"Years: {', '.join(sorted(years))}")
    print(f"Asset types: {', '.join(sorted(asset_types))}")

    # Show sample records
    print(f"\nSample records:")
    for r in all_records[:5]:
        price_sqft = r['sale_value'] / r['area_sqft'] if r['area_sqft'] else 0
        print(f"  {r['district']}/{r['locality']} | {r['asset_type']} | "
              f"{r['registration_date'][:4]} | Rs.{price_sqft:,.0f}/sqft")

    # Insert transactions
    print(f"\nInserting {len(all_records)} transactions into database...")
    inserted_txn = await insert_transactions(all_records)
    print(f"Inserted: {inserted_txn} transaction records")

    # Insert guideline values
    print(f"\nExtracting and inserting guideline values...")
    inserted_gv = await insert_guideline_values(all_records)
    print(f"Inserted: {inserted_gv} guideline value records")

    # Verify
    async with get_db_context() as session:
        total_rt = await session.execute(text("SELECT COUNT(*) FROM registry_transactions"))
        total_gv = await session.execute(text("SELECT COUNT(*) FROM guideline_values"))
        print(f"\nDatabase totals:")
        print(f"  registry_transactions: {total_rt.scalar()} rows")
        print(f"  guideline_values: {total_gv.scalar()} rows")

        # Per-district breakdown
        dist_counts = await session.execute(text("""
            SELECT district, COUNT(*), COUNT(DISTINCT locality)
            FROM registry_transactions
            GROUP BY district ORDER BY COUNT(*) DESC
        """))
        print(f"\nPer-district breakdown:")
        for row in dist_counts.fetchall():
            print(f"  {row[0]}: {row[1]} transactions, {row[2]} localities")

    print(f"\n{'='*60}")
    print(f"INGESTION COMPLETE")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
