# app/sales/cleanup.py
from bson import ObjectId
from app.core.database import db



async def delete_user_sales(user_id: ObjectId):
    reports = await db.sales_reports.find(
        {"user_id": user_id},
        {"_id": 1}
    ).to_list(None)

    report_ids = [r["_id"] for r in reports]

    if report_ids:
        await db.sales_items.delete_many({
            "report_id": {"$in": report_ids}
        })

    await db.sales_reports.delete_many({"user_id": user_id})
