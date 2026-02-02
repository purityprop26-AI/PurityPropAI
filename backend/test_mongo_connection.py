"""Test MongoDB Atlas connection"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

# MongoDB Atlas Connection String
CONNECTION_STRING = "mongodb+srv://naveenkumart949_db_user:Naveenkumar@cluster0.dch6vry.mongodb.net/purityprop?retryWrites=true&w=majority&tls=true&tlsAllowInvalidCertificates=true"

async def test_connection():
    
    print("Testing MongoDB Atlas connection...")
    print(f"Connection string: {CONNECTION_STRING[:50]}...")
    
    try:
        client = AsyncIOMotorClient(
            connection_string,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000
        )
        
        # Test the connection
        await client.admin.command('ping')
        print("✅ Successfully connected to MongoDB Atlas!")
        
        # List databases
        dbs = await client.list_database_names()
        print(f"Available databases: {dbs}")
        
        client.close()
        
    except Exception as e:
        print(f"❌ Connection failed: {type(e).__name__}")
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_connection())
