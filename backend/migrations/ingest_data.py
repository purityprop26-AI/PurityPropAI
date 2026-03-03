"""
PurityProp — Data Ingestion Pipeline
======================================

Ingests JSON and PDF files containing property price data
into the registry_transactions table.

USAGE:
  python -m migrations.ingest_data

Place files in:
  backend/data/raw_json/   → JSON files
  backend/data/raw_pdf/    → PDF files

SUPPORTED JSON FORMATS:
  Format A (array of objects):
    [
      {"locality": "anna nagar", "district": "chennai", "price_sqft": 9500,
       "area_sqft": 2400, "asset_type": "land", "date": "2024-08-15"},
      ...
    ]

  Format B (locality-grouped):
    {
      "anna_nagar": {
        "district": "chennai",
        "transactions": [
          {"price_sqft": 9500, "area_sqft": 2400, "date": "2024-08-15"},
          ...
        ]
      }
    }

  Format C (flat rows — CSV-like):
    [
      {"locality": "anna nagar", "price": 21600000, "area": 2400, "date": "2024-08-15"}
    ]

PDF: Extracts text → finds tables with locality/price data → parses into records.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import text
from app.core.database import get_db_context

# ─────────────────────────────────────────────────────────────────────
# LOCALITY NORMALIZER
# ─────────────────────────────────────────────────────────────────────

def normalize_locality(name: str) -> str:
    """Normalize locality name to database format."""
    name = name.lower().strip()
    name = re.sub(r'[^a-z0-9\s]', '', name)
    name = re.sub(r'\s+', '_', name)
    return name


def normalize_district(name: str) -> str:
    """Normalize district name."""
    name = name.lower().strip()
    name = re.sub(r'[^a-z\s]', '', name)
    name = name.strip()
    return name


def parse_date(date_str: str) -> Optional[str]:
    """Parse various date formats to YYYY-MM-DD."""
    if not date_str:
        return None
    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d', '%d-%b-%Y', '%d %b %Y'):
        try:
            return datetime.strptime(str(date_str).strip(), fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    # Try just year
    if re.match(r'^\d{4}$', str(date_str)):
        return f"{date_str}-06-15"  # Mid-year default
    return None


def detect_asset_type(text: str) -> str:
    """Detect asset type from text."""
    t = text.lower()
    if any(w in t for w in ['apartment', 'flat', 'bhk']):
        return 'apartment'
    if any(w in t for w in ['villa', 'bungalow', 'independent']):
        return 'villa'
    if any(w in t for w in ['commercial', 'office', 'shop']):
        return 'commercial'
    return 'land'


# ─────────────────────────────────────────────────────────────────────
# JSON INGESTION
# ─────────────────────────────────────────────────────────────────────

def parse_json_file(filepath: str) -> List[Dict[str, Any]]:
    """Parse JSON file into normalized transaction records."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    records = []

    # Format A: Array of objects
    if isinstance(data, list):
        for item in data:
            record = _extract_record_from_dict(item)
            if record:
                records.append(record)

    # Format B: Locality-grouped
    elif isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict):
                # Check if it has 'transactions' array
                if 'transactions' in value:
                    district = normalize_district(value.get('district', 'chennai'))
                    locality = normalize_locality(key)
                    asset_type = value.get('asset_type', 'land')
                    for txn in value['transactions']:
                        txn['locality'] = locality
                        txn['district'] = district
                        txn['asset_type'] = asset_type
                        record = _extract_record_from_dict(txn)
                        if record:
                            records.append(record)
                else:
                    # Single entry per locality
                    item = {**value, 'locality': key}
                    record = _extract_record_from_dict(item)
                    if record:
                        records.append(record)

    print(f"  Parsed {len(records)} records from {os.path.basename(filepath)}")
    return records


def _extract_record_from_dict(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract a normalized transaction record from a dict."""
    # Find locality
    locality = normalize_locality(
        item.get('locality') or item.get('location') or
        item.get('area') or item.get('place') or ''
    )
    if not locality:
        return None

    # Find district
    district = normalize_district(
        item.get('district') or item.get('city') or 'chennai'
    )

    # Find price
    price_sqft = (
        item.get('price_sqft') or item.get('price_per_sqft') or
        item.get('rate_sqft') or item.get('rate') or
        item.get('guideline_value') or 0
    )
    total_price = item.get('price') or item.get('sale_value') or item.get('total_price') or 0
    area = item.get('area_sqft') or item.get('area') or item.get('size') or 0

    # If we have total price and area but no price_sqft, compute it
    if not price_sqft and total_price and area:
        price_sqft = float(total_price) / float(area)

    # If we have price_sqft but no total, compute it (default 2400 sqft)
    if price_sqft and not total_price:
        area = float(area) if area else 2400
        total_price = float(price_sqft) * area

    if not price_sqft and not total_price:
        return None

    # Find date
    date_str = parse_date(
        item.get('date') or item.get('registration_date') or
        item.get('reg_date') or item.get('year') or ''
    )
    if not date_str:
        date_str = '2024-07-01'  # Default to current cycle

    # Asset type
    asset_type = (
        item.get('asset_type') or item.get('type') or
        item.get('property_type') or 'land'
    ).lower()
    if asset_type not in ('land', 'apartment', 'villa', 'commercial'):
        asset_type = detect_asset_type(asset_type)

    # Zone tier
    zone = item.get('zone_tier') or item.get('zone') or None

    return {
        'district': district,
        'locality': locality,
        'asset_type': asset_type,
        'area_sqft': float(area) if area else 2400,
        'sale_value': float(total_price) if total_price else float(price_sqft) * 2400,
        'registration_date': date_str,
        'zone_tier': zone,
        'data_source': 'json_import',
    }


# ─────────────────────────────────────────────────────────────────────
# PDF INGESTION
# ─────────────────────────────────────────────────────────────────────

def parse_pdf_file(filepath: str) -> List[Dict[str, Any]]:
    """Extract transaction data from PDF files."""
    try:
        import pdfplumber
    except ImportError:
        print(f"  ⚠️ pdfplumber not installed. Run: pip install pdfplumber")
        print(f"  Skipping PDF: {os.path.basename(filepath)}")
        return []

    records = []
    with pdfplumber.open(filepath) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            # Try table extraction first
            tables = page.extract_tables()
            if tables:
                for table in tables:
                    records.extend(_parse_table(table))
            else:
                # Fallback: extract text and look for price patterns
                text_content = page.extract_text() or ""
                records.extend(_parse_text_for_prices(text_content))

    print(f"  Parsed {len(records)} records from {os.path.basename(filepath)}")
    return records


def _parse_table(table: List[List]) -> List[Dict[str, Any]]:
    """Parse a table extracted from PDF."""
    if not table or len(table) < 2:
        return []

    records = []
    # First row is likely headers
    headers = [str(h).lower().strip() if h else '' for h in table[0]]

    # Map headers to our fields
    col_map = {}
    for i, h in enumerate(headers):
        if any(w in h for w in ['locality', 'location', 'area', 'place', 'village']):
            col_map['locality'] = i
        elif any(w in h for w in ['district', 'city']):
            col_map['district'] = i
        elif any(w in h for w in ['price', 'value', 'rate', 'sqft', 'sq.ft']):
            col_map['price'] = i
        elif any(w in h for w in ['area', 'size', 'extent']):
            col_map['area'] = i
        elif any(w in h for w in ['date', 'year', 'period']):
            col_map['date'] = i
        elif any(w in h for w in ['type', 'asset', 'property']):
            col_map['type'] = i

    if 'locality' not in col_map or 'price' not in col_map:
        return []  # Can't identify essential columns

    for row in table[1:]:
        try:
            locality = str(row[col_map['locality']] or '').strip()
            price_str = str(row[col_map['price']] or '0')
            price = float(re.sub(r'[^\d.]', '', price_str) or 0)

            if not locality or not price:
                continue

            area = 2400
            if 'area' in col_map:
                area_str = str(row[col_map.get('area', '')] or '2400')
                area = float(re.sub(r'[^\d.]', '', area_str) or 2400)

            date_str = '2024-07-01'
            if 'date' in col_map:
                date_str = parse_date(str(row[col_map['date']] or '')) or '2024-07-01'

            district = 'chennai'
            if 'district' in col_map:
                district = normalize_district(str(row[col_map['district']] or 'chennai'))

            asset_type = 'land'
            if 'type' in col_map:
                asset_type = detect_asset_type(str(row[col_map['type']] or 'land'))

            records.append({
                'district': district,
                'locality': normalize_locality(locality),
                'asset_type': asset_type,
                'area_sqft': area,
                'sale_value': price * area if price < 50000 else price,  # Auto-detect sqft vs total
                'registration_date': date_str,
                'zone_tier': None,
                'data_source': 'pdf_import',
            })
        except (ValueError, IndexError):
            continue

    return records


def _parse_text_for_prices(text_content: str) -> List[Dict[str, Any]]:
    """Extract price data from raw PDF text using regex patterns."""
    records = []

    # Pattern: "Locality Name ... ₹X,XXX" or "Locality Name ... Rs.X,XXX"
    lines = text_content.split('\n')
    for line in lines:
        # Look for price pattern
        price_match = re.search(r'[₹Rs.INR]+\s*([\d,]+(?:\.\d+)?)', line)
        if not price_match:
            continue

        price = float(price_match.group(1).replace(',', ''))
        # Extract locality (text before the price)
        locality_text = line[:price_match.start()].strip()
        locality_text = re.sub(r'[^\w\s]', '', locality_text).strip()

        if not locality_text or len(locality_text) < 3:
            continue

        records.append({
            'district': 'chennai',
            'locality': normalize_locality(locality_text),
            'asset_type': 'land',
            'area_sqft': 2400,
            'sale_value': price * 2400 if price < 50000 else price,
            'registration_date': '2024-07-01',
            'zone_tier': None,
            'data_source': 'pdf_import',
        })

    return records


# ─────────────────────────────────────────────────────────────────────
# DATABASE INSERT
# ─────────────────────────────────────────────────────────────────────

async def insert_records(records: List[Dict[str, Any]]) -> int:
    """Insert validated records into registry_transactions."""
    inserted = 0
    skipped = 0

    async with get_db_context() as session:
        for r in records:
            try:
                # Validate
                if not r.get('locality') or not r.get('sale_value'):
                    skipped += 1
                    continue
                if float(r['sale_value']) <= 0:
                    skipped += 1
                    continue

                await session.execute(
                    text("""
                        INSERT INTO registry_transactions
                            (district, locality, asset_type, area_sqft, sale_value,
                             registration_date, zone_tier, data_source)
                        VALUES
                            (:district, :locality, :asset_type, :area_sqft, :sale_value,
                             :registration_date, :zone_tier, :data_source)
                    """),
                    {
                        'district': r['district'],
                        'locality': r['locality'],
                        'asset_type': r['asset_type'],
                        'area_sqft': r['area_sqft'],
                        'sale_value': r['sale_value'],
                        'registration_date': r['registration_date'],
                        'zone_tier': r.get('zone_tier'),
                        'data_source': r['data_source'],
                    }
                )
                inserted += 1
            except Exception as e:
                print(f"  Error inserting record: {e}")
                skipped += 1

    return inserted


# ─────────────────────────────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────────────────────────────

async def main():
    data_dir = Path(__file__).parent.parent / 'data'
    json_dir = data_dir / 'raw_json'
    pdf_dir = data_dir / 'raw_pdf'

    print("=" * 60)
    print("PURITYPROP DATA INGESTION PIPELINE")
    print("=" * 60)

    all_records = []

    # Process JSON files
    if json_dir.exists():
        json_files = list(json_dir.glob('*.json'))
        print(f"\nFound {len(json_files)} JSON files")
        for f in json_files:
            records = parse_json_file(str(f))
            all_records.extend(records)

    # Process PDF files
    if pdf_dir.exists():
        pdf_files = list(pdf_dir.glob('*.pdf'))
        print(f"\nFound {len(pdf_files)} PDF files")
        for f in pdf_files:
            records = parse_pdf_file(str(f))
            all_records.extend(records)

    if not all_records:
        print("\n⚠️ No records found!")
        print(f"  Place JSON files in: {json_dir}")
        print(f"  Place PDF files in: {pdf_dir}")
        print("\n  Example JSON format:")
        print('  [')
        print('    {"locality": "anna nagar", "district": "chennai",')
        print('     "price_sqft": 9500, "area_sqft": 2400,')
        print('     "asset_type": "land", "date": "2024-08-15"},')
        print('  ]')
        return

    # Summary before insert
    print(f"\n{'─'*60}")
    print(f"TOTAL RECORDS TO INSERT: {len(all_records)}")

    # Show sample
    districts = set(r['district'] for r in all_records)
    localities = set(r['locality'] for r in all_records)
    print(f"Districts: {', '.join(sorted(districts))}")
    print(f"Localities: {len(localities)} unique")
    print(f"Date range: {min(r['registration_date'] for r in all_records)} to {max(r['registration_date'] for r in all_records)}")

    # Insert
    print(f"\nInserting into database...")
    inserted = await insert_records(all_records)
    print(f"\n✅ Inserted: {inserted} records")
    print(f"⏭️ Skipped: {len(all_records) - inserted} records")

    # Verify
    async with get_db_context() as session:
        total = await session.execute(text("SELECT COUNT(*) FROM registry_transactions"))
        print(f"\nTotal records in registry_transactions: {total.scalar()}")


if __name__ == "__main__":
    asyncio.run(main())
