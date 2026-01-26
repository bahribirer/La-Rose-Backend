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

    # 0️⃣ GELECEK AY (UPCOMING)
    next_comp = await db.competitions.find_one(
        {
            "status": "upcoming",          # 🔥 filtre eklendi
            "starts_at": {"$gt": now_utc},
        },
        sort=[("starts_at", 1)]
    )

    if next_comp:
        registered_next = await db.competition_registrations.find_one({
            "user_id": user_id,
            "competition_id": next_comp["_id"],
        })

        if registered_next:
            return {
                "status": "registered",
                "competition": next_comp,
            }

    # 1️⃣ AKTİF YARIŞMA
    current = await db.competitions.find_one({
        "status": "active",                # 🔥 KRİTİK DÜZELTME
        "starts_at": {"$lte": now_utc},
        "ends_at": {"$gte": now_utc},
    })

    if current:
        accepted = await db.competition_participants.find_one({
            "user_id": user_id,
            "competition_id": current["_id"],
        })

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

                # 🔥 CLEANUP: Remove from registrations
                await db.competition_registrations.delete_one({"_id": registered["_id"]})

                return {
                    "status": "accepted",
                    "competition": current,
                }

        if accepted:
            # 🔥 BIREYSEL BITIŞ KONTROLÜ
            if accepted.get("finished_at") and accepted["finished_at"] <= now_utc:
                # Yarışma dünyada devam ediyor olsa bile BU kullanıcı bitmiş.
                # 'none' döndürerek onu normal 0/4 hedeflerine çekiyoruz (Normal Mod).
                return {
                    "status": "none",
                }
                
            return {
                "status": "accepted",
                "competition": current,
            }

        return {
            "status": "missed",
            "competition": current,
            "can_register_next": is_registration_period_tr(),
        }

    # 2️⃣ KAYIT AÇIK AMA YARIŞMA YOK (NEXT > LAST)
    if next_comp and is_registration_period_tr() :
        return {
            "status": "registration_open",
            "competition": next_comp,
        }

    # 3️⃣ SON YARIŞMA (BITMIS, IP TAL EDILMEMIS)
    last = await db.competitions.find_one(
        {
            "status": { "$in": ["completed"] },   # 🔥 iptal hariç
            "ends_at": {"$lt": now_utc},
        },
        sort=[("ends_at", -1)]
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
            }
        
        else:
            return {
                "status": "missed",
                "competition": last,
                "can_register_next": is_registration_period_tr(),
            }

    return {"status": "none"}
