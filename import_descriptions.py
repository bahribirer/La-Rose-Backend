"""
Excel'deki ürün açıklamalarını MongoDB'ye yükler.
Çalıştır: python import_descriptions.py
"""
import asyncio
import pandas as pd
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "rosap_db"
EXCEL_PATH = "/Users/bahribirer/Downloads/La Rosee Ürün detayları revize 2.xlsx"

async def main():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]

    df = pd.read_excel(EXCEL_PATH)

    updated = 0
    not_found = []

    for _, row in df.iterrows():
        barcode = str(row["Ürün Barkod Numarası"]).strip()
        aciklama = str(row.get("Ürün Açıklaması", "") or "").strip()
        detay = str(row.get("Ürün detayları", "") or "").strip()

        # Açıklama + detayları birleştir
        full_desc = aciklama
        if detay and detay.lower() != "nan":
            full_desc = aciklama + "\n\n" + detay if aciklama else detay

        if not full_desc or full_desc.lower() == "nan":
            continue

        res = await db.products.update_one(
            {"id": barcode},
            {"$set": {"description": full_desc}}
        )

        if res.matched_count > 0:
            updated += 1
            print(f"✅ {barcode} güncellendi")
        else:
            not_found.append(barcode)
            print(f"⚠️  {barcode} bulunamadı")

    print(f"\n✔ {updated} ürün güncellendi.")
    if not_found:
        print(f"⚠ Bulunamayan barkodlar ({len(not_found)}): {not_found}")

    client.close()

asyncio.run(main())
