import pandas as pd
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

from app.pharmacies.constants import REGION_REPRESENTATIVES
from app.pharmacies.utils import normalize_text

# ================= CONFIG =================

MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "rosap_db"

EXCEL_PATH = "La Rosee Eczane Bölge Listesi.xlsx"

PHARMACY_COL = "ECZANE ADI"
LOCATION_COL = "LOKASYON"

# ================= MAIN =================

async def run_import():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    pharmacies = db.pharmacies

    # 🔥 TÜM SHEET'LERİ OKU
    sheets = pd.read_excel(EXCEL_PATH, sheet_name=None)

    inserted = 0
    updated = 0

    for sheet_name, df in sheets.items():
        region = sheet_name.strip()  # Bölge 1 / Bölge 2 ...

        representative = REGION_REPRESENTATIVES.get(region)
        if not representative:
            print(f"⚠️ Mümessil yok, atlandı: {region}")
            continue

        print(f"\n📍 Bölge işleniyor: {region}")

        for _, row in df.iterrows():
            raw_pharmacy = row.get(PHARMACY_COL)
            raw_location = row.get(LOCATION_COL)

            # 🔹 Geçersiz / açıklama satırları
            if not isinstance(raw_pharmacy, str):
                continue

            if "sorumlusu" in raw_pharmacy.lower():
                continue

            if not isinstance(raw_location, str):
                continue

            pharmacy_name = raw_pharmacy.strip()
            district = raw_location.strip()

            normalized_name = normalize_text(pharmacy_name)

            doc = {
                "pharmacy_name": pharmacy_name,
                "normalized_name": normalized_name,
                "district": district,
                "region": region,
                "representative": {
                    "name": representative,
                },
                "updated_at": datetime.utcnow(),
            }

            result = await pharmacies.update_one(
                {"normalized_name": normalized_name},
                {
                    "$set": doc,
                    "$setOnInsert": {
                        "created_at": datetime.utcnow(),
                    },
                },
                upsert=True,
            )

            if result.upserted_id:
                inserted += 1
            else:
                updated += 1

    print("\n✅ IMPORT TAMAMLANDI")
    print(f"➕ Eklenen: {inserted}")
    print(f"♻️ Güncellenen: {updated}")

    client.close()


# ================= RUN =================

if __name__ == "__main__":
    asyncio.run(run_import())
