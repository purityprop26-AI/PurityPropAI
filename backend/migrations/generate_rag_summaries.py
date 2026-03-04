"""
PurityProp — RAG Document Generator
=====================================

Phase 4: Generates 300-500 word locality summaries from property_price_trends data.
These documents are optimized for vector search (Hybrid RAG).

Run: python -m migrations.generate_rag_summaries
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from sqlalchemy import text
from app.core.database import get_db_context


def format_price(value):
    """Format price for human readability."""
    if value is None:
        return "N/A"
    if value >= 10_000_000:
        return f"₹{value / 10_000_000:.2f} Cr"
    if value >= 100_000:
        return f"₹{value / 100_000:.1f} Lakhs"
    return f"₹{value:,.0f}"


def generate_summary(locality_name: str, region: str, city: str, trends: list) -> str:
    """
    Generate a 300-500 word locality summary for RAG retrieval.

    Args:
        locality_name: Normalized locality name
        region: Region (e.g. "South Chennai")
        city: City name
        trends: List of dicts with year-wise pricing data
    """
    # Separate observed vs forecast
    observed = sorted([t for t in trends if t['data_type'] == 'observed'], key=lambda x: x['year'])
    forecast = sorted([t for t in trends if t['data_type'] == 'forecast'], key=lambda x: x['year'])

    display_name = locality_name.replace('_', ' ').title()

    parts = []

    # Header
    parts.append(f"Locality: {display_name}")
    parts.append(f"Region: {region}")
    parts.append(f"City: {city}")
    parts.append("")

    # Date range
    all_years = sorted(set(t['year'] for t in trends))
    if all_years:
        parts.append(f"Real Estate Trend Summary ({all_years[0]}–{all_years[-1]}):")
        parts.append("")

    # Land price trends (observed)
    if observed:
        first = observed[0]
        last = observed[-1]
        if first.get('land_price_avg') and last.get('land_price_avg'):
            growth = ((last['land_price_avg'] - first['land_price_avg']) / first['land_price_avg']) * 100
            parts.append(
                f"Land prices increased from {format_price(first['land_price_avg'])} per sq.ft "
                f"in {first['year']} to {format_price(last['land_price_avg'])} in {last['year']}, "
                f"showing a growth of {growth:.1f}% over {last['year'] - first['year']} years."
            )

        # Land price range
        if last.get('land_price_min') and last.get('land_price_max'):
            parts.append(
                f"Current land price range: {format_price(last['land_price_min'])} – "
                f"{format_price(last['land_price_max'])} per sq.ft."
            )
        parts.append("")

    # Forecast
    if forecast:
        last_forecast = forecast[-1]
        if last_forecast.get('land_price_avg'):
            parts.append(
                f"Projected land price for {last_forecast['year']}: "
                f"{format_price(last_forecast['land_price_avg'])} per sq.ft."
            )
            if forecast[0].get('land_price_avg') and last_forecast.get('land_price_avg'):
                parts.append(
                    f"Forecast range: {format_price(forecast[0]['land_price_avg'])} "
                    f"({forecast[0]['year']}) to {format_price(last_forecast['land_price_avg'])} "
                    f"({last_forecast['year']})."
                )
        parts.append("")

    # Apartment prices
    apt_data = [t for t in observed if t.get('apartment_price')]
    if apt_data:
        first_apt = apt_data[0]
        last_apt = apt_data[-1]
        if first_apt['apartment_price'] and last_apt['apartment_price']:
            parts.append(
                f"Apartment prices rose from {format_price(first_apt['apartment_price'])} per sq.ft "
                f"in {first_apt['year']} to {format_price(last_apt['apartment_price'])} in {last_apt['year']}."
            )
        parts.append("")

    # Guideline values
    gv_data = [t for t in observed if t.get('guideline_price')]
    if gv_data:
        first_gv = gv_data[0]
        last_gv = gv_data[-1]
        if first_gv['guideline_price'] and last_gv['guideline_price']:
            parts.append(
                f"Government guideline value increased from {format_price(first_gv['guideline_price'])} "
                f"to {format_price(last_gv['guideline_price'])} per sq.ft."
            )
        parts.append("")

    # Ground value
    gnd_data = [t for t in observed if t.get('ground_value')]
    if gnd_data:
        last_gnd = gnd_data[-1]
        parts.append(
            f"Ground value (2400 sq.ft): {format_price(last_gnd['ground_value'])} as of {last_gnd['year']}."
        )
        parts.append("")

    # Negotiation range
    neg_data = [t for t in observed if t.get('negotiation_min') is not None]
    if neg_data:
        first_neg = neg_data[0]
        last_neg = neg_data[-1]
        if first_neg.get('negotiation_max') and last_neg.get('negotiation_max'):
            parts.append(
                f"Negotiation margin changed from "
                f"{first_neg['negotiation_min']:.0f}%–{first_neg['negotiation_max']:.0f}% "
                f"in {first_neg['year']} to "
                f"{last_neg['negotiation_min']:.0f}%–{last_neg['negotiation_max']:.0f}% "
                f"in {last_neg['year']}."
            )
        parts.append("")

    # Market context
    parts.append(
        f"{display_name} is located in the {region} corridor of {city}, Tamil Nadu. "
        f"This area has shown {'strong' if len(observed) >= 3 else 'moderate'} "
        f"price appreciation driven by infrastructure development and demand growth."
    )

    return "\n".join(parts)


def build_metadata(locality_name: str, region: str, city: str, trends: list) -> dict:
    """Build metadata JSON for the RAG summary."""
    observed = [t for t in trends if t['data_type'] == 'observed']
    all_years = sorted(set(t['year'] for t in trends))

    price_growth = None
    if len(observed) >= 2:
        first = observed[0]
        last = observed[-1]
        if first.get('land_price_avg') and last.get('land_price_avg') and first['land_price_avg'] > 0:
            price_growth = round(
                ((last['land_price_avg'] - first['land_price_avg']) / first['land_price_avg']) * 100, 1
            )

    return {
        "city": city,
        "region": region,
        "locality": locality_name,
        "years_covered": f"{all_years[0]}–{all_years[-1]}" if all_years else None,
        "observed_years": len(observed),
        "forecast_years": len(trends) - len(observed),
        "price_growth_pct": price_growth,
        "data_source": "pdf_import",
        "has_apartment_data": any(t.get('apartment_price') for t in trends),
        "has_guideline_data": any(t.get('guideline_price') for t in trends),
    }


async def generate_and_store_summaries():
    """Generate RAG summaries for all localities in property_price_trends."""
    print("Generating RAG summaries...")

    async with get_db_context() as session:
        # Get all localities with their city/region info
        result = await session.execute(text("""
            SELECT l.locality_id, l.locality_name, r.region_name, c.city_name
            FROM localities l
            JOIN regions r ON l.region_id = r.region_id
            JOIN cities c ON r.city_id = c.city_id
            ORDER BY c.city_name, r.region_name, l.locality_name
        """))
        localities = result.fetchall()
        print(f"  Found {len(localities)} localities")

        generated = 0
        for loc_id, loc_name, region_name, city_name in localities:
            # Get price trends for this locality
            trends_result = await session.execute(text("""
                SELECT year, land_price_min, land_price_max, land_price_avg,
                       apartment_price, market_price, guideline_price, ground_value,
                       negotiation_min, negotiation_max, data_type
                FROM property_price_trends
                WHERE locality_id = :lid
                ORDER BY year
            """), {"lid": loc_id})

            trends = [
                {
                    'year': r[0],
                    'land_price_min': float(r[1]) if r[1] else None,
                    'land_price_max': float(r[2]) if r[2] else None,
                    'land_price_avg': float(r[3]) if r[3] else None,
                    'apartment_price': float(r[4]) if r[4] else None,
                    'market_price': float(r[5]) if r[5] else None,
                    'guideline_price': float(r[6]) if r[6] else None,
                    'ground_value': float(r[7]) if r[7] else None,
                    'negotiation_min': float(r[8]) if r[8] else None,
                    'negotiation_max': float(r[9]) if r[9] else None,
                    'data_type': r[10],
                }
                for r in trends_result.fetchall()
            ]

            if not trends:
                continue

            # Generate summary
            summary = generate_summary(loc_name, region_name, city_name, trends)
            metadata = build_metadata(loc_name, region_name, city_name, trends)

            # Insert/update in locality_rag_summaries
            try:
                await session.execute(text("""
                    INSERT INTO locality_rag_summaries
                        (locality_name, region, city, text_summary, metadata)
                    VALUES (:loc, :region, :city, :summary, :meta)
                    ON CONFLICT (locality_name, city)
                    DO UPDATE SET text_summary = EXCLUDED.text_summary,
                                  metadata = EXCLUDED.metadata,
                                  updated_at = NOW()
                """), {
                    "loc": loc_name,
                    "region": region_name,
                    "city": city_name,
                    "summary": summary,
                    "meta": json.dumps(metadata),
                })
                generated += 1

                if generated % 25 == 0:
                    print(f"  Progress: {generated}/{len(localities)} summaries generated")
            except Exception as e:
                print(f"  Error for {loc_name}: {e}")

    print(f"  ✅ Generated {generated} RAG summaries")
    return generated


async def main():
    print("=" * 60)
    print("PURITYPROP — RAG SUMMARY GENERATOR")
    print("=" * 60)

    count = await generate_and_store_summaries()

    # Show sample
    async with get_db_context() as session:
        result = await session.execute(text("""
            SELECT locality_name, city, LENGTH(text_summary) as len
            FROM locality_rag_summaries
            ORDER BY locality_name
            LIMIT 5
        """))
        print("\nSample summaries:")
        for row in result.fetchall():
            print(f"  {row[0]} ({row[1]}): {row[2]} chars")

        # Show one full summary
        sample = await session.execute(text("""
            SELECT text_summary FROM locality_rag_summaries LIMIT 1
        """))
        row = sample.fetchone()
        if row:
            print(f"\n--- SAMPLE RAG DOCUMENT ---")
            print(row[0][:800])
            print("...")

    print("\n" + "=" * 60)
    print("RAG SUMMARY GENERATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
