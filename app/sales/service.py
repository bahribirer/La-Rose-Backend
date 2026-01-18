from datetime import datetime
from app.core.database import db


async def save_scan_report(
    user: dict,
    items,
    competition_id=None,
    is_competition_report=False,
):
    """
    SALES SERVICE = finansal gerçeklik otoritesi
    """

    # ================== NORMALIZE ITEMS ==================
    normalized_items = []

    # 🔥 RECOVERY: TELEFON VERIYI SILIYORSA HAFIZADAN GETIR
    # En son taranan ham raporu bul (son 1 saat içindeki)
    last_scan = await db.scan_raw_reports.find_one(
        {"source": "ocr"},
        sort=[("createdAt", -1)]
    )

    recovery_map = {}
    if last_scan:
        print("🧠 RECOVERY MODE: Found Raw Scan", last_scan.get("_id"))
        for ri in last_scan.get("items", []):
            if ri.get("urun_id"):
                recovery_map[ri["urun_id"]] = {
                    "ecz_kar": ri.get("ecz_kar", 0.0),
                    "maliyet": ri.get("maliyet", 0.0),
                    "birim_fiyat": ri.get("birim_fiyat"),
                    "tutar": ri.get("tutar"),
                }

    for item in items:
        miktar = item.miktar or 0
        
        # 1. Telefondan gelen veri
        ecz_kar = item.ecz_kar
        maliyet = item.maliyet or 0.0

        # 2. Telefondan boş geldiyse (0 veya None), hafızadan bak
        if (ecz_kar is None or ecz_kar == 0) and item.urun_id in recovery_map:
            print(f"🔧 RESTORING PROFIT for {item.urun_id}")
            rec = recovery_map[item.urun_id]
            ecz_kar = rec.get("ecz_kar") or 0.0
            maliyet = rec.get("maliyet") or 0.0

            # Admin alanlarını da kurtar
            if item.birim_fiyat is None:
                item.birim_fiyat = rec["birim_fiyat"]
            if item.tutar is None:
                item.tutar = rec["tutar"]

        ecz_kar = ecz_kar if ecz_kar is not None else 0.0

        normalized_items.append({
            "urun_id": item.urun_id,
    "urun_name": item.urun_name,
    "miktar": miktar,

    # 🔥 ADMIN
    "birim_fiyat": item.birim_fiyat,
    "tutar": item.tutar,

    # mevcut
    "maliyet": maliyet,
    "ecz_kar": ecz_kar,
    "match_confidence": item.match_confidence,
})



    # ================== SUMMARY ==================
    total_items = sum((i.get("miktar") or 0) for i in normalized_items)
    
    total_profit = sum(
        (i.get("ecz_kar") or 0.0) 
        for i in normalized_items
    )
    
    total_cost = sum(
        (i.get("maliyet") or 0.0) * (i.get("miktar") or 0) 
        for i in normalized_items
    )

    # ================== REPORT NAME ==================
    profile = await db.user_profiles.find_one(
        {"user_id": user["_id"]}
    )

    pharmacy_name = (
        profile.get("pharmacy_name")
        if profile and profile.get("pharmacy_name")
        else None
    )

    pharmacy_name = (
        pharmacy_name
        or user.get("full_name")
        or user.get("email")
        or "Rapor"
    )

    today_str = datetime.now().strftime("%d.%m.%Y")
    report_name = f"{pharmacy_name} - {today_str}"

    # ================== REPORT ==================
    report = {
        "user_id": user["_id"],
        "name": report_name,
        "type": "scan",
        "source": "ocr",
        "createdAt": datetime.utcnow(),

        "competition_id": competition_id,
        "is_competition_report": is_competition_report,

        "summary": {
            "total_items": total_items,
            "total_profit": total_profit,
            "total_cost": total_cost,
        }
    }

    result = await db.sales_reports.insert_one(report)
    report_id = result.inserted_id

    # ================== ITEMS ==================
    docs = []
    for i in normalized_items:
        docs.append({
    "report_id": report_id,
    "productId": i["urun_id"],
    "productName": i["urun_name"],
    "quantity": i["miktar"],

    # 🔥 ADMIN
    "unitPrice": i.get("birim_fiyat"),
    "totalPrice": i.get("tutar"),

    # mevcut
    "profit": i["ecz_kar"],
    "cost": i["maliyet"],
    "confidence": i["match_confidence"],
})


    if docs:
        await db.sales_items.insert_many(docs)

    return {
        "report_id": str(report_id),
        "name": report_name,
        "item_count": len(docs),
    }
