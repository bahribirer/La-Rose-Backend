from datetime import datetime
from bson import ObjectId
from app.core.database import db
from app.competitions.utils import is_registration_period_tr, now_tr

# ================= CURRENT =================

async def get_current_competition():
    now = datetime.utcnow()

    return await db.competitions.find_one({
        "status": "active",                # 🔥 ZORUNLU
        "starts_at": {"$lte": now},
        "ends_at": {"$gte": now},
    })

# ================= NEXT =================

async def get_next_competition():
    now = datetime.utcnow()

    return await db.competitions.find_one({
        "status": "upcoming",              # 🔥 sadece upcoming
        "starts_at": {"$gt": now},
    }, sort=[("starts_at", 1)])

# ================= STATUS =================

async def get_user_competition_status(user_id: ObjectId):
    now_tr_time = now_tr()
    now_utc = datetime.utcnow()

    # 0️⃣ GELECEK YARIŞMA (UPCOMING) - Kayıt/Geri sayım için lazım
    next_comp = await db.competitions.find_one(
        {
            "status": { "$in": ["upcoming", "active"] }, # 🔥 'active' olsa da henüz başlamamış olabilir
            "starts_at": {"$gt": now_utc},
        },
        sort=[("starts_at", 1)]
    )

    # 1️⃣ AKTİF YARIŞMA SORGUSU (En yüksek öncelik)
    current = await db.competitions.find_one({
        "status": { "$in": ["active", "upcoming"] }, # 🔥 ZAMANI GELMİŞSE UPCOMING DE AKTİF SAYILIR
        "starts_at": {"$lte": now_utc},
        "ends_at": {"$gte": now_utc},
    })

    if current:
        # 🛡️ OTO-AKTİVASYON (Admin başlatmayı unutmuşsa veya 1 Ocak geldiyse)
        if current.get("status") == "upcoming":
            await db.competitions.update_one(
                {"_id": current["_id"]},
                {"$set": {"status": "active", "activated_at": now_utc}}
            )
            current["status"] = "active" # Hafızada güncelle
        accepted = await db.competition_participants.find_one({
            "user_id": user_id,
            "competition_id": current["_id"],
        })

        # Bireysel Bitiş Kontrolü
        is_finished_individually = False
        if accepted and accepted.get("finished_at") and accepted["finished_at"] <= now_utc:
            is_finished_individually = True

        # Eğer yarışmadaysak ve bitirmemişsek -> Skorboard göster
        if accepted and not is_finished_individually:
            return {
                "status": "accepted",
                "competition": current,
            }

        # Eğer yeni ayın yarışmasına admin onay verdiyse (upcoming -> active olduysa) 
        # ve kullanıcı geçen aydan kayıtlıysa otomatik kabul et.
        if not accepted:
            registered = await db.competition_registrations.find_one({
                "user_id": user_id,
                "competition_id": current["_id"],
            })
            if registered:
                await db.competition_participants.insert_one({
                    "user_id": user_id,
                    "competition_id": current["_id"],
                    "accepted_at": now_utc,
                    "auto": True,
                })
                await db.competition_registrations.delete_one({"_id": registered["_id"]})
                return {
                    "status": "accepted",
                    "competition": current,
                }

        # Eğer yarışma var ama ben katılmamışsam (missed) 
        # VE kayıt dönemi değilse -> 'missed' ekranı
        if not is_finished_individually:
             return {
                "status": "missed",
                "competition": current,
                "can_register_next": is_registration_period_tr() and next_comp is not None,
            }

    # 2️⃣ GELECEK YARIŞMA KAYIT DURUMU (Öncelik: Kayıtlı mı? -> Kayıt Açık mı?)
    if next_comp:
        # Kayıtlı mıyım?
        registered_next = await db.competition_registrations.find_one({
            "user_id": user_id,
            "competition_id": next_comp["_id"],
        })
        if registered_next:
            return {
                "status": "registered",
                "competition": next_comp,
            }

        # Kayıt açık mı?
        if is_registration_period_tr():
            return {
                "status": "registration_open",
                "competition": next_comp,
            }

    # 3️⃣ SON YARIŞMA DURUMU (Ended)
    last = await db.competitions.find_one(
        { "status": "completed" },
        sort=[("ends_at", -1), ("ended_at", -1)]
    )

    if last:
        joined = await db.competition_participants.find_one({
            "user_id": user_id,
            "competition_id": last["_id"],
        })
        if joined:
             return {
                "status": "ended",
                "competition": last,
                "can_register_next": is_registration_period_tr() and next_comp is not None,
            }
        else:
            return {
                "status": "missed",
                "competition": last,
                "can_register_next": is_registration_period_tr() and next_comp is not None,
            }
    
    return {"status": "none"}
