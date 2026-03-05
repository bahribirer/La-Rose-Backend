import asyncio
import os
import sys

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))

from app.core.database import db

PRODUCT_MAPPING = {
    "3770008214220": {"name": "CLEANSING OIL 200 ML", "category": "Yüz Temizleme"},
    "3770008214046": {"name": "CLEANSING FOAM 150 ML", "category": "Yüz Temizleme"},
    "3770008214237": {"name": "GENTLE SCRUB 75 ML", "category": "Yüz Temizleme"},
    "3770008214053": {"name": "TONIC LOTION 200 ML", "category": "Yüz Temizleme"},
    "3770008214152": {"name": "PURIF. MASK 75 ML", "category": "Arındırıcı Bakım"},
    "3770008214022": {"name": "MOIST. MASK 75 ML", "category": "Nemlendirici Bakım"},
    "3770008214008": {"name": "HYDRATING CREAM 60 ML", "category": "Nemlendirici Bakım"},
    "3770008214015": {"name": "HYDRATING GEL 60 ML", "category": "Nemlendirici Bakım"},
    "3770008214374": {"name": "PULPE DE VIE CREAM 40 ML", "category": "Nemlendirici Bakım"},
    "3770008214176": {"name": "REP. CREAM 40 ML", "category": "Nemlendirici Bakım"},
    "3770008214183": {"name": "NOURISHING CREAM 60 ML", "category": "Besleyici Bakım"},
    "3770008214480": {"name": "REGEN. MASK 75 ML", "category": "Yenileyici Bakım"},
    "3770008214305": {"name": "EYE CONTOUR 15 ML", "category": "Göz Çevresi Bakımı"},
    "3770008214503": {"name": "ANTI-IMPERF. SERUM 30 ML", "category": "Serumlar"},
    "3770008214039": {"name": "VIT. RADIANCE SERUM 30 ML", "category": "Serumlar"},
    "3770008214534": {"name": "REP. SERUM 30 ML", "category": "Serumlar"},
    "3770008214367": {"name": "NOUR. FACE OIL 30 ML", "category": "Yüz Yağları"},
    "3770008214060": {"name": "SHOWER CREAM 200 ML", "category": "Vücut Bakımı"},
    "3770008214114": {"name": "BODY SCRUB 200 ML", "category": "Vücut Bakımı"},
    "3770008214077": {"name": "MOIST. BODY MILK 200 ML", "category": "Vücut Bakımı"},
    "3770008214473": {"name": "REP. BODY BALM 200 ML", "category": "Vücut Bakımı"},
    "3770008214084": {"name": "HAND CREAM 50 ML", "category": "El ve Tırnak Bakımı"},
    "3770008214145": {"name": "REGEN. HAND CREAM 50 ML", "category": "El ve Tırnak Bakımı"},
    "3770008214091": {"name": "DEODORANT 50 ML", "category": "Kişisel Hijyen"},
    "3770008214190": {"name": "SUN CREAM SPF30 50 ML", "category": "Güneş Bakımı"},
    "3770008214206": {"name": "SUN CREAM SPF50 50 ML", "category": "Güneş Bakımı"},
    "3770008214213": {"name": "STICK SPF50 15 ML", "category": "Güneş Bakımı"},
    "3770008214329": {"name": "CLEANSING GEL KIDS 400 ML", "category": "Bebek & Çocuk"},
    "3770008214336": {"name": "MOIST. CREAM KIDS 200 ML", "category": "Bebek & Çocuk"},
    "3770008214350": {"name": "MASSAGE OIL KIDS 100 ML", "category": "Bebek & Çocuk"},
}

async def migrate():
    print("Starting product name migration...")
    updated_count = 0
    
    for gtin, meta in PRODUCT_MAPPING.items():
        res = await db.products.update_one(
            {"id": gtin},
            {"$set": {
                "name": meta["name"],
                "category": meta["category"],
                "gtin": gtin
            }}
        )
        if res.modified_count > 0:
            print(f"Updated: {meta['name']}")
            updated_count += 1
        elif res.matched_count > 0:
            print(f"Already updated or no change: {meta['name']}")
        else:
            print(f"Warning: Product {gtin} not found in database.")
            
    print(f"Migration completed. {updated_count} products updated.")

if __name__ == "__main__":
    asyncio.run(migrate())
