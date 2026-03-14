import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

async def find_all_old_names():
    uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/rosap_db")
    client = AsyncIOMotorClient(uri)
    db = client.get_default_database()

    old_names = ["Şampiyonlar Ligi", "Süper Lig", "1. Lig"]
    
    collections = await db.list_collection_names()
    print(f"Checking {len(collections)} collections...")

    for coll_name in collections:
        # Search for any field that matches the old names
        # Since we don't know the schema for all collections, we use a regex or $or on common fields
        # But even better, we check if any document contains the string in any field? 
        # MongoDB doesn't have a global string search easily, so we checks common fields and also do a full scan if needed.
        
        found = False
        async for doc in db[coll_name].find({}):
            doc_str = str(doc)
            for old_name in old_names:
                if old_name in doc_str:
                    print(f"FOUND '{old_name}' in collection '{coll_name}', ID: {doc.get('_id')}")
                    # Print the doc to see the field
                    print(f"  Field(s): {[k for k,v in doc.items() if str(v) == old_name]}")
                    found = True
                    break
            if found: # Just find one per collection to be fast, or find all?
                pass
                
    print("\nScan completed.")

if __name__ == "__main__":
    asyncio.run(find_all_old_names())
