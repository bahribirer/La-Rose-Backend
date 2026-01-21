from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from datetime import datetime

from app.core.account_delete import delete_account
from app.core.dependencies import get_current_firebase_user
from app.core.database import db
from app.pharmacies.constants import REGION_REPRESENTATIVES
from app.users.schemas import ProfileUpdateRequest, UserProfileResponse
from app.users.service import save_avatar, try_auto_match_pharmacy, update_user_profile, serialize_profile
from bson import ObjectId
from app.users.schemas import MatchPharmacyRequest


router = APIRouter(prefix="/users", tags=["Users"])


async def get_current_db_user(
    firebase_user=Depends(get_current_firebase_user),
):
    firebase_uid = firebase_user["uid"]
    email = firebase_user.get("email")

    user = await db.users.find_one({"firebase_uid": firebase_uid})

    # 🔥 USER YOKSA OTOMATİK OLUŞTUR
    if not user:
        user_doc = {
        "firebase_uid": firebase_uid,
        "email": email,
        "created_at": datetime.utcnow(),

        # ✅ MUTLAKA OLMALI
        "phone_verified": False,
        "phone_verified_at": None,
        "email_verified": False,
        "email_verified": False,
        "onboarding_completed": False,
        "device_tokens": [],
    }

        result = await db.users.insert_one(user_doc)
        user_doc["_id"] = result.inserted_id

        return user_doc

    return user



@router.get("/me/profile", response_model=UserProfileResponse)
async def get_profile(
    current_user=Depends(get_current_db_user),
):
    print("🟡 USER DOC:", current_user)

    await try_auto_match_pharmacy(current_user["_id"])


    profile = await db.user_profiles.find_one(
        {"user_id": current_user["_id"]}
    )

    print("🟠 PROFILE DOC:", profile)

    result = serialize_profile(current_user, profile)
    print("🟢 SERIALIZED RESPONSE:", result)

    return result



@router.patch("/me/profile", response_model=UserProfileResponse)
async def update_profile(
    data: ProfileUpdateRequest,
    current_user=Depends(get_current_db_user),
):
    await update_user_profile(
        user_id=current_user["_id"],
        data=data,
    )

    profile = await db.user_profiles.find_one(
        {"user_id": current_user["_id"]}
    )
    return serialize_profile(current_user, profile)


@router.post("/me/profile/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user=Depends(get_current_db_user),
):
    # ✅ GERÇEK DOSYA KAYDEDİLİR
    avatar_url = await save_avatar(file, current_user["_id"])

    await db.user_profiles.update_one(
        {"user_id": current_user["_id"]},
        {
            "$set": {
                "avatar": avatar_url,
                "updated_at": datetime.utcnow(),
            },
            "$setOnInsert": {
                "user_id": current_user["_id"],
                "created_at": datetime.utcnow(),
            },
        },
        upsert=True,
    )

    return {"avatar": avatar_url}



@router.delete("/me", status_code=204)
async def delete_my_account(
    current_user=Depends(get_current_db_user),
):
    await delete_account(current_user)

@router.post("/me/device-token")
async def update_device_token(
    token: str = Query(...),
    current_user=Depends(get_current_db_user),
):
    await db.users.update_one(
        {"_id": current_user["_id"]},
        {"$addToSet": {"device_tokens": token}}
    )
    return {"status": "success", "message": "Token registered"}


@router.get("/debug/token")
async def debug_token(
    user=Depends(get_current_firebase_user)
):
    return {
        "firebase_uid": user["uid"]
    }

@router.post("/me/match-pharmacy")
async def match_pharmacy(
    data: MatchPharmacyRequest,
    current_user=Depends(get_current_db_user),
):
    try:
        pharmacy_id = ObjectId(data.pharmacy_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Geçersiz eczane ID")

    pharmacy = await db.pharmacies.find_one({"_id": pharmacy_id})
    if not pharmacy:
        raise HTTPException(status_code=404, detail="Eczane bulunamadı")

    region = pharmacy.get("region")
    representative_name = REGION_REPRESENTATIVES.get(region)

    await db.user_profiles.update_one(
        {"user_id": current_user["_id"]},
        {
            "$set": {
                "pharmacy_id": pharmacy["_id"],
                "pharmacy_name": pharmacy.get("pharmacy_name"),
                "district": pharmacy.get("district"),
                "region": region,
                # 🔥 SADECE STRING
                "representative": representative_name,
                "updated_at": datetime.utcnow(),
            },
            "$setOnInsert": {
                "user_id": current_user["_id"],
                "created_at": datetime.utcnow(),
            },
        },
        upsert=True,
    )

    profile = await db.user_profiles.find_one(
        {"user_id": current_user["_id"]}
    )

    return serialize_profile(current_user, profile)

@router.post("/me/reset-pharmacy")
async def reset_pharmacy(
    current_user=Depends(get_current_db_user),
):
    await db.user_profiles.update_one(
        {"user_id": current_user["_id"]},
        {
            "$set": {
                "pharmacy_id": None,
                "pharmacy_name": None,
                "district": None,
                "region": None,
                "representative": None,
                "updated_at": datetime.utcnow(),
            }
        },
    )

    profile = await db.user_profiles.find_one(
        {"user_id": current_user["_id"]}
    )

    return serialize_profile(current_user, profile)



