import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

async def list_colls():
    uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/rosap_db")
    client = AsyncIOMotorClient(uri)
    db = client.get_default_database()
    collections = await db.list_collection_names()
    print(collections)

if __name__ == "__main__":
    asyncio.run(list_colls())
