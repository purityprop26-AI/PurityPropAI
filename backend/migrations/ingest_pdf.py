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
  - Chennai Localities All Region PDF

Phase 1-2 ETL enhancements:
  - Full 2021-2031 range (observed + forecast)
  - Cr/Lakhs currency parsing
  - Negotiation range extraction
  - Market value extraction
  - Chennai region detection
  - data_type tagging (observed vs forecast)

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

def _convert_currency(value_str: str) -> Optional[float]:
    """
    Convert currency strings with Cr/Lakhs notation.
    Examples: '₹1.34 Cr' → 13400000, '48 Lakhs' → 4800000, '₹5,600' → 5600
    """
    if not value_str:
        return None
    value_str = str(value_str).strip()

    # Remove currency symbols and source tags (MB, 99a, CP, NB, Proj, Est)
    cleaned = re.sub(r'[₹Rs.INR]', '', value_str)
    cleaned = re.sub(r'\b(MB|99a|CP|NB|Proj|Est|Forecast)\b', '', cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip()

    # Crore pattern: 1.34 Cr, 1.34Cr, 2 Crore
    cr_match = re.search(r'([\d,]+\.?\d*)\s*(?:Cr|Crore)', cleaned, re.IGNORECASE)
    if cr_match:
        try:
            return float(cr_match.group(1).replace(',', '')) * 10_000_000
        except ValueError:
            pass

    # Lakhs pattern: 48 Lakhs, 48L, 48 Lakh
    lakh_match = re.search(r'([\d,]+\.?\d*)\s*(?:Lakh|Lakhs|L\b)', cleaned, re.IGNORECASE)
    if lakh_match:
        try:
            return float(lakh_match.group(1).replace(',', '')) * 100_000
        except ValueError:
            pass

    # Plain number: 5,600 or 12500
    num_match = re.search(r'([\d,]+\.?\d*)', cleaned)
    if num_match:
        try:
            return float(num_match.group(1).replace(',', ''))
        except ValueError:
            pass

    return None


def parse_price(text: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Parse price text like '₹5,800 – ₹6,800' or '₹12,500' or '₹1.34 Cr' into (min, max).
    Now handles Cr/Lakhs notation.
    Returns (None, None) if unparseable.
    """
    if not text:
        return None, None

    text = text.replace('\n', ' ').replace('\\n', ' ').strip()

    # Check for range separator (–, -, to)
    parts = re.split(r'[–\-—]|\bto\b', text)
    if len(parts) >= 2:
        v1 = _convert_currency(parts[0])
        v2 = _convert_currency(parts[1])
        if v1 is not None and v2 is not None:
            return min(v1, v2), max(v1, v2)

    # Single value
    v = _convert_currency(text)
    if v is not None:
        return v, v

    return None, None


def parse_negotiation(text: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Parse negotiation range like '5%–8%' or '3-5%' into (min, max).
    Returns (None, None) if unparseable.
    """
    if not text:
        return None, None

    text = str(text).replace('\n', ' ').strip()

    # Extract percentage numbers
    nums = re.findall(r'(\d+(?:\.\d+)?)', text)
    if len(nums) >= 2:
        try:
            v1, v2 = float(nums[0]), float(nums[1])
            return min(v1, v2), max(v1, v2)
        except ValueError:
            pass
    elif len(nums) == 1:
        try:
            v = float(nums[0])
            return v, v
        except ValueError:
            pass

    return None, None


def parse_year(text: str) -> Optional[int]:
    """Extract year from text."""
    if not text:
        return None
    match = re.search(r'(20[12345]\d)', str(text))
    return int(match.group(1)) if match else None


def detect_data_type(year: int, row_text: str = '') -> str:
    """
    Determine if a row is observed data or forecast.
    - Years <= 2025 = observed (unless explicitly marked as forecast)
    - Years > 2025 = forecast
    - Text containing 'Proj', 'Forecast', 'Est' = forecast
    """
    row_lower = row_text.lower() if row_text else ''
    if any(tag in row_lower for tag in ['proj', 'forecast', 'est']):
        return 'forecast'
    if year > 2025:
        return 'forecast'
    return 'observed'


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
    if 'chennai' in text_lower:
        return 'chennai'
    if 'coimbatore' in text_lower or 'coimbatur' in text_lower:
        return 'coimbatore'
    if 'salem' in text_lower:
        return 'salem'
    if 'madurai' in text_lower:
        return 'madurai'
    if 'trichy' in text_lower or 'tiruchirappalli' in text_lower:
        return 'trichy'
    return 'unknown'


def detect_chennai_region(text: str) -> Optional[str]:
    """Detect Chennai sub-region (South/North/Central/East/West) from page text."""
    if not text:
        return None
    text_lower = text.lower()
    region_keywords = {
        'South Chennai': ['south chennai', 'south zone', 'southern chennai'],
        'North Chennai': ['north chennai', 'north zone', 'northern chennai'],
        'Central Chennai': ['central chennai', 'central zone', 'city centre'],
        'East Chennai': ['east chennai', 'east zone', 'eastern chennai', 'ecr', 'omr corridor'],
        'West Chennai': ['west chennai', 'west zone', 'western chennai'],
    }
    for region, keywords in region_keywords.items():
        for kw in keywords:
            if kw in text_lower:
                return region
    return None


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

                # Parse each row — include ALL years 2021-2031
                for row in table[1:]:
                    row_text = ' '.join(str(c) for c in row if c)
                    year = parse_year(str(row[0]) if row[0] else '')
                    if not year or year < 2021 or year > 2031:
                        continue

                    # Determine observed vs forecast
                    data_type = detect_data_type(year, row_text)

                    # Column mapping (based on observed format):
                    # [0]=Year, [1]=Land Price, [2]=Apartment Rate, [3]=Ground Value,
                    # [4]=Market Value, [5]=Negotiation, [6]=Guideline
                    land_min, land_max = parse_price(str(row[1]) if len(row) > 1 and row[1] else '')
                    apt_min, apt_max = parse_price(str(row[2]) if len(row) > 2 and row[2] else '')
                    ground_min, ground_max = parse_price(str(row[3]) if len(row) > 3 and row[3] else '')
                    market_min, market_max = parse_price(str(row[4]) if len(row) > 4 and row[4] else '')
                    neg_min, neg_max = parse_negotiation(str(row[5]) if len(row) > 5 and row[5] else '')
                    guideline_min, guideline_max = parse_price(str(row[6]) if len(row) > 6 and row[6] else '')

                    # Detect Chennai region from page text
                    region = None
                    if current_district == 'chennai':
                        region = detect_chennai_region(page_text)

                    # Create LAND transaction
                    if land_min and current_locality:
                        land_avg = (land_min + land_max) / 2
                        records.append({
                            'district': current_district or 'unknown',
                            'locality': current_locality,
                            'region': region,
                            'asset_type': 'land',
                            'area_sqft': 2400,
                            'sale_value': land_avg * 2400,
                            'registration_date': f'{year}-07-01',
                            'zone_tier': None,
                            'guideline_value': ((guideline_min + guideline_max) / 2) if guideline_min else None,
                            'data_source': 'pdf_import',
                            'data_type': data_type,
                            'price_min': land_min,
                            'price_max': land_max,
                            'ground_value': ((ground_min + ground_max) / 2) if ground_min else None,
                            'market_value': ((market_min + market_max) / 2) if market_min else None,
                            'negotiation_min': neg_min,
                            'negotiation_max': neg_max,
                        })

                    # Create APARTMENT transaction
                    if apt_min and current_locality:
                        apt_avg = (apt_min + apt_max) / 2
                        records.append({
                            'district': current_district or 'unknown',
                            'locality': current_locality,
                            'region': region,
                            'asset_type': 'apartment',
                            'area_sqft': 1200,  # Standard apartment
                            'sale_value': apt_avg * 1200,
                            'registration_date': f'{year}-07-01',
                            'zone_tier': None,
                            'guideline_value': ((guideline_min + guideline_max) / 2) if guideline_min else None,
                            'data_source': 'pdf_import',
                            'data_type': data_type,
                            'price_min': apt_min,
                            'price_max': apt_max,
                            'ground_value': None,
                            'market_value': ((market_min + market_max) / 2) if market_min else None,
                            'negotiation_min': neg_min,
                            'negotiation_max': neg_max,
                        })

            # Progress
            if (page_num + 1) % 50 == 0:
                print(f"  Page {page_num+1}/{total_pages} ({localities_found} localities, {len(records)} records)")

    print(f"  Total: {localities_found} localities, {len(records)} records extracted")
    return records


def _extract_locality_from_text(text: str) -> Optional[str]:
    """Extract locality name from page text."""
    # Pattern 1: "LOCALITY NAME Property Price Analysis (2021-2031)"
    # Or: "LOCALITY NAME - Property Price Analysis"
    match = re.search(
        r'^(.+?)\s*(?:[–-]\s*)?Property Price Analysis',
        text, re.MULTILINE | re.IGNORECASE
    )
    if match:
        name = match.group(1).strip()
        # Clean up numbered prefix like "1. D.B. Road"
        name = re.sub(r'^\d+\.?\s*', '', name)
        return normalize_locality_name(name)

    # Pattern 2: Chennai format - "1.Thoraipakkam Real Estate Market Intelligence (2021-2031)"
    match2 = re.search(
        r'^(?:\d+\.?\s*)?(.+?)\s*Real Estate Market Intelligence',
        text, re.MULTILINE | re.IGNORECASE
    )
    if match2:
        name = match2.group(1).strip()
        name = re.sub(r'^\d+\.?\s*', '', name)
        return normalize_locality_name(name)

    # Fallback: "LOCALITY_NAME\nTier: ..."
    match3 = re.search(r'^([A-Z][A-Za-z\s.]+)\n.*Tier:', text, re.MULTILINE)
    if match3:
        return normalize_locality_name(match3.group(1))

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
    """Insert transaction records into registry_transactions (batched)."""
    inserted = 0
    batch_size = 100

    for batch_start in range(0, len(records), batch_size):
        batch = records[batch_start:batch_start + batch_size]
        async with get_db_context() as session:
            for r in batch:
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
        # Progress
        done = min(batch_start + batch_size, len(records))
        if done % 500 == 0 or done == len(records):
            print(f"  Progress: {done}/{len(records)} processed ({inserted} inserted)")

    return inserted


# ─────────────────────────────────────────────────────────────────────
# INSERT INTO PROPERTY_PRICE_TRENDS (new structured table)
# ─────────────────────────────────────────────────────────────────────

async def insert_price_trends(records: List[Dict[str, Any]]) -> int:
    """
    Insert records into property_price_trends table.
    Groups land records by locality + year, resolves locality_id.
    """
    from migrations.migrate_chennai_schema import CHENNAI_REGION_MAP

    inserted = 0

    # Group records by (district, locality, year, data_type)
    trend_map = {}
    for r in records:
        if r['asset_type'] != 'land':  # land records carry the primary pricing
            continue
        key = (r['district'], r['locality'], r['registration_date'][:4], r.get('data_type', 'observed'))
        if key not in trend_map:
            trend_map[key] = r
        # If duplicate, keep the one with more data
        elif r.get('market_value') and not trend_map[key].get('market_value'):
            trend_map[key] = r

    # Also collect apartment prices
    apt_map = {}
    for r in records:
        if r['asset_type'] == 'apartment':
            key = (r['district'], r['locality'], r['registration_date'][:4])
            apt_avg = (r['price_min'] + r['price_max']) / 2 if r.get('price_min') and r.get('price_max') else None
            apt_map[key] = apt_avg

    async with get_db_context() as session:
        # Get/create locality IDs
        for (district, locality, year_str, data_type), r in trend_map.items():
            try:
                year = int(year_str)

                # Resolve region for the locality
                region_name = r.get('region')
                if not region_name and district == 'chennai':
                    # Try to find in CHENNAI_REGION_MAP
                    for reg, locs in CHENNAI_REGION_MAP.items():
                        if locality in locs:
                            region_name = reg
                            break
                if not region_name:
                    region_name = f"{district.title()} City"

                # Ensure city exists
                await session.execute(
                    text("INSERT INTO cities (city_name) VALUES (:name) ON CONFLICT DO NOTHING"),
                    {"name": district.title()}
                )
                city_result = await session.execute(
                    text("SELECT city_id FROM cities WHERE city_name = :name"),
                    {"name": district.title()}
                )
                city_row = city_result.fetchone()
                if not city_row:
                    continue
                city_id = city_row[0]

                # Ensure region exists
                await session.execute(
                    text("""
                        INSERT INTO regions (city_id, region_name)
                        VALUES (:city_id, :name)
                        ON CONFLICT (city_id, region_name) DO NOTHING
                    """),
                    {"city_id": city_id, "name": region_name}
                )
                region_result = await session.execute(
                    text("SELECT region_id FROM regions WHERE city_id = :cid AND region_name = :name"),
                    {"cid": city_id, "name": region_name}
                )
                region_row = region_result.fetchone()
                if not region_row:
                    continue
                region_id = region_row[0]

                # Ensure locality exists
                await session.execute(
                    text("""
                        INSERT INTO localities (region_id, locality_name)
                        VALUES (:rid, :name)
                        ON CONFLICT (region_id, locality_name) DO NOTHING
                    """),
                    {"rid": region_id, "name": locality}
                )
                loc_result = await session.execute(
                    text("SELECT locality_id FROM localities WHERE region_id = :rid AND locality_name = :name"),
                    {"rid": region_id, "name": locality}
                )
                loc_row = loc_result.fetchone()
                if not loc_row:
                    continue
                locality_id = loc_row[0]

                # Get apartment price for this locality+year
                apt_price = apt_map.get((district, locality, year_str))

                # Compute averages
                land_avg = ((r['price_min'] + r['price_max']) / 2) if r.get('price_min') and r.get('price_max') else None

                await session.execute(
                    text("""
                        INSERT INTO property_price_trends
                            (locality_id, year, land_price_min, land_price_max, land_price_avg,
                             apartment_price, market_price, guideline_price, ground_value,
                             negotiation_min, negotiation_max, data_type)
                        VALUES
                            (:lid, :year, :lmin, :lmax, :lavg,
                             :apt, :market, :guideline, :ground,
                             :negmin, :negmax, :dtype)
                        ON CONFLICT (locality_id, year, data_type) DO UPDATE
                        SET land_price_min = EXCLUDED.land_price_min,
                            land_price_max = EXCLUDED.land_price_max,
                            land_price_avg = EXCLUDED.land_price_avg,
                            apartment_price = EXCLUDED.apartment_price,
                            market_price = EXCLUDED.market_price,
                            guideline_price = EXCLUDED.guideline_price,
                            ground_value = EXCLUDED.ground_value,
                            negotiation_min = EXCLUDED.negotiation_min,
                            negotiation_max = EXCLUDED.negotiation_max
                    """),
                    {
                        'lid': locality_id, 'year': year,
                        'lmin': r.get('price_min'), 'lmax': r.get('price_max'),
                        'lavg': land_avg,
                        'apt': apt_price,
                        'market': r.get('market_value'),
                        'guideline': r.get('guideline_value'),
                        'ground': r.get('ground_value'),
                        'negmin': r.get('negotiation_min'),
                        'negmax': r.get('negotiation_max'),
                        'dtype': data_type,
                    }
                )
                inserted += 1
            except Exception as e:
                if 'duplicate' not in str(e).lower():
                    print(f"  Price trend insert error ({locality}/{year_str}): {e}")

    return inserted


# ─────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────

async def main():
    data_dir = Path(__file__).parent.parent / 'data' / 'raw_pdf'

    print("=" * 60)
    print("PURITYPROP PDF INGESTION PIPELINE (v2 — Chennai ETL)")
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
    observed = sum(1 for r in all_records if r.get('data_type') == 'observed')
    forecast = sum(1 for r in all_records if r.get('data_type') == 'forecast')

    print(f"\n{'='*60}")
    print(f"EXTRACTION SUMMARY")
    print(f"{'='*60}")
    print(f"Total records: {len(all_records)}")
    print(f"  Observed (2021-2025): {observed}")
    print(f"  Forecast (2026-2031): {forecast}")
    print(f"Districts: {', '.join(sorted(districts))}")
    print(f"Unique localities: {len(localities)}")
    print(f"Years: {', '.join(sorted(years))}")
    print(f"Asset types: {', '.join(sorted(asset_types))}")

    # Show sample records
    print(f"\nSample records:")
    for r in all_records[:5]:
        price_sqft = r['sale_value'] / r['area_sqft'] if r['area_sqft'] else 0
        dtype = r.get('data_type', 'observed')
        print(f"  {r['district']}/{r['locality']} | {r['asset_type']} | "
              f"{r['registration_date'][:4]} | Rs.{price_sqft:,.0f}/sqft | [{dtype}]")

    # Insert transactions (only observed data into registry_transactions)
    observed_records = [r for r in all_records if r.get('data_type', 'observed') == 'observed']
    print(f"\nInserting {len(observed_records)} observed transactions into registry_transactions...")
    inserted_txn = await insert_transactions(observed_records)
    print(f"Inserted: {inserted_txn} transaction records")

    # Insert guideline values
    print(f"\nExtracting and inserting guideline values...")
    inserted_gv = await insert_guideline_values(all_records)
    print(f"Inserted: {inserted_gv} guideline value records")

    # Insert property price trends (ALL data including forecasts)
    print(f"\nInserting {len(all_records)} records into property_price_trends...")
    try:
        inserted_ppt = await insert_price_trends(all_records)
        print(f"Inserted: {inserted_ppt} price trend records")
    except Exception as e:
        print(f"  Warning: property_price_trends insert failed: {e}")
        print(f"  Run `python -m migrations.migrate_chennai_schema` first to create tables.")

    # Verify
    async with get_db_context() as session:
        total_rt = await session.execute(text("SELECT COUNT(*) FROM registry_transactions"))
        total_gv = await session.execute(text("SELECT COUNT(*) FROM guideline_values"))
        print(f"\nDatabase totals:")
        print(f"  registry_transactions: {total_rt.scalar()} rows")
        print(f"  guideline_values: {total_gv.scalar()} rows")

        # Check property_price_trends if it exists
        try:
            total_ppt = await session.execute(text("SELECT COUNT(*) FROM property_price_trends"))
            print(f"  property_price_trends: {total_ppt.scalar()} rows")
        except Exception:
            pass

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

