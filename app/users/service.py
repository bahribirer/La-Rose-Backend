from datetime import datetime
from typing import Optional
from bson import ObjectId
import os
import shutil
from uuid import uuid4
from fastapi import UploadFile

from app.core.database import db
from app.pharmacies.utils import normalize_text
from app.users.schemas import ProfileUpdateRequest


# ============================================================
# SERIALIZE PROFILE (GET RESPONSE)
# ============================================================

def serialize_profile(user: dict, profile: Optional[dict]):
    rep = None
    if profile:
        r = profile.get("representative")
        if isinstance(r, dict):
            rep = r.get("name") or r.get("full_name")
        elif isinstance(r, str):
            rep = r

    return {
        "id": str(user["_id"]),
        "email": user.get("email"),
        "full_name": user.get("full_name"),

        "phone_number": profile.get("phone_number") if profile else None,

        # ✅ DOĞRU YER
        "phone_verified": bool(user.get("phone_verified")),
        "phone_verified_at": user.get("phone_verified_at"),

        "birth_date": profile.get("birth_date") if profile else None,

        "free_text_pharmacy_name": (
            profile.get("free_text_pharmacy_name") if profile else None
        ),

        "pharmacy_id": (
            str(profile["pharmacy_id"])
            if profile and profile.get("pharmacy_id")
            else None
        ),
        "pharmacy_name": profile.get("pharmacy_name") if profile else None,
        "region": profile.get("region") if profile else None,
        "district": profile.get("district") if profile else None,

        "representative": rep,

        "position": profile.get("position") if profile else None,
        "avatar": profile.get("avatar") if profile else None,

        "onboarding_completed": bool(user.get("onboarding_completed")),
        "city": profile.get("city") if profile else None,
    }




# ============================================================
# GET PROFILE
# ============================================================

async def get_user_profile(user_id: ObjectId):
    user = await db.users.find_one({"_id": user_id})
    if not user:
        return None

    profile = await db.user_profiles.find_one({"user_id": user_id})

    return serialize_profile(user, profile)


# ============================================================
# UPDATE PROFILE (UPSERT)
# ============================================================

async def update_user_profile(
    user_id: ObjectId,
    data: ProfileUpdateRequest,
):
    payload = data.model_dump(exclude_none=True)
    if not payload:
        return {"status": "no_changes"}

    old_profile = await db.user_profiles.find_one({"user_id": user_id})

    user_fields = {}
    profile_fields = {}

    # 🔹 USERS COLLECTION
    if "full_name" in payload:
        user_fields["full_name"] = payload.pop("full_name")

    if "onboarding_completed" in payload:
        user_fields["onboarding_completed"] = payload["onboarding_completed"]

    # 🔹 PROFILE COLLECTION
    profile_fields = payload
    profile_fields["updated_at"] = datetime.utcnow()

    if user_fields:
        await db.users.update_one(
            {"_id": user_id},
            {"$set": user_fields},
        )

    await db.user_profiles.update_one(
        {"user_id": user_id},
        {
            "$set": profile_fields,
            "$setOnInsert": {
                "user_id": user_id,
                "created_at": datetime.utcnow(),
            },
        },
        upsert=True,
    )

    return {"status": "ok"}


# ============================================================
# AVATAR UPLOAD
# ============================================================

UPLOAD_DIR = "uploads/avatars"

async def save_avatar(
    file: UploadFile,
    user_id: ObjectId,
):
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    ext = file.filename.split(".")[-1]
    filename = f"{user_id}_{uuid4().hex}.{ext}"
    path = os.path.join(UPLOAD_DIR, filename)

    with open(path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return f"/uploads/avatars/{filename}"


# ============================================================
# DELETE USER (HARD DELETE)
# ============================================================

async def delete_user_completely(user_id: ObjectId):
    """
    Kullanıcıya ait TÜM verileri kalıcı olarak siler
    """

    profile = await db.user_profiles.find_one({"user_id": user_id})
    if profile:
        avatar_path = profile.get("avatar")
        if avatar_path and avatar_path.startswith("/uploads/avatars/"):
            full_path = avatar_path.lstrip("/")
            if os.path.exists(full_path):
                os.remove(full_path)

    await db.user_profiles.delete_one({"user_id": user_id})

    if "user_settings" in await db.list_collection_names():
        await db.user_settings.delete_one({"user_id": user_id})

    await db.users.delete_one({"_id": user_id})

    return True


async def delete_user_profile(user_id: ObjectId):
    """
    User profile + avatar delete
    """

    profile = await db.user_profiles.find_one({"user_id": user_id})

    if profile and profile.get("avatar"):
        avatar_path = profile["avatar"].lstrip("/")
        if os.path.exists(avatar_path):
            os.remove(avatar_path)

    await db.user_profiles.delete_one({"user_id": user_id})


async def try_auto_match_pharmacy(user_id: ObjectId):
    profile = await db.user_profiles.find_one({"user_id": user_id})
    if not profile:
        return False

    free_text = profile.get("free_text_pharmacy_name")
    if not free_text:
        return False

    normalized = normalize_text(free_text)

    pharmacy = await db.pharmacies.find_one(
        {
            "normalized_name": {
                "$regex": f".*{normalized}.*",
                "$options": "i",
            }
        }
    )

    if not pharmacy:
        return False

    # 🔥 OTOMATİK EŞLEŞME
    await db.user_profiles.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "pharmacy_id": pharmacy["_id"],
                "pharmacy_name": pharmacy["pharmacy_name"],
                "district": pharmacy.get("district"),
                "region": pharmacy.get("region"),
                "representative": pharmacy.get("representative"),
                "updated_at": datetime.utcnow(),
            },
            "$unset": {
                "free_text_pharmacy_name": ""
            },
        },
    )

    return True