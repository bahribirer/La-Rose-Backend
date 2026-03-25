import asyncio, re, unicodedata
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.core.database import db

def slugify(text):
    tr_map = str.maketrans('ğĞışİöÖüÜçÇ', 'gGisIoOuUcC')
    text = text.translate(tr_map)
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^\w\s-]', '', text.lower())
    text = re.sub(r'[\s_-]+', '-', text)
    return text.strip('-')[:80]

async def run():
    docs = await db.products.find(
        {"$or": [{"slug": {"$exists": False}}, {"slug": ""}]},
        {"_id": 0, "id": 1, "name": 1}
    ).to_list(length=None)

    updated = 0
    for d in docs:
        slug = slugify(d.get("name", d["id"]))
        await db.products.update_one({"id": d["id"]}, {"$set": {"slug": slug}})
        print(f"✅ {d['id']} → {slug}")
        updated += 1
    print(f"\nToplam: {updated} ürün slug eklendi")

if __name__ == "__main__":
    asyncio.run(run())
