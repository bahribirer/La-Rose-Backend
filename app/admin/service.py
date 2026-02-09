from datetime import datetime
from typing import Optional
from app.core.database import db


# =========================
# OVERVIEW
# =========================

async def get_overview(start: datetime, end: datetime):
    pipeline = [
        {
            "$match": {
                "createdAt": {"$gte": start, "$lte": end}
            }
        },
        {
            "$group": {
                "_id": None,
                "total_reports": {"$sum": 1},
                "total_profit": {"$sum": "$summary.total_profit"},
                "total_cost": {"$sum": "$summary.total_cost"},
                "total_items": {"$sum": "$summary.total_items"},
                "total_sales": {"$sum": "$summary.total_sales"},
            }
        }
    ]

    cursor = db.sales_reports.aggregate(pipeline)
    data = await cursor.to_list(length=1)

    r = data[0] if data else {}

    return {
        "total_reports": r.get("total_reports", 0),
        "total_profit": round(r.get("total_profit", 0), 2),
        "total_revenue": round(
            r.get("total_revenue", 0) or r.get("total_sales", 0) or (r.get("total_profit", 0) + r.get("total_cost", 0)), 2
        ),
        "total_items": r.get("total_items", 0),
    }


# =========================
# TOP USERS
# =========================

async def get_top_users(start: datetime, end: datetime, limit: int = 10):
    pipeline = [
        {
            "$match": {
                "createdAt": {"$gte": start, "$lte": end}
            }
        },
        {
            "$group": {
                "_id": "$user_id",
                "total_profit": {"$sum": "$summary.total_profit"},
                "total_cost": {"$sum": "$summary.total_cost"},
                "total_items": {"$sum": "$summary.total_items"},
                "total_sales": {"$sum": "$summary.total_sales"},
            }
        },
        {"$sort": {"total_profit": -1}},
        {"$limit": limit},
    ]

    cursor = db.sales_reports.aggregate(pipeline)

    results = []
    async for r in cursor:
        user = await db.users.find_one({"_id": r["_id"]})

        results.append({
            "user_id": str(r["_id"]),
            "name": (
                user.get("full_name")
                or user.get("email")
                if user else "Kullanıcı"
            ),
            "total_profit": round(r.get("total_profit", 0), 2),
            "total_revenue": round(
                r.get("total_sales", 0) or (r.get("total_profit", 0) + r.get("total_cost", 0)), 2
            ),
            "total_items": r.get("total_items", 0),
        })

    return results


# =========================
# TOP PRODUCTS
# =========================

async def get_top_products(start: datetime, end: datetime, limit: Optional[int] = 10):
    pipeline = [
        {
            "$lookup": {
                "from": "sales_reports",
                "localField": "report_id",
                "foreignField": "_id",
                "as": "report"
            }
        },
        {"$unwind": "$report"},
        {
            "$match": {
                "report.createdAt": {"$gte": start, "$lte": end}
            }
        },
        {
            "$group": {
                "_id": {
                    "productId": "$productId",
                    "productName": "$productName",
                },
                "quantity": {"$sum": "$quantity"},
                "total_profit": {"$sum": "$profit"},
                "total_cost": {"$sum": "$cost"},
                # 🔥 NEW: Sum total sales from item price
                "total_sales": { 
                    "$sum": { 
                        "$ifNull": ["$totalPrice", { "$multiply": ["$unitPrice", "$quantity"] }, 0] 
                    } 
                }
            }
        },
        {"$sort": {"quantity": -1}},
    ]

    if limit:
        pipeline.append({"$limit": limit})

    cursor = db.sales_items.aggregate(pipeline)

    # 🔍 Fetch products for latest TR names
    all_products = await db.products.find({}).to_list(None)
    prod_meta_map = {p["id"]: p for p in all_products}

    top_products = [
        {
            "product_id": (
                str(r["_id"]["productId"])
                if r["_id"].get("productId") else None
            ),
            "product_name": prod_meta_map.get(r["_id"].get("productId"), {}).get("tr_name") or r["_id"]["productName"],
            "quantity": int(r.get("quantity", 0)),
            "total_profit": round(r.get("total_profit", 0), 2),
            "total_cost": round(r.get("total_cost", 0), 2),
            # 🔥 FALLBACK: Sayısal veri yoksa Kâr + Maliyet = Ciro yaklaşımı
            "total_sales": round(
                r.get("total_sales", 0) or (r.get("total_profit", 0) + r.get("total_cost", 0)), 2
            ),
        }
        async for r in cursor
    ]
    
    if top_products:
        print(f"🚀 TOP PRODUCTS SAMPLE: {top_products[0]}")
    
    return top_products

