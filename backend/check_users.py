```python
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

ATLAS_URL = "mongodb+srv://naveenkumart949_db_user:Naveenkumar@cluster0.dch6vry.mongodb.net/purityprop?retryWrites=true&w=majority&tls=true&tlsAllowInvalidCertificates=true"

async def check_users():
    try:
        client = AsyncIOMotorClient(ATLAS_URL)
        db = client["purityprop"]
        
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
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_users())
