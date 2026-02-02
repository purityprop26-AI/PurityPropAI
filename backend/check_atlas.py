import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import sys

# Provided connection string
ATLAS_URL = "mongodb+srv://naveenkumart949_db_user:Naveenkumar@cluster0.dch6vry.mongodb.net/purityprop?retryWrites=true&w=majority&tls=true&tlsAllowInvalidCertificates=true"

async def check_connection():
    try:
        print(f"Connecting to Atlas...")
        # validatng the string format implicitly by using it
        client = AsyncIOMotorClient(ATLAS_URL, serverSelectionTimeoutMS=5000)
        
        # Force connection
        info = await client.server_info()
        print(f"✅ Connection successful! Server version: {info.get('version')}")
        
        db = client["real_estate_ai"]
        collections = await db.list_collection_names()
        print(f"Existing collections: {collections}")
        
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(check_connection())
