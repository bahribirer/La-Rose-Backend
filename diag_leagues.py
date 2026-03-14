import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

async def check_leagues():
    uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/rosap_db")
    client = AsyncIOMotorClient(uri)
    db = client.get_default_database()

    collections = ["user_profiles", "pharmacies", "competitions", "sales_reports", "competition_participants"]

    for coll_name in collections:
        print(f"Collection: {coll_name}")
        distinct_leagues = await db[coll_name].distinct("league")
        print(f"  Distinct league values: {distinct_leagues}")
        
    print("\nChecking for documents with old names:")
    old_names = ["Şampiyonlar Ligi", "Süper Lig", "1. Lig"]
    for coll_name in collections:
        for old_name in old_names:
            count = await db[coll_name].count_documents({"league": old_name})
            if count > 0:
                print(f"  FOUND {count} documents in {coll_name} with '{old_name}'")

if __name__ == "__main__":
    asyncio.run(check_leagues())
