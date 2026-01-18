from typing import Optional
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime
from app.admin.dependencies import admin_required
from app.competitions.utils import end_of_month_utc
from app.core.database import db
from app.core.utils import serialize_mongo


from app.admin.service import (
    get_overview,
    get_top_users,
    get_top_products
)
from app.admin.schemas import AdminOverviewResponse

router = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)


@router.get("/overview", response_model=AdminOverviewResponse)
async def admin_overview(
    start: datetime = Query(..., description="UTC datetime (ISO 8601)"),
    end: datetime = Query(..., description="UTC datetime (ISO 8601)"),
    _=Depends(admin_required),
):
    return {
        "overview": await get_overview(start, end),
        "top_users": await get_top_users(start, end),
        "top_products": await get_top_products(start, end),
    }


@router.get("/analytics/daily", dependencies=[Depends(admin_required)])
async def daily_analytics(
    start: datetime = Query(..., description="UTC datetime (ISO 8601)"),
    end: datetime = Query(..., description="UTC datetime (ISO 8601)"),
):
    pipeline = [
        {
            "$match": {
                "createdAt": {
                    "$gte": start,
                    "$lte": end
                }
            }
        },
        {
            "$group": {
                "_id": {
                    "$dateToString": {
                        "format": "%Y-%m-%d",
                        "date": "$createdAt"
                    }
                },
                "total_profit": {
                    "$sum": "$summary.total_profit"
                },
                "total_cost": {
                    "$sum": "$summary.total_cost"
                }
            }
        },
        {
            "$addFields": {
                "total_revenue": {
                    "$add": ["$total_profit", "$total_cost"]
                }
            }
        },
        {"$sort": {"_id": 1}}
    ]

    cursor = db.sales_reports.aggregate(pipeline)

    labels, revenue, profit = [], [], []
    async for r in cursor:
        labels.append(r["_id"])
        revenue.append(float(r["total_revenue"]))
        profit.append(float(r["total_profit"]))

    return {
        "labels": labels,
        "revenue": revenue,
        "profit": profit
    }
@router.get("/users", dependencies=[Depends(admin_required)])
async def list_users():
    pipeline = [
        # 🔹 PROFILE JOIN
        {
            "$lookup": {
                "from": "user_profiles",
                "localField": "_id",
                "foreignField": "user_id",
                "as": "profile"
            }
        },
        {
            "$unwind": {
                "path": "$profile",
                "preserveNullAndEmptyArrays": True
            }
        },

        # 🔥 PROFILE FLATTEN
        {
  "$addFields": {
    "pharmacy_name": "$profile.pharmacy_name",
    "district": "$profile.district",
    "region": "$profile.region",

    # 🔥 REPRESENTATIVE NORMALIZE
    "representative": {
      "$cond": {
        "if": { "$eq": [{ "$type": "$profile.representative" }, "object"] },
        "then": "$profile.representative.name",
        "else": "$profile.representative"
      }
    }
  }
},


        # 🔹 SALES REPORTS JOIN
        {
            "$lookup": {
                "from": "sales_reports",
                "localField": "_id",
                "foreignField": "user_id",
                "as": "reports"
            }
        },

        # 🔹 AGGREGATES
        {
            "$addFields": {
                "total_reports": { "$size": "$reports" },
                "total_profit": { "$sum": "$reports.summary.total_profit" },
                "total_items": { "$sum": "$reports.summary.total_items" }
            }
        },

        # 🔹 PROJECT (⚠️ SADECE FIELD: 1)
        {
            "$project": {
                "email": 1,
                "full_name": 1,
                "avatar": 1,
                "role": 1,
                "created_at": 1,

                "pharmacy_name": 1,
                "district": 1,
                "region": 1,
                "representative": 1,

                "total_reports": 1,
                "total_profit": 1,
                "total_items": 1
            }
        },

        # 🔹 SORT
        {
            "$sort": { "created_at": -1 }
        }
    ]

    cursor = db.users.aggregate(pipeline)

    users = []
    async for u in cursor:
        users.append({
            "id": str(u["_id"]),
            "email": u.get("email"),
            "full_name": u.get("full_name"),
            "avatar": u.get("avatar"),
            "role": u.get("role", "user"),
            "created_at": u.get("created_at"),

            "pharmacy_name": u.get("pharmacy_name"),
            "district": u.get("district"),
            "region": u.get("region"),
            "representative": u.get("representative"),

            "total_reports": int(u.get("total_reports", 0)),
            "total_profit": float(u.get("total_profit", 0)),
            "total_items": int(u.get("total_items", 0)),
        })

    return users



@router.get("/reports", dependencies=[Depends(admin_required)])
async def admin_reports():
    cursor = (
        db.sales_reports
        .find({})
        .sort("createdAt", -1)
    )

    items = []
    async for r in cursor:
        items.append({
            "id": str(r["_id"]),
            "name": r.get("name"),
            "createdAt": r.get("createdAt"),
            "summary": r.get("summary", {
                "total_items": 0,
                "total_profit": 0,
                "total_cost": 0,
            }),
        })

    return items

@router.get("/reports/{report_id}", dependencies=[Depends(admin_required)])
async def admin_report_detail(report_id: str):
    if not ObjectId.is_valid(report_id):
        raise HTTPException(status_code=400, detail="Geçersiz rapor ID")

    report = await db.sales_reports.find_one(
        {"_id": ObjectId(report_id)}
    )

    if not report:
        raise HTTPException(status_code=404, detail="Rapor bulunamadı")

    cursor = db.sales_items.find(
        {"report_id": ObjectId(report_id)}
    )

    items = []
    async for i in cursor:
        items.append({
            "id": str(i["_id"]),
            "product_id": i.get("productId"),
            # 🔥 ASIL DÜZELTME BURADA
            "product_name": i.get("productName"),
            "quantity": int(i.get("quantity") or 0),
            
            # 🔥 FIX: Return prices to Admin Panel
            "unit_price": float(i.get("unitPrice") or i.get("unit_price") or 0),
            "total_price": float(i.get("totalPrice") or i.get("total_price") or 0),
            # camelCase for Frontend
            "unitPrice": float(i.get("unitPrice") or i.get("unit_price") or 0),
            "totalPrice": float(i.get("totalPrice") or i.get("total_price") or 0),
            
            "profit": float(i.get("profit") or 0),
            "cost": float(i.get("cost") or 0),
            "confidence": float(i.get("confidence") or 0),
        })

    return {
        "id": str(report["_id"]),
        "name": report.get("name", "Satış Raporu"),
        "createdAt": report.get("createdAt"),
        "summary": report.get("summary", {}),
        "items": items
    }

@router.get("/representatives", dependencies=[Depends(admin_required)])
async def representatives_performance(
    region: Optional[str] = Query(default=None),
):
    pipeline = []

    # 🔥 BÖLGE FİLTRESİ (OPSİYONEL)
    if region:
        pipeline.append({
            "$match": { "region": region }
        })

    pipeline += [
        # sadece eşleşmiş profiller
        {
            "$match": {
                "representative": { "$ne": None }
            }
        },

        # 🔹 normalize (object gelirse stringe çevir)
        {
            "$addFields": {
                "rep_name": {
                    "$cond": {
                        "if": { "$eq": [{ "$type": "$representative" }, "object"] },
                        "then": "$representative.name",
                        "else": "$representative"
                    }
                }
            }
        },

        # 🔹 group by representative + region
        {
            "$group": {
                "_id": {
                    "representative": "$rep_name",
                    "region": "$region"
                },
                "pharmacy_ids": { "$addToSet": "$pharmacy_id" },
                "user_ids": { "$addToSet": "$user_id" }
            }
        },

        # 🔹 counts
        {
            "$addFields": {
                "pharmacy_count": { "$size": "$pharmacy_ids" },
                "user_count": { "$size": "$user_ids" }
            }
        },

        # 🔹 join sales_reports
        {
            "$lookup": {
                "from": "sales_reports",
                "localField": "user_ids",
                "foreignField": "user_id",
                "as": "reports"
            }
        },

        # 🔹 aggregates
        {
            "$addFields": {
                "total_items": { "$sum": "$reports.summary.total_items" },
                "total_profit": { "$sum": "$reports.summary.total_profit" }
            }
        },

        # 🔹 sıralama
        { "$sort": { "total_profit": -1 } }
    ]

    cursor = db.user_profiles.aggregate(pipeline)

    results = []
    async for r in cursor:
        results.append({
            "representative": r["_id"]["representative"],
            "region": r["_id"]["region"],
            "pharmacy_count": int(r.get("pharmacy_count", 0)),
            "user_count": int(r.get("user_count", 0)),
            "total_items": int(r.get("total_items", 0)),
            "total_profit": float(r.get("total_profit", 0)),
        })

    return results

from fastapi import Depends, HTTPException
from urllib.parse import unquote

@router.get("/representatives/{name}", dependencies=[Depends(admin_required)])
async def representative_detail(name: str):
    rep_name = unquote(name)

    pipeline = [
        # ilgili mümessil
        { "$match": { "representative": { "$ne": None } } },

        # normalize (object → string)
        {
            "$addFields": {
                "rep_name": {
                    "$cond": {
                        "if": { "$eq": [{ "$type": "$representative" }, "object"] },
                        "then": "$representative.name",
                        "else": "$representative"
                    }
                }
            }
        },
        { "$match": { "rep_name": rep_name } },

        # kullanıcı & eczane setleri
        {
            "$group": {
                "_id": {
                    "representative": "$rep_name",
                    "region": "$region"
                },
                "user_ids": { "$addToSet": "$user_id" },
                "pharmacies": { "$addToSet": "$pharmacy_name" }
            }
        },

        # sales join
        {
            "$lookup": {
                "from": "sales_reports",
                "localField": "user_ids",
                "foreignField": "user_id",
                "as": "reports"
            }
        },

        # totals
        {
            "$addFields": {
                "total_items": { "$sum": "$reports.summary.total_items" },
                "total_profit": { "$sum": "$reports.summary.total_profit" }
            }
        }
    ]

    cursor = db.user_profiles.aggregate(pipeline)
    doc = await cursor.to_list(length=1)

    if not doc:
        raise HTTPException(404, "Mümessil bulunamadı")

    r = doc[0]

    # kullanıcı listesi (isim + email)
    users = []
    async for u in db.users.find({ "_id": { "$in": r["user_ids"] } }):
        users.append({
            "id": str(u["_id"]),
            "name": u.get("full_name") or u.get("email"),
            "email": u.get("email")
        })

    return {
        "representative": r["_id"]["representative"],
        "region": r["_id"]["region"],
        "pharmacies": sorted([p for p in r.get("pharmacies", []) if p]),
        "users": users,
        "total_items": int(r.get("total_items", 0)),
        "total_profit": float(r.get("total_profit", 0)),
    }

@router.get(
    "/representatives/{name}/users",
    dependencies=[Depends(admin_required)]
)
async def representative_users_with_competition(
    name: str,
    year: int = Query(...),
    month: int = Query(...)
):
    rep_name = unquote(name)

    # 🔥 AY + YIL'A GÖRE YARIŞMA BUL
    competition = await db.competitions.find_one({
        "year": year,
        "month": month,
        "status": { "$in": ["active", "completed"] }
    })

    if not competition:
        return {
            "competition": None,
            "in_competition": [],
            "not_in_competition": []
        }

    # 🔹 Bu mümessilin kullanıcıları
    profiles = db.user_profiles.find({
        "$or": [
            {"representative": rep_name},
            {"representative.name": rep_name},
        ]
    })

    user_ids = []
    async for p in profiles:
        user_ids.append(p["user_id"])

    # 🔹 Yarışmaya katılanlar
    participants = db.competition_participants.find({
        "competition_id": competition["_id"],
        "user_id": {"$in": user_ids}
    })

    participant_ids = set()
    async for p in participants:
        participant_ids.add(p["user_id"])

    # 🔹 Kullanıcıları ayır
    users_cursor = db.users.find({ "_id": { "$in": user_ids } })

    in_competition = []
    not_in_competition = []

    async for u in users_cursor:
        user_data = {
            "id": str(u["_id"]),
            "name": u.get("full_name") or u.get("email"),
            "email": u.get("email"),
        }

        if u["_id"] in participant_ids:
            in_competition.append(user_data)
        else:
            not_in_competition.append(user_data)

    return {
        "competition": {
            "year": competition["year"],
            "month": competition["month"],
        },
        "in_competition": in_competition,
        "not_in_competition": not_in_competition,
    }


@router.get("/users/{user_id}", dependencies=[Depends(admin_required)])
async def admin_user_detail(user_id: str):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(400, "Invalid user id")

    pipeline = [
        { "$match": { "_id": ObjectId(user_id) } },

        {
            "$lookup": {
                "from": "user_profiles",
                "localField": "_id",
                "foreignField": "user_id",
                "as": "profile"
            }
        },
        { "$unwind": { "path": "$profile", "preserveNullAndEmptyArrays": True }},

        {
            "$lookup": {
                "from": "sales_reports",
                "localField": "_id",
                "foreignField": "user_id",
                "as": "reports"
            }
        },

        {
            "$addFields": {
                "total_reports": { "$size": "$reports" },
                "total_items": { "$sum": "$reports.summary.total_items" },
                "total_profit": { "$sum": "$reports.summary.total_profit" }
            }
        }
    ]

    doc = await db.users.aggregate(pipeline).to_list(1)
    if not doc:
        raise HTTPException(404, "User not found")

    u = doc[0]

    return {
        "id": str(u["_id"]),
        "name": u.get("full_name"),
        "email": u.get("email"),
        "pharmacy": u.get("profile", {}).get("pharmacy_name"),
        "region": u.get("profile", {}).get("region"),
        "representative": u.get("profile", {}).get("representative"),
        "total_reports": u.get("total_reports", 0),
        "total_items": u.get("total_items", 0),
        "total_profit": u.get("total_profit", 0),
    }

@router.get("/competitions", dependencies=[Depends(admin_required)])
async def admin_list_competitions():
    cursor = db.competitions.find({}).sort("starts_at", -1)

    items = []
    async for c in cursor:
        items.append({
            "id": str(c["_id"]),
            "year": c["year"],
            "month": c["month"],
            "status": c.get("status", "upcoming"),
            "starts_at": c["starts_at"],
            "ends_at": c["ends_at"],
        })

    return items

@router.post("/competitions", dependencies=[Depends(admin_required)])
async def admin_create_competition(year: int, month: int):
    exists = await db.competitions.find_one({
        "year": year,
        "month": month,
        "status": { "$ne": "cancelled" }
    })

    if exists:
        raise HTTPException(400, "Competition already exists")

    starts_at = datetime(year, month, 1)
    ends_at = end_of_month_utc(year, month)

    doc = {
        "year": year,
        "month": month,
        "starts_at": starts_at,
        "ends_at": ends_at,
        "status": "upcoming",
        "created_at": datetime.utcnow(),
    }

    res = await db.competitions.insert_one(doc)

    return {
        "id": str(res.inserted_id),
        "status": "upcoming",
    }


from app.competitions.cron import activate_competition_by_admin

@router.post("/competitions/{competition_id}/start", dependencies=[Depends(admin_required)])
async def admin_start_competition(competition_id: str):
    if not ObjectId.is_valid(competition_id):
        raise HTTPException(400, "Invalid competition id")

    comp = await db.competitions.find_one({ "_id": ObjectId(competition_id) })
    if not comp:
        raise HTTPException(404, "Competition not found")

    if comp.get("status") != "upcoming":
        raise HTTPException(400, "Only upcoming competitions can be started")

    # 🔒 AY BAZLI TEK YARIŞMA KURALI
    existing = await db.competitions.find_one({
        "_id": { "$ne": comp["_id"] },
        "year": comp["year"],
        "month": comp["month"],
        "status": "active",
    })

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Bu ay için zaten aktif bir yarışma var"
        )

    # 🔥 TEK SOURCE OF TRUTH
    await activate_competition_by_admin(comp["_id"])

    return { "status": "active" }




@router.post("/competitions/{competition_id}/finish", dependencies=[Depends(admin_required)])
async def admin_finish_competition(competition_id: str):
    comp = await db.competitions.find_one({ "_id": ObjectId(competition_id) })

    if not comp:
        raise HTTPException(404, "Competition not found")

    if comp.get("status") != "active":
        raise HTTPException(400, "Only active competitions can be finished")

    await db.competitions.update_one(
        { "_id": comp["_id"] },
        {
            "$set": {
                "status": "completed",
                "ended_at": datetime.utcnow(),
            }
        }
    )

    return { "status": "completed" }


@router.post("/competitions/{competition_id}/cancel", dependencies=[Depends(admin_required)])
async def admin_cancel_competition(competition_id: str):
    if not ObjectId.is_valid(competition_id):
        raise HTTPException(400, "Invalid competition id")

    comp = await db.competitions.find_one({ "_id": ObjectId(competition_id) })
    if not comp:
        raise HTTPException(404, "Competition not found")

    # ❌ SADECE COMPLETED KORUNUR
    if comp.get("status") == "completed":
        raise HTTPException(
            status_code=400,
            detail="Completed competition cannot be cancelled"
        )

    # 🔥 HARD DELETE (upcoming + active)
    await db.competitions.delete_one({ "_id": comp["_id"] })

    # 🔥 BAĞLI KAYITLARI TEMİZLE
    await db.competition_registrations.delete_many({
        "competition_id": comp["_id"]
    })

    await db.competition_participants.delete_many({
        "competition_id": comp["_id"]
    })

    return { "status": "deleted" }

@router.get(
    "/competitions/{competition_id}/participants",
    dependencies=[Depends(admin_required)]
)
async def admin_competition_participants(competition_id: str):
    if not ObjectId.is_valid(competition_id):
        raise HTTPException(400, "Invalid competition id")

    competition = await db.competitions.find_one({
        "_id": ObjectId(competition_id)
    })

    if not competition:
        raise HTTPException(404, "Competition not found")

    # 🔹 Yarışmaya katılan kullanıcılar
    participants_cursor = db.competition_participants.find({
        "competition_id": competition["_id"]
    })

    user_ids = []
    async for p in participants_cursor:
        user_ids.append(p["user_id"])

    if not user_ids:
        return {
            "competition": {
                "year": competition["year"],
                "month": competition["month"],
            },
            "participants": []
        }

    # 🔹 Kullanıcı + rapor sayısı
    pipeline = [
        { "$match": { "_id": { "$in": user_ids } } },

        {
            "$lookup": {
                "from": "sales_reports",
                "localField": "_id",
                "foreignField": "user_id",
                "as": "reports"
            }
        },

        {
            "$addFields": {
                "report_count": { "$size": "$reports" }
            }
        },

        {
            "$project": {
                "_id": 0,
                "id": { "$toString": "$_id" },
                "name": { "$ifNull": ["$full_name", "$email"] },
                "email": 1,
                "report_count": 1
            }
        },

        { "$sort": { "report_count": -1 } }
    ]

    cursor = db.users.aggregate(pipeline)

    participants = []
    async for u in cursor:
        participants.append(u)

    return {
        "competition": {
            "year": competition["year"],
            "month": competition["month"],
        },
        "participants": participants
    }







