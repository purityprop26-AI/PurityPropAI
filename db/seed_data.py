"""
SUPABASE-NATIVE REAL ESTATE INTELLIGENCE SYSTEM
Data Seeder — Sample Chennai Real Estate Properties

Seeds realistic property data into the database for demonstration
and testing purpose with vector embeddings, PostGIS locations, and JSONB attributes.
"""
import asyncio
import asyncpg
import json
import os
import random
import sys

# Chennai Localities with coordinates
LOCALITIES = [
    ("T Nagar", 13.0404, 80.2340, 7500, 12000),
    ("Anna Nagar", 13.0850, 80.2100, 6000, 10000),
    ("Adyar", 13.0067, 80.2568, 8000, 14000),
    ("Velachery", 12.9815, 80.2180, 5000, 8500),
    ("Thiruvanmiyur", 12.9833, 80.2632, 7000, 11000),
    ("Porur", 13.0382, 80.1559, 4500, 7500),
    ("Tambaram", 12.9250, 80.1280, 3500, 6000),
    ("Chromepet", 12.9512, 80.1399, 4000, 6500),
    ("Guindy", 13.0067, 80.2206, 6500, 10500),
    ("OMR (Sholinganallur)", 12.9010, 80.2279, 5500, 9000),
    ("Mylapore", 13.0339, 80.2690, 9000, 15000),
    ("Nungambakkam", 13.0599, 80.2425, 8500, 14000),
    ("Mogappair", 13.0730, 80.1816, 4500, 7000),
    ("Perambur", 13.1133, 80.2360, 5000, 7500),
    ("Kodambakkam", 13.0476, 80.2285, 6000, 9500),
    ("Ashok Nagar", 13.0387, 80.2114, 6500, 10000),
    ("KK Nagar", 13.0350, 80.2050, 6000, 9500),
    ("Besant Nagar", 13.0002, 80.2666, 9000, 16000),
    ("ECR (Palavakkam)", 12.9600, 80.2590, 6000, 10000),
    ("Pallikaranai", 12.9370, 80.2050, 4500, 7000),
]

PROPERTY_TYPES = ["apartment", "villa", "plot", "house", "penthouse"]
LISTING_TYPES = ["sale", "rent"]
BHK_CONFIG = [1, 2, 3, 4, 5]

AMENITIES_POOL = [
    "swimming_pool", "gym", "playground", "clubhouse", "garden",
    "security_24x7", "power_backup", "car_parking", "lift",
    "rain_water_harvesting", "solar_panels", "indoor_games",
    "jogging_track", "party_hall", "cctv", "intercom",
    "gas_pipeline", "sewage_treatment", "fire_safety", "vastu_compliant",
]

NEARBY_PLACES_POOL = [
    {"name": "Metro Station", "type": "transit", "weight": 2.0},
    {"name": "Bus Stop", "type": "transit", "weight": 1.5},
    {"name": "PSBB School", "type": "school", "weight": 1.5},
    {"name": "DAV School", "type": "school", "weight": 1.5},
    {"name": "Apollo Hospital", "type": "hospital", "weight": 1.5},
    {"name": "Fortis Hospital", "type": "hospital", "weight": 1.0},
    {"name": "Saravana Stores", "type": "shopping", "weight": 1.0},
    {"name": "Phoenix Mall", "type": "shopping", "weight": 1.0},
    {"name": "Marina Beach", "type": "landmark", "weight": 0.5},
    {"name": "IIT Madras", "type": "education", "weight": 1.0},
]

BUILDERS = [
    "Aparna Construction", "Casagrand", "DRA Homes", "KG Foundations",
    "Navin's", "Olympia Group", "Prestige Group", "Puravankara",
    "Radiance Realty", "Shriram Properties", "Sobha Limited",
    "SP Foundations", "Tata Housing", "TVS Emerald", "VGN Projects",
]


def generate_property(idx: int):
    """Generate a single realistic property."""
    locality, lat, lon, price_low, price_high = random.choice(LOCALITIES)
    prop_type = random.choice(PROPERTY_TYPES)
    listing_type = "sale" if random.random() < 0.8 else "rent"

    bhk = random.choice(BHK_CONFIG)
    if prop_type == "plot":
        bhk = 0

    # Area based on BHK
    if bhk == 0:
        carpet_area = random.randint(600, 2400)
    elif bhk == 1:
        carpet_area = random.randint(450, 650)
    elif bhk == 2:
        carpet_area = random.randint(700, 1100)
    elif bhk == 3:
        carpet_area = random.randint(1000, 1600)
    elif bhk == 4:
        carpet_area = random.randint(1500, 2500)
    else:
        carpet_area = random.randint(2000, 3500)

    price_per_sqft = random.randint(price_low, price_high)
    if listing_type == "rent":
        price = random.randint(12000, 80000)
    else:
        price = carpet_area * price_per_sqft

    builder = random.choice(BUILDERS)
    project_name = f"{builder} {random.choice(['Heights', 'Towers', 'Residency', 'Enclave', 'Gardens', 'Plaza', 'Manor', 'Nest', 'Haven', 'Vista'])}"

    title = f"{bhk} BHK {prop_type.replace('_', ' ').title()} in {locality}" if bhk > 0 else f"{carpet_area} Sqft {prop_type.replace('_', ' ').title()} in {locality}"

    # Random jitter for location
    lat_adj = lat + random.uniform(-0.01, 0.01)
    lon_adj = lon + random.uniform(-0.01, 0.01)

    # Amenities
    num_amenities = random.randint(3, 10)
    amenities = random.sample(AMENITIES_POOL, min(num_amenities, len(AMENITIES_POOL)))

    # Nearby places with distances
    num_nearby = random.randint(2, 6)
    nearby = []
    for place in random.sample(NEARBY_PLACES_POOL, min(num_nearby, len(NEARBY_PLACES_POOL))):
        nearby.append({
            "name": place["name"],
            "type": place["type"],
            "distance_km": round(random.uniform(0.2, 5.0), 2),
            "weight": place["weight"],
        })

    # Price history (last 5 years)
    price_history = []
    base = price * random.uniform(0.6, 0.8)
    for year in range(2021, 2027):
        base = base * random.uniform(1.03, 1.15)
        price_history.append({
            "year": year,
            "price": round(base),
            "price_per_sqft": round(base / carpet_area) if carpet_area > 0 else 0,
        })

    # Attributes
    attributes = {
        "bhk": bhk,
        "bathrooms": max(1, bhk),
        "balconies": random.randint(0, 3),
        "floor": random.randint(1, 20),
        "total_floors": random.randint(5, 25),
        "age_years": random.randint(0, 15),
        "facing": random.choice(["east", "west", "north", "south", "north_east", "south_east"]),
        "furnished": random.choice(["unfurnished", "semi_furnished", "fully_furnished"]),
        "parking": random.randint(0, 2),
        "water_source": random.choice(["borewell", "corporation", "both"]),
        "power_backup": random.choice([True, False]),
        "rera_registered": random.choice([True, False]),
    }

    # Generate a random 384-dim vector (simulating embedding)
    embedding = [round(random.gauss(0, 0.1), 6) for _ in range(384)]

    return {
        "title": title,
        "slug": title.lower().replace(" ", "-").replace("'", "")[:100] + f"-{idx}",
        "description": f"Beautiful {bhk} BHK {prop_type.replace('_', ' ')} located in the heart of {locality}, Chennai. "
                       f"Built by {builder}, this property offers {carpet_area} sqft of living space with modern amenities. "
                       f"{'RERA registered. ' if attributes['rera_registered'] else ''}"
                       f"{'Fully furnished. ' if attributes['furnished'] == 'fully_furnished' else ''}",
        "property_type": prop_type,
        "listing_type": listing_type,
        "price": price,
        "price_per_sqft": price_per_sqft if listing_type == "sale" else None,
        "carpet_area_sqft": carpet_area,
        "bedrooms": bhk if bhk > 0 else None,
        "bathrooms": attributes["bathrooms"] if bhk > 0 else None,
        "locality": locality,
        "city": "Chennai",
        "state": "Tamil Nadu",
        "pincode": f"6000{random.randint(10, 99)}",
        "lat": lat_adj,
        "lon": lon_adj,
        "builder_name": builder,
        "project_name": project_name,
        "attributes": json.dumps(attributes),
        "amenities": json.dumps(amenities),
        "nearby_places": json.dumps(nearby),
        "price_history": json.dumps(price_history),
        "embedding": f"[{','.join(str(v) for v in embedding)}]",
        "is_active": True,
    }


async def seed_data(count: int = 100):
    """Seed the database with sample properties."""
    db_url = os.environ.get("DATABASE_URL", "").replace("+asyncpg", "").replace("postgresql+asyncpg", "postgresql")
    if not db_url or "asyncpg" in db_url:
        db_url = "postgresql://postgres:puritypropAI26@db.rqqkhmbayxnsoyxhpfmk.supabase.co:5432/postgres"

    conn = await asyncpg.connect(db_url, ssl="require")

    print(f"Connected to database")
    print(f"Generating {count} sample properties...")

    # Clear existing sample data (optional)
    existing = await conn.fetchval("SELECT count(*) FROM properties")
    print(f"Existing properties: {existing}")

    inserted = 0
    for i in range(count):
        prop = generate_property(i)

        try:
            await conn.execute("""
                INSERT INTO properties (
                    title, slug, description, property_type, listing_type,
                    price, price_per_sqft, carpet_area_sqft,
                    bedrooms, bathrooms,
                    locality, city, state, pincode,
                    location,
                    builder_name, project_name,
                    attributes, amenities, nearby_places, price_history,
                    embedding
                ) VALUES (
                    $1, $2, $3, $4, $5,
                    $6, $7, $8,
                    $9, $10,
                    $11, $12, $13, $14,
                    ST_SetSRID(ST_MakePoint($15, $16), 4326),
                    $17, $18,
                    $19::jsonb, $20::jsonb, $21::jsonb, $22::jsonb,
                    $23::vector
                )
            """,
                prop["title"], prop["slug"], prop["description"],
                prop["property_type"], prop["listing_type"],
                prop["price"], prop["price_per_sqft"], prop["carpet_area_sqft"],
                prop["bedrooms"], prop["bathrooms"],
                prop["locality"], prop["city"], prop["state"], prop["pincode"],
                prop["lon"], prop["lat"],
                prop["builder_name"], prop["project_name"],
                prop["attributes"], prop["amenities"],
                prop["nearby_places"], prop["price_history"],
                prop["embedding"],
            )
            inserted += 1
        except Exception as e:
            print(f"  Error inserting property {i}: {e}")

    # Verify seeded data
    print("Verifying seeded data...")

    total = await conn.fetchval("SELECT count(*) FROM properties")
    await conn.close()

    print(f"\n✓ Seeded {inserted}/{count} properties")
    print(f"✓ Total properties in database: {total}")

    return inserted


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    asyncio.run(seed_data(count))
