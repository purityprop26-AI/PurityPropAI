import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load env vars if present (local dev)
load_dotenv()

async def check_users():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ Error: DATABASE_URL environment variable is not set.")
        return

    try:
        client = AsyncIOMotorClient(database_url)
        db = client["real_estate_ai"]
        
        # Count users
        user_count = await db.user.count_documents({})
        print(f"📊 Total Users: {user_count}")
        
        if user_count > 0:
            print("\n👥 User Details:")
            async for user in db.user.find({}, {"hashed_password": 0}):  # Exclude password
                print(f"  - Name: {user.get('name')}")
                print(f"    Email: {user.get('email')}")
                print(f"    Created: {user.get('created_at')}")
                print()
        else:
            print("\n⚠️ No users found in database yet.")
            
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(check_users())
