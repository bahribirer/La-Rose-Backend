from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from app.competitions.service import get_user_competition_status
from app.sales.schemas import SaleReportCreateRequest
from app.sales.service import save_scan_report
from app.users.router import get_current_db_user
from app.admin.dependencies import admin_required
from app.core.database import db
from bson import ObjectId
from typing import Optional

router = APIRouter(
    prefix="/sales",
    tags=["Sales"]
)

# ================= SAVE SCAN =================

@router.post("/scan")
async def save_sales_from_scan(
    payload: SaleReportCreateRequest,
    current_user=Depends(get_current_db_user),
):
    print("🧪 RAW PAYLOAD:", payload.model_dump())
    if not payload.items:
        raise HTTPException(400, "Boş rapor")

    now = datetime.utcnow()

    # ================== AY ARALIĞI ==================
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    next_month = (month_start + timedelta(days=32)).replace(day=1)

    # ================== HAFTA ARALIĞI ==================
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=7)

    # ================== HAFTALIK KONTROL (MAX 1) ==================
    weekly_count = await db.sales_reports.count_documents({
        "user_id": current_user["_id"],
        "createdAt": {"$gte": week_start, "$lt": week_end},
    })

    if weekly_count >= 1:
        raise HTTPException(
            status_code=400,
            detail="Bu hafta zaten rapor yüklediniz"
        )

    # ================== AYLIK KONTROL (MAX 4) ==================
    monthly_count = await db.sales_reports.count_documents({
        "user_id": current_user["_id"],
        "createdAt": {"$gte": month_start, "$lt": next_month},
    })

    if monthly_count >= 4:
        raise HTTPException(
            status_code=400,
            detail="Bu ay en fazla 4 rapor yükleyebilirsiniz"
        )

    # ================== AKTİF YARIŞMA ==================
    competition = await db.competitions.find_one({
        "starts_at": {"$lte": now},
        "ends_at": {"$gte": now},
    })

    is_competition_report = False
    competition_id = None

    if competition:
        accepted = await db.competition_participants.find_one({
            "competition_id": competition["_id"],
            "user_id": current_user["_id"],
        })

        if accepted:
            is_competition_report = True
            competition_id = competition["_id"]

    # ================== KAYDET ==================
    result = await save_scan_report(
        user=current_user,
        items=payload.items,
        competition_id=competition_id,
        is_competition_report=is_competition_report,
    )

    # 🚨 ADMIN NOTIFICATION CHECK: 4th Report
    if monthly_count + 1 == 4:
        from app.notifications.service import create_admin_notification
        user_name = current_user.get("full_name") or current_user.get("email") or "Kullanıcı"
        
        await create_admin_notification(
            title="🎯 Aylık Hedef Tamamlandı!",
            body=f"{user_name} bu ayki 4. raporunu yükleyerek kotasını doldurdu.",
            type="goal_reached",
            data={"user_id": str(current_user["_id"])}
        )

    return {
        "message": "Scan raporu kaydedildi",
        "report_id": result["report_id"],
        "is_competition_report": is_competition_report,
        "weekly_used": 1,
        "weekly_limit": 1,
        "monthly_used": monthly_count + 1,
        "monthly_limit": 4,
    }




# ================= LIST REPORTS (PAGINATION) =================

@router.get("/reports")
async def list_sales_reports(
    page: int = 1,
    limit: int = 10,
    current_user=Depends(get_current_db_user),
):
    now = datetime.utcnow()

    # ====== DATE RANGES ======
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    next_month = (month_start + timedelta(days=32)).replace(day=1)

    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=7)

    # ====== COUNTS ======
    weekly_count = await db.sales_reports.count_documents({
        "user_id": current_user["_id"],
        "createdAt": {"$gte": week_start, "$lt": week_end},
    })

    monthly_count = await db.sales_reports.count_documents({
        "user_id": current_user["_id"],
        "createdAt": {"$gte": month_start, "$lt": next_month},
    })

    # ====== PAGINATION ======
    skip = (page - 1) * limit
    query = {"user_id": current_user["_id"]}

    total = await db.sales_reports.count_documents(query)

    cursor = (
        db.sales_reports
        .find(query)
        .sort("createdAt", -1)
        .skip(skip)
        .limit(limit)
    )

    items = []
    async for r in cursor:
        items.append({
            "id": str(r["_id"]),
            "name": r.get("name"),
            "createdAt": r["createdAt"],
            "type": r.get("type"),
            "source": r.get("source"),
            "summary": r.get("summary", {}),
            "is_competition_report": bool(r.get("is_competition_report", False)),
        })

    return {
        "items": items,
        "page": page,
        "limit": limit,
        "total": total,

        # 🔥 UI İÇİN ALTIN BİLGİ
        "weekly": {
            "used": weekly_count,
            "limit": 1,
        },
        "monthly": {
            "used": monthly_count,
            "limit": 4,
        },
    }




# ================= EXPORT =================

@router.get("/reports/export")
async def export_user_reports(
    user_id: str,
    month: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    columns: Optional[str] = Query(None), # Comma separated keys
    current_user=Depends(admin_required),
):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(400, "Invalid ID")

    # Fetch User Name for Filename
    user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
    user_name = "Kullanici"
    if user_doc:
        user_name = user_doc.get("full_name") or user_doc.get("email") or "Kullanici"
        user_name = "".join([c if c.isalnum() else "_" for c in user_name])

    query = {"user_id": ObjectId(user_id)}
    
    if month and year:
        start = datetime(year, month, 1)
        end = (start + timedelta(days=32)).replace(day=1)
        query["createdAt"] = {"$gte": start, "$lt": end}

    reports = []
    async for r in db.sales_reports.find(query):
        reports.append(r)
        
    if not reports:
        raise HTTPException(404, "Rapor bulunamadı")
        
    # GENERATE EXCEL
    import openpyxl
    import io
    from fastapi.responses import StreamingResponse
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Satis Detaylari"
    
    # COLUMN MAPPING
    # Key -> (Header Name, Data Extractor Function)
    column_map = {
        "date": ("Tarih", lambda r, i: r.get("createdAt").strftime("%Y-%m-%d %H:%M")),
        "product_name": ("Ürün Adı", lambda r, i: i.get("productName", "Bilinmeyen")),
        "quantity": ("Adet", lambda r, i: i.get("quantity", 0)),
        "unit_price": ("Birim Fiyat", lambda r, i: i.get("unitPrice", 0)),
        "total_price": ("Toplam Tutar", lambda r, i: i.get("totalPrice", 0)),
        "profit": ("Kâr", lambda r, i: i.get("profit", 0)),
        "cost": ("Masraf", lambda r, i: i.get("cost", 0)),
        "report_name": ("Rapor Adı", lambda r, i: r.get("name", "-")),
    }
    
    # Determine columns to export
    if columns:
        selected_keys = [k.strip() for k in columns.split(",") if k.strip() in column_map]
    else:
        # Default
        selected_keys = ["date", "product_name", "quantity", "unit_price", "total_price"]
        
    # Write Headers
    ws.append([column_map[k][0] for k in selected_keys])
    
    for r in reports:
        items_cursor = db.sales_items.find({"report_id": r["_id"]})
        has_items = False
        
        async for item in items_cursor:
            has_items = True
            row = [column_map[k][1](r, item) for k in selected_keys]
            ws.append(row)
            
        if not has_items:
             pass
        
    # SAVE TO BUFFER
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    filename = f"Raporlar_{user_name}.xlsx"
    
    return StreamingResponse(
        output, 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# ================= DETAIL =================

@router.get("/reports/{report_id}")
async def get_sales_report_detail(
    report_id: str,
    current_user=Depends(get_current_db_user),
):
    report = await db.sales_reports.find_one({
        "_id": ObjectId(report_id),
        "user_id": current_user["_id"],
    })

    if not report:
        raise HTTPException(status_code=404, detail="Rapor bulunamadı")

    cursor = db.sales_items.find({"report_id": report["_id"]})

    items = []
    async for i in cursor:
        items.append({
    "id": str(i["_id"]),
    "productId": i.get("productId"),
    "productName": i.get("productName"),
    "quantity": i.get("quantity"),

    # 🔥 ADMIN FİYATLAR
    "unitPrice": i.get("unitPrice"),
    "totalPrice": i.get("totalPrice"),

    # mevcut alanlar
    "profit": i.get("profit"),
    "cost": i.get("cost"),
    "confidence": i.get("confidence"),
})


    return {
        "report": {
            "id": str(report["_id"]),
            "name": report.get("name"),   # 🔥 DETAIL’DE DE VAR
            "createdAt": report["createdAt"],
            "type": report.get("type"),
            "source": report.get("source"),
            "summary": report.get("summary"),
            "is_competition_report": bool(report.get("is_competition_report", False)),
        },
        "items": items,
    }

# ================= DELETE =================

@router.delete("/reports/{report_id}")
async def delete_sales_report(
    report_id: str,
    current_user=Depends(get_current_db_user),
):
    report = await db.sales_reports.find_one({
        "_id": ObjectId(report_id),
        "user_id": current_user["_id"],
    })

    if not report:
        raise HTTPException(status_code=404, detail="Rapor bulunamadı")

    await db.sales_items.delete_many({"report_id": report["_id"]})
    await db.sales_reports.delete_one({"_id": report["_id"]})

    return {"message": "Rapor ve bağlı satışlar silindi"}

@router.patch("/reports/{report_id}")
async def update_report_name(
    report_id: str,
    payload: dict,
    current_user=Depends(get_current_db_user),
):
    name = payload.get("name")
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="Rapor adı boş")

    res = await db.sales_reports.update_one(
        {
            "_id": ObjectId(report_id),
            "user_id": current_user["_id"],
        },
        {"$set": {"name": name.strip()}}
    )

    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Rapor bulunamadı")

    return {"message": "Rapor adı güncellendi"}

# ================= SCOREBOARD =================

# ================= SCOREBOARD =================

@router.get("/scoreboard")
async def get_scoreboard(
    filter: str = Query("month"),
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    current_user=Depends(get_current_db_user),
):
    now = datetime.utcnow()

    print("\n================ SCOREBOARD =================")
    print("👤 user_id:", current_user["_id"])
    print("📌 filter:", filter)
    print("📆 year:", year, "month:", month)

    # ================= 1️⃣ COMPETITION BUL =================

    if filter == "previousMonths":
        if not year or not month:
            raise HTTPException(400, "year and month required")

        competition = await db.competitions.find_one({
            "year": year,
            "month": month,
        })

    elif filter == "lastMonth":
        prev = now.replace(day=1) - timedelta(days=1)
        competition = await db.competitions.find_one({
            "year": prev.year,
            "month": prev.month,
        })

    else:
        competition = await db.competitions.find_one({
            "starts_at": {"$lte": now},
            "ends_at": {"$gte": now},
        })

        if not competition:
            raise HTTPException(403, "competition_missed")

        accepted = await db.competition_participants.find_one({
            "competition_id": competition["_id"],
            "user_id": current_user["_id"],
        })

        if not accepted:
            raise HTTPException(403, "competition_not_accepted")

    if not competition:
        return {
            "my_user_id": str(current_user["_id"]),
            "items": [],
        }

    print("🏁 COMPETITION:", competition["year"], competition["month"])

    # ================= 2️⃣ USER FILTER =================

    if filter in ["previousMonths", "lastMonth"]:
        # 🔥 geçmiş ay → HERKES
        user_match = {}
    else:
        # 🔥 aktif ay → sadece katılanlar
        participants = [
            p["user_id"]
            async for p in db.competition_participants.find({
                "competition_id": competition["_id"]
            })
        ]

        print("👥 PARTICIPANTS:", participants)

        if not participants:
            return {
                "my_user_id": str(current_user["_id"]),
                "items": [],
            }

        user_match = {"user_id": {"$in": participants}}

    # ================= 3️⃣ SCOREBOARD PIPELINE =================

    pipeline = [
    {
        "$match": {
            **user_match,

            # 🔥 SADECE YARIŞMA RAPORLARI
            "is_competition_report": True,
            "competition_id": competition["_id"],

            "createdAt": {
                "$gte": competition["starts_at"],
                "$lte": competition["ends_at"],
            },
        }
    },
    {
        "$group": {
            "_id": "$user_id",
            "total_profit": {"$sum": "$summary.total_profit"},
            "total_cost": {"$sum": "$summary.total_cost"},
            "total_items": {"$sum": "$summary.total_items"},
        }
    },
    {
        "$addFields": {
            "total_sales": {"$add": ["$total_profit", "$total_cost"]}
        }
    },
    {"$sort": {
    "total_items": -1,     # 🔥 ASIL SIRALAMA
    "total_profit": -1     # (opsiyonel) eşitlik bozucu
}},

    {"$limit": 50},
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
                or "Kullanıcı"
            ) if user else "Kullanıcı",
            "total_sales": float(r.get("total_sales", 0) or 0),
            "total_profit": float(r.get("total_profit", 0) or 0),
            "total_items": int(r.get("total_items", 0) or 0),
        })

    print("📊 RESULT COUNT:", len(results))

    return {
        "my_user_id": str(current_user["_id"]),
        "competition": {
            "year": competition["year"],
            "month": competition["month"],
        },
        "items": results,
    }

@router.get("/scoreboard/history")
async def get_scoreboard_history(
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    current_user=Depends(get_current_db_user),
):
    if not year or not month:
        raise HTTPException(400, "year & month required")

    start = datetime(year, month, 1)
    end = (
        datetime(year + 1, 1, 1)
        if month == 12
        else datetime(year, month + 1, 1)
    )

    pipeline = [
        {
            "$match": {
                "createdAt": {"$gte": start, "$lt": end}
            }
        },
        {
            "$group": {
                "_id": "$user_id",
                "total_profit": {"$sum": "$summary.total_profit"},
                "total_cost": {"$sum": "$summary.total_cost"},
                "total_items": {"$sum": "$summary.total_items"},
            }
        },
        {"$sort": {
    "total_items": -1,     # 🔥 ASIL SIRALAMA
    "total_profit": -1     # (opsiyonel) eşitlik bozucu
}},

    ]

    cursor = db.sales_reports.aggregate(pipeline)

    results = []
    async for r in cursor:
        user = await db.users.find_one({"_id": r["_id"]})
        results.append({
            "user_id": str(r["_id"]),
            "name": user.get("full_name") if user else "Kullanıcı",
            "total_profit": r["total_profit"],
            "total_items": r["total_items"],
        })


    return {
        "my_user_id": str(current_user["_id"]),
        "items": results,
    }


