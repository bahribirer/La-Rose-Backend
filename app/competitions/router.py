from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime

from app.users.router import get_current_db_user
from app.core.database import db
from app.competitions.service import (
    get_user_competition_status,
    get_next_competition,
)
from app.competitions.utils import is_registration_period_tr

router = APIRouter(
    prefix="/competitions",
    tags=["Competitions"]
)

# =====================================================
# STATUS (MOBİL & ADMIN OKUR)
# =====================================================

@router.get("/status")
async def get_status(current_user=Depends(get_current_db_user)):
    res = await get_user_competition_status(current_user["_id"])

    response = {
        "status": res["status"],
    }

    if "can_register_next" in res:
        response["can_register_next"] = res["can_register_next"]

    if "competition" in res:
        c = res["competition"]
        response["competition"] = {
            "id": str(c["_id"]),
            "year": c["year"],
            "month": c["month"],
            "starts_at": c["starts_at"],
            "ends_at": c["ends_at"],
        }

    return response

# =====================================================
# REGISTER NEXT (GELECEK AY)
# =====================================================

@router.post("/register")
async def register_next_competition(
    current_user=Depends(get_current_db_user),
):
    now = datetime.utcnow()

    if not is_registration_period_tr():

        raise HTTPException(
            status_code=400,
            detail="Registration period not started",
        )

    next_comp = await get_next_competition()
    if not next_comp:
        raise HTTPException(404, "No upcoming competition")

    exists = await db.competition_registrations.find_one({
        "user_id": current_user["_id"],
        "competition_id": next_comp["_id"],
    })

    if exists:
        return {"status": "already_registered"}

    await db.competition_registrations.insert_one({
        "user_id": current_user["_id"],
        "competition_id": next_comp["_id"],
        "year": next_comp["year"],
        "month": next_comp["month"],
        "status": "registered",
        "created_at": now,
    })

    return {"status": "registered"}

# =====================================================
# ACCEPT CURRENT (SADECE ACTIVE YARIŞMA)
# =====================================================

@router.post("/accept")
async def accept_current_competition(
    current_user=Depends(get_current_db_user),
):
    now = datetime.utcnow()

    # 🔥 SADECE ACTIVE
    competition = await db.competitions.find_one({
        "status": "active",
        "starts_at": {"$lte": now},
        "ends_at": {"$gte": now},
    })

    if not competition:
        raise HTTPException(
            status_code=403,
            detail="competition_missed"
        )

    exists = await db.competition_participants.find_one({
        "user_id": current_user["_id"],
        "competition_id": competition["_id"],
    })

    if exists:
        return {"status": "accepted"}

    await db.competition_participants.insert_one({
        "user_id": current_user["_id"],
        "competition_id": competition["_id"],
        "accepted_at": now,
    })

    return {"status": "accepted"}
