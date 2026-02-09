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

    # ================== 1️⃣ COMPETITION MODE DETERMINATION ==================
    # 🔥 COMPLETED Yarışmaları bul (Bunlar limitleri etkilememeli)
    completed_cursor = db.competitions.find({"status": "completed"})
    completed_ids = []
    async for c in completed_cursor:
        completed_ids.append(c["_id"])

    # 🔥 AKTİF YARIŞMA (Sadece 'active' ise)
    competition = await db.competitions.find_one({
        "status": "active",
        # "starts_at": {"$lte": now}, # 🔥 RELAXED: Active ise tarih bekleme
    })

    is_competition_report = False
    competition_id = None

    if competition:
        # 1. Zaten katılımcı mı?
        accepted = await db.competition_participants.find_one({
            "competition_id": competition["_id"],
            "user_id": current_user["_id"],
            "$or": [
                {"finished_at": None},
                {"finished_at": {"$gt": now}}
            ]
        })

        # 2. Kayıtlı mı? (Henüz kabul edilmemiş ama kayıtlı)
        registered = False
        if not accepted:
            registered = await db.competition_registrations.find_one({
                "competition_id": competition["_id"],
                "user_id": current_user["_id"],
            })

        if accepted or registered:
            is_competition_report = True
            competition_id = competition["_id"]
            print(f"🏆 COMPETITION REPORT TAGGED (User: {current_user['_id']}, Comp: {competition['year']}-{competition['month']})")

    # ================== 2️⃣ VISIBILITY & LIMIT LOGIC ==================
    # 🏎️ Modumuza göre kimi "gördüğümüzü" ve kimi "limit" saydığımızı belirliyoruz
    if is_competition_report:
        # Yarışmadaysak: Sadece bu yarışmanın raporlarını sayıyoruz
        visibility_query = {
            "is_competition_report": True,
            "competition_id": competition_id
        }
    else:
        # Yarışmada değilsek: Sadece bu yarışmadan SONRAKİ normal raporları sayıyoruz
        visibility_query = {
            "is_competition_report": {"$ne": True}
        }
        
        # 1. Küresel bitiş (Herkes için geçerli)
        last_ended_comp = await db.competitions.find_one(
            {"status": "completed"},
            sort=[("ended_at", -1), ("ends_at", -1)]
        )
        global_finish = last_ended_comp.get("ended_at") or last_ended_comp.get("ends_at") if last_ended_comp else month_start
        
        # 2. Bireysel bitiş (Sadece bu kullanıcı için geçerli)
        # Yarışma 'active' olsa bile kullanıcı bitmiş olabilir.
        user_finish_doc = await db.competition_participants.find_one(
            {"user_id": current_user["_id"], "finished_at": {"$lte": now}},
            sort=[("finished_at", -1)]
        )
        user_finish = user_finish_doc["finished_at"] if user_finish_doc else datetime.min
        
        # En güncelini seçiyoruz
        effective_finish = max(global_finish, user_finish)
        visibility_query["createdAt"] = {"$gte": effective_finish}
        print(f"🕒 Normal visibility threshold for {current_user['email']}: {effective_finish}")

    # HAFTALIK KONTROL (Mevcut modumuzda raporumuz var mı?)
    weekly_reports = await db.sales_reports.find({
        "user_id": current_user["_id"],
        "createdAt": {"$gte": week_start, "$lt": week_end},
        **visibility_query
    }).to_list(None)

    weekly_count = len(weekly_reports)

    if weekly_count >= 1:
        raise HTTPException(
            status_code=400,
            detail="Bu hafta zaten rapor yüklediniz"
        )

    # AYLIK KONTROL
    monthly_count = await db.sales_reports.count_documents({
        "user_id": current_user["_id"],
        "createdAt": {"$gte": month_start, "$lt": next_month},
        **visibility_query
    })

    if monthly_count >= 4:
        raise HTTPException(
            status_code=400,
            detail="Bu ay en fazla 4 rapor yükleyebilirsiniz"
        )

    # ================== 3️⃣ SAVING ==================
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
        "weekly_used": weekly_count + 1,
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

    # ====== COMPETITION MODE CHECK ======
    active_comp = await db.competitions.find_one({
        "status": "active",
        "starts_at": {"$lte": now},
        "ends_at": {"$gte": now},
    })
    
    is_in_active_competition = False
    active_comp_id = None
    if active_comp:
        participant = await db.competition_participants.find_one({
            "competition_id": active_comp["_id"],
            "user_id": current_user["_id"],
            "$or": [
                {"finished_at": None},
                {"finished_at": {"$gt": now}}
            ]
        })
        if participant:
            is_in_active_competition = True
            active_comp_id = active_comp["_id"]

    # ====== BUILD QUERY ======
    if is_in_active_competition:
        # 🏎️ YARIŞMA MODU: Sadece bu yarışmaya ait raporları göster
        visibility_query = {
            "is_competition_report": True,
            "competition_id": active_comp_id
        }
    else:
        # 📄 NORMAL MOD: Sadece en son biten yarışmadan sonraki normal raporları göster
        visibility_query = {
            "is_competition_report": {"$ne": True}
        }
        
        # 1. Küresel bitiş
        last_ended_comp = await db.competitions.find_one(
            {"status": "completed"},
            sort=[("ended_at", -1), ("ends_at", -1)]
        )
        global_finish = last_ended_comp.get("ended_at") or last_ended_comp.get("ends_at") if last_ended_comp else month_start
        
        # 2. Bireysel bitiş
        user_finish_doc = await db.competition_participants.find_one(
            {"user_id": current_user["_id"], "finished_at": {"$lte": now}},
            sort=[("finished_at", -1)]
        )
        user_finish = user_finish_doc["finished_at"] if user_finish_doc else datetime.min
        
        effective_finish = max(global_finish, user_finish)
        visibility_query["createdAt"] = {"$gte": effective_finish}

    # ====== COUNTS (For UI Progress Bars) ======
    weekly_count = await db.sales_reports.count_documents({
        "user_id": current_user["_id"],
        "createdAt": {"$gte": week_start, "$lt": week_end},
        **visibility_query
    })

    monthly_count = await db.sales_reports.count_documents({
        "user_id": current_user["_id"],
        "createdAt": {"$gte": month_start, "$lt": next_month},
        **visibility_query
    })

    # ====== PAGINATION & LISTING ======
    skip = (page - 1) * limit
    query = {
        "user_id": current_user["_id"],
        **visibility_query
    }

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
    user_ids: str,
    month: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    columns: Optional[str] = Query(None), # Comma separated keys
    pharmacy: Optional[str] = Query(None), # Filter by pharmacy name
    competition_id: Optional[str] = Query(None), # 🔥 Filter by competition
    current_user=Depends(admin_required),
):
    # Parse IDs
    ids_list = [id.strip() for id in user_ids.split(",") if id.strip()]
    if not ids_list:
        raise HTTPException(400, "No user IDs provided")
        
    for uid in ids_list:
        if not ObjectId.is_valid(uid):
             raise HTTPException(400, f"Invalid ID: {uid}")
             
    object_ids = [ObjectId(uid) for uid in ids_list]

    # Fetch User Name/Pharmacy for Filename (from first user)
    user_doc = await db.users.find_one({"_id": object_ids[0]})
    display_name = "Toplu_Rapor"
    if user_doc:
        # If single user, strict name. If multiple, maybe pharmacy name?
        # Let's rely on the first user's pharmacy name or name
        profile_pharmacy = user_doc.get("pharmacy_name") # From aggregation it might be different, but here we query raw user
        # Raw users collection usually doesn't have pharmacy_name unless aggregated or saved there? 
        # Actually user_doc is from db.users. 
        # Let's use name.
        display_name = user_doc.get("full_name") or user_doc.get("email") or "Kullanici"
        
        # If multiple users, try to find a common pharmacy name or just use "Eczane_Grubu"
        if len(object_ids) > 1:
            # Try to fetch profile for pharmacy name
            pipeline = [
                {"$match": {"_id": object_ids[0]}},
                {"$lookup": {"from": "user_profiles", "localField": "_id", "foreignField": "user_id", "as": "profile"}},
                {"$unwind": {"path": "$profile", "preserveNullAndEmptyArrays": True}}
            ]
            agg = await db.users.aggregate(pipeline).to_list(1)
            if agg and agg[0].get("profile"):
                display_name = agg[0]["profile"].get("pharmacy_name") or display_name

    # Fetch all user names for mapping
    user_cursor = db.users.find({"_id": {"$in": object_ids}})
    user_map = {}
    async for u in user_cursor:
        user_map[u["_id"]] = u.get("full_name") or u.get("email") or "Kullanici"

    # Sanitize filename (ASCII only)
    import unicodedata
    normalized = unicodedata.normalize('NFKD', display_name).encode('ascii', 'ignore').decode('ascii')
    safe_name = "".join([c if c.isalnum() else "_" for c in normalized])
    
    query = {"user_id": {"$in": object_ids}}
    
    if pharmacy:
        # Filter reports that start with the pharmacy name (case insensitive)
        # Because reports are named like "PharmacyName - Date"
        import re
        query["name"] = {"$regex": f"^{re.escape(pharmacy)}", "$options": "i"}

    if month and year:
        start = datetime(year, month, 1)
        end = (start + timedelta(days=32)).replace(day=1)
        query["createdAt"] = {"$gte": start, "$lt": end}

    if competition_id:
        if ObjectId.is_valid(competition_id):
            query["competition_id"] = ObjectId(competition_id)
            # Eğer competition_id varsa tarih filtresine gerek yok/yarışmanın kendi tarihleri geçerli
            if "createdAt" in query:
                del query["createdAt"]

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
    # COLUMN MAPPING
    # Key -> (Header Name, Data Extractor Function)
    # COLUMN MAPPING
    # Key -> (Header Name, Data Extractor Function)
    # COLUMN MAPPING
    # Key -> (Header Name, Data Extractor Function)
    column_map = {
        "cat": ("KATEGORİ", lambda r, i, p: p.get("category") or "-"),
        "gtin": ("GTIN", lambda r, i, p: p.get("gtin") or i.get("barcode") or i.get("productId") or "-"),
        "product_name": ("PRODUCT", lambda r, i, p: i.get("productName", "Bilinmeyen")),
        "ml": ("ML", lambda r, i, p: p.get("volume") or "-"),
        "psf_2026": ("2026 PSF", lambda r, i, p: p.get("psf_price") or 0),
        "esf": ("ESF", lambda r, i, p: p.get("esf_price") or 0),
        "wsf": ("WSF", lambda r, i, p: p.get("wsf_price") or 0),
        "price_eur": ("PRICE", lambda r, i, p: p.get("price_eur") or 0),
        "price_51": ("51", lambda r, i, p: p.get("price_51") or 0),
        "cost_tax": ("Maliyet", lambda r, i, p: p.get("cost") or i.get("cost") or 0),
        "profit": ("Kär", lambda r, i, p: i.get("profit") or i.get("ecz_kar") or 0),
        "markup": ("Markup", lambda r, i, p: p.get("markup") or 0),
        "margin": ("Kärlılık", lambda r, i, p: p.get("margin") or 0),
        "date": ("Tarih", lambda r, i, p: i.get("date") or r.get("createdAt").strftime("%d.%m.%Y")),
        "user_name": ("Kullanıcı", lambda r, i, p: user_map.get(r.get("user_id"), "-")),
        "quantity": ("Adet", lambda r, i, p: i.get("quantity", 0)),
        "unit_price": ("Birim Fiyat", lambda r, i, p: i.get("unitPrice") or i.get("birim_fiyat") or 0),
        "total_price": ("Net Satış", lambda r, i, p: i.get("totalPrice") or i.get("tutar") or 0),
        "barcode": ("Barkod", lambda r, i, p: i.get("barcode") or i.get("productId") or "-"),
        "stock": ("Stok", lambda r, i, p: i.get("stock", 0)),
        "report_name": ("Rapor Adı", lambda r, i, p: r.get("name", "-")),
    }

    # Determine columns to export
    if columns:
        selected_keys = [k.strip() for k in columns.split(",") if k.strip() in column_map]
    else:
        # Default as per the photo
        selected_keys = [
            "cat", "gtin", "product_name", "ml", "psf_2026", "esf", "wsf", 
            "price_eur", "price_51", "cost_tax", "profit", "markup", "margin"
        ]
        
    # Write Headers
    ws.append([column_map[k][0] for k in selected_keys])
    
    # 🔍 Fetch all products once for lookup
    all_products = await db.products.find({}).to_list(None)
    prod_meta_map = {p["id"]: p for p in all_products}

    for r in reports:
        items_cursor = db.sales_items.find({"report_id": r["_id"]})
        
        async for item in items_cursor:
            # Try to find metadata by barcode (productId)
            barcode = item.get("productId")
            prod_meta = prod_meta_map.get(barcode, {})
            
            row = [column_map[k][1](r, item, prod_meta) for k in selected_keys]
            ws.append(row)
        
    # SAVE TO BUFFER
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    filename = f"Raporlar_{safe_name}.xlsx"
    
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
    "stock": i.get("stock"),

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

    # 🎯 ÖNCELİK: Yıl ve Ay verilmişse direkt o yarışmayı bul (Filter ne olursa olsun)
    if year and month:
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
        # 🔥 Aktif ay: Önce "active" olanı bul (Erken başlamış olabilir)
        competition = await db.competitions.find_one({
            "status": "active",
        })
        
        # Eğer active yoksa, tarihi gelmiş olanı bul (fallback)
        if not competition:
            competition = await db.competitions.find_one({
                "starts_at": {"$lte": now},
                "ends_at": {"$gte": now},
            })

    # 🛡️ GÜVENLİK BARİYERİ
    if not competition:
        if year and month: # Geçmiş ay istenmiş ama yoksa hata verme, boş dön
             return {"my_user_id": str(current_user["_id"]), "items": []}
        raise HTTPException(403, "competition_missed")

    # 🔥 Aktif bir yarışma ise katılım kontrolü yap
    if competition.get("status") == "active":
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
    
    # 🔥 ARTIK HER AY İÇİN (Geçmiş/Şu an) Sadece Katılımcıları Getir
    # Eskiden "geçmiş ay -> herkes" demiştik ama bu hatalı (tüm userları getiriyor).
    # Artık geçmişte de kim katıldıysa sadece o gözüksün.
    
    participants = []
    p_names = []
    async for p in db.competition_participants.find({"competition_id": competition["_id"]}):
        participants.append(p["user_id"])
        u_info = await db.users.find_one({"_id": p["user_id"]})
        p_names.append(u_info.get("full_name") or u_info.get("email") if u_info else "Unknown")
    
    print(f"👥 PARTICIPANTS ({len(participants)}): {p_names}")

    if not participants:
        print("⚠️ NO PARTICIPANTS FOUND FOR THIS COMPETITION")
        return {
            "my_user_id": str(current_user["_id"]),
            "items": [],
        }

    user_match = {"user_id": {"$in": participants}}

    # ================= 3️⃣ SCOREBOARD PIPELINE =================

    print(f"🕵️ CHECKING ID: {competition['_id']} (Type: {type(competition['_id'])})")
    
    # Debug: DB'de bu ID'ye sahip kaç rapor var?
    debug_count = await db.sales_reports.count_documents({"competition_id": competition["_id"]})
    print(f"🧐 DB REPORT COUNT FOR THIS ID: {debug_count}")

    pipeline = [
        {
            "$match": {
                **user_match,
                
                # 🔥 STRICT ID & DATE FILTER: 
                # 1. ID eşleşmeli.
                # 2. Tarih aralığında olmalı (Erken başlayanları/eskiyi temizle).
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


    print("🏁 COMPETITION DATES:", competition["starts_at"], "->", competition["ends_at"])
    print("📋 PIPELINE MATCH:", pipeline[0]["$match"])

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
    if results:
        print("🥇 FIRST RESULT:", results[0])

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

    # ================= 1️⃣ COMPETITION BUL =================
    competition = await db.competitions.find_one({
        "year": year,
        "month": month,
    })

    if not competition:
        return {
            "my_user_id": str(current_user["_id"]),
            "competition": {"year": year, "month": month},
            "items": [],
        }

    # ================= 2️⃣ PARTICIPANTS BUL =================
    participants = []
    async for p in db.competition_participants.find({"competition_id": competition["_id"]}):
        participants.append(p["user_id"])

    if not participants:
        return {
            "my_user_id": str(current_user["_id"]),
            "competition": {"id": str(competition["_id"]), "year": year, "month": month},
            "items": [],
        }

    # ================= 3️⃣ STRICT PIPELINE =================
    pipeline = [
        {
            "$match": {
                "user_id": {"$in": participants},
                "competition_id": competition["_id"],
                # 🔥 STRICT DATE: Ay başı/sonu kuralına uymayanları (erken yüklenenler vb) ele
                "createdAt": {
                    "$gte": competition["starts_at"],
                    "$lte": competition["ends_at"],
                }
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
        {"$sort": {"total_items": -1}},
    ]

    print(f"🕵️ HISTORY DEBUG | {year}/{month} | CompID: {competition['_id']}")
    cursor = db.sales_reports.aggregate(pipeline)

    results = []
    async for r in cursor:
        user = await db.users.find_one({"_id": r["_id"]})
        results.append({
            "user_id": str(r["_id"]),
            "name": (user.get("full_name") or user.get("email")) if user else "Kullanıcı",
            "total_sales": float(r.get("total_sales", 0)),
            "total_profit": float(r.get("total_profit", 0)),
            "total_items": int(r.get("total_items", 0)),
        })

    return {
        "my_user_id": str(current_user["_id"]),
        "competition": {
            "id": str(competition["_id"]),
            "year": competition["year"],
            "month": competition["month"],
        },
        "items": results,
    }
