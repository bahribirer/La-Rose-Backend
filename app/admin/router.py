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
                "total_cost": { "$sum": "$reports.summary.total_cost" },
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
                "total_cost": 1,
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
            "total_revenue": float(u.get("total_profit", 0) + u.get("total_cost", 0)),
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
        summary = r.get("summary", {
            "total_items": 0,
            "total_profit": 0,
            "total_cost": 0,
        })
        
        # 🔥 FIX: Calculate revenue on the fly if missing
        if "total_revenue" not in summary:
            summary["total_revenue"] = summary.get("total_sales") or (summary.get("total_profit", 0) + summary.get("total_cost", 0))

        items.append({
            "id": str(r["_id"]),
            "name": r.get("name"),
            "createdAt": r.get("createdAt"),
            "summary": summary,
            "is_competition_report": bool(r.get("is_competition_report", False)),
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
        p_id = i.get("productId")
        
        # 🔥 FIX: Product ID is the Barcode (e.g. 869...). 
        # No need to query products collection unless we need other fields.
        barcode = p_id if p_id else "-"

        items.append({
            "id": str(i["_id"]),
            "product_id": p_id,
            "product_name": i.get("productName"),
            "quantity": int(i.get("quantity") or 0),
            "unit_price": float(i.get("unitPrice") or i.get("unit_price") or 0),
            "total_price": float(i.get("totalPrice") or i.get("total_price") or 0),
            "unitPrice": float(i.get("unitPrice") or i.get("unit_price") or i.get("birim_fiyat") or 0),
            "totalPrice": float(i.get("totalPrice") or i.get("total_price") or i.get("tutar") or 0),
            "price": float(i.get("unitPrice") or i.get("unit_price") or i.get("birim_fiyat") or 0),
            "profit": float(i.get("profit") or i.get("ecz_kar") or 0),
            "cost": float(i.get("cost") or i.get("maliyet") or 0),
            "confidence": float(i.get("confidence") or i.get("match_confidence") or 0),
            "date": i.get("date"),
            "barcode": barcode,
            "stock": int(i.get("stock") or i.get("stok_miktari") or 0)
        })

    # 🔥 FIX: Admin Panel needs total_revenue (profit + cost)
    summary = report.get("summary", {})
    if "total_revenue" not in summary:
        summary["total_revenue"] = summary.get("total_sales") or (summary.get("total_profit", 0) + summary.get("total_cost", 0) + 0.0001)

    print(f"🚀 ADMIN DETAIL RESP: {summary} | ITEM[0]: {items[0] if items else 'EMPTY'}")

    return {
        "id": str(report["_id"]),
        "name": report.get("name", "Satış Raporu"),
        "createdAt": report.get("createdAt"),
        "summary": summary,
        "items": items
    }

# 🔥 DEBUG ENDPOINT: PROOF OF DATA
@router.get("/debug/report-item/{report_id}", dependencies=[Depends(admin_required)])
async def debug_report_item(report_id: str):
    item = await db.sales_items.find_one({"report_id": ObjectId(report_id)})
    if item:
        item["_id"] = str(item["_id"])
        item["report_id"] = str(item["report_id"])
        return item
    return {"error": "No items found for this report"}

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
                "total_profit": { "$sum": "$reports.summary.total_profit" },
                "total_cost": { "$sum": "$reports.summary.total_cost" }
            }
        },
        { 
            "$addFields": { 
                "total_revenue": { "$add": ["$total_profit", "$total_cost"] } 
            } 
        },

        # 🔹 sıralama
        { "$sort": { "total_revenue": -1 } }
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
            "total_revenue": float(r.get("total_revenue", 0)),
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
                "total_profit": { "$sum": "$reports.summary.total_profit" },
                "total_cost": { "$sum": "$reports.summary.total_cost" }
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
        "total_revenue": float(r.get("total_profit", 0) + r.get("total_cost", 0)),
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

    # 1️⃣ AGGREGATION (Lifetime Stats)
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
                "total_profit": { "$sum": "$reports.summary.total_profit" },
                "total_cost": { "$sum": "$reports.summary.total_cost" }
            }
        }
    ]

    doc = await db.users.aggregate(pipeline).to_list(1)
    if not doc:
        raise HTTPException(404, "User not found")

    u = doc[0]

    # 2️⃣ CONTEXT-AWARE COUNTS (Reset Logic)
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    current_month_count = await db.sales_reports.count_documents({
        "user_id": u["_id"],
        "createdAt": {"$gte": month_start},
        "is_competition_report": {"$ne": True}
    })

    # 3️⃣ COMPETITION INFO
    last_comp_info = None
    
    # En son katıldığı yarışmayı bul
    last_participation = await db.competition_participants.find_one(
        { "user_id": u["_id"] }, 
        sort=[("accepted_at", -1)]
    )

    if last_participation:
        comp = await db.competitions.find_one({"_id": last_participation["competition_id"]})
        if comp:
            # 🔥 GERÇEK STATUS KONTROLÜ (Tarih + Bireysel Bitiş)
            is_truly_active = (
                comp.get("status") == "active" and 
                comp["starts_at"] <= now <= comp["ends_at"] and
                (last_participation.get("finished_at") is None or last_participation["finished_at"] > now)
            )
            
            if not is_truly_active and last_participation.get("finished_at") and last_participation["finished_at"] <= now:
                # Kullanıcı bireysel olarak bitmişse, admin panelinde onu "Normal Mod"da (0/4 hedef) gösterelim.
                last_comp_info = None
            else:
                last_comp_info = {
                    "id": str(comp["_id"]),
                    "status": "active" if is_truly_active else comp.get("status"),
                    "year": comp["year"],
                    "month": comp["month"],
                    "is_finished_individually": last_participation.get("finished_at") is not None
                }

    return {
        "id": str(u["_id"]),
        "name": u.get("full_name"),
        "email": u.get("email"),
        "pharmacy": u.get("profile", {}).get("pharmacy_name"),
        "region": u.get("profile", {}).get("region"),
        "representative": u.get("profile", {}).get("representative"),
        
        # Lifetime Stats
        "total_reports": u.get("total_reports", 0),
        "total_items": u.get("total_items", 0),
        "total_profit": u.get("total_profit", 0),
        "total_revenue": u.get("total_profit", 0) + u.get("total_cost", 0),

        # Context Stats (for UI Reset & Download)
        "current_month_reports": current_month_count,
        "competition": last_comp_info
    }


@router.post("/users/{user_id}/notify", dependencies=[Depends(admin_required)])
async def send_user_notification(user_id: str, type: str = "report"):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(400, "Invalid user id")

    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(404, "User not found")
        
    # CONTENT MAP
    content_map = {
        "report": {
            "title": "Rapor Hatırlatması 📊",
            "body": "Bu haftaki stok raporunu yüklemeyi unutma! Hemen şimdi yükle.",
        },
        "competition": {
            "title": "Yarışma Başladı! 🏆",
            "body": "Yeni yarışma kayıtları açıldı. Hemen katıl ve kazanmaya başla!",
        },
        "stock": {
            "title": "Stok Hatırlatması 📦",
            "body": "Lütfen stok durumunuzu mümessilinize bildiriniz.",
        }
    }
    
    content = content_map.get(type, content_map["report"])

    # 📌 SAVE TO DB & SEND PUSH (via service.py)
    from app.notifications.service import create_notification
    await create_notification(
        user_id=user["_id"],
        title=content["title"],
        body=content["body"],
        type=type
    )

    return {
        "message": "Bildirim gönderildi", 
        "status": "sent"
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

    # 🛡️ ZAMAN KONTROLÜ
    now = datetime.utcnow()
    if comp["starts_at"] > now:
        raise HTTPException(400, "Henüz yarışma başlangıç tarihi gelmedi")

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

    now = datetime.utcnow()

    # 1️⃣ Yarışmayı Bitir
    await db.competitions.update_one(
        { "_id": comp["_id"] },
        {
            "$set": {
                "status": "completed",
                "ended_at": now,
            }
        }
    )

    # 2️⃣ Katılımcıların da bittiği tarihi işle
    await db.competition_participants.update_many(
        { "competition_id": comp["_id"] },
        {
            "$set": {
                "finished_at": now
            }
        }
    )

    # 3️⃣ Bildirim Gönder (Mobilin Yenilenmesi İçin)
    from app.notifications.service import create_notification
    
    participants_cursor = db.competition_participants.find({ "competition_id": comp["_id"] })
    
    # Send individually or bulk? For simplicity and to use existing service, loop.
    # Ideally use a bulk service if available, but for now loop is acceptable for typical participant counts.
    async for p in participants_cursor:
        await create_notification(
            user_id=p["user_id"],
            title="Yarışma Sona Erdi",
            body=f"{comp['month']}/{comp['year']} yarışması tamamlanmıştır.",
            type="competition_ended",
            data={
                "competition_id": str(comp["_id"]),
                "refresh": "true"
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
                "let": { "uid": "$_id" },
                "pipeline": [
                    { 
                        "$match": { 
                            "$expr": { 
                                "$and": [
                                    { "$eq": ["$user_id", "$$uid"] },
                                    { "$eq": ["$competition_id", ObjectId(competition_id)] }
                                ]
                            }
                        } 
                    }
                ],
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
            "status": competition.get("status"),
        },
        "participants": participants
    }







