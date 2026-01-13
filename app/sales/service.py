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

    for item in items:
        miktar = item.miktar or 0
        maliyet = item.maliyet or 0.0

        # 🔥 PROFIT KURALI
        ecz_kar = item.ecz_kar if item.ecz_kar is not None else 0.0

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
    total_items = sum(i["miktar"] for i in normalized_items)
    total_profit = sum(i["ecz_kar"] for i in normalized_items)
    total_cost = sum(i["maliyet"] * i["miktar"] for i in normalized_items)

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
    "unit_price": i.get("birim_fiyat"),
    "total_price": i.get("tutar"),

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
