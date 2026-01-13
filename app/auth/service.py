from datetime import datetime
from bson import ObjectId

from app.core.database import db
from app.users.schemas import ProfileUpdateRequest


async def update_user_profile(
    user_id: ObjectId,
    data: ProfileUpdateRequest,
):
    """
    Firebase-authenticated user profile update
    - Sadece gönderilen alanlar update edilir
    - full_name -> users
    - diğer alanlar -> user_profiles
    """

    payload = data.model_dump(exclude_none=True)

    if not payload:
        return {"status": "no_changes"}

    user_fields = {}
    profile_fields = {}

    # USERS collection
    if "full_name" in payload:
        user_fields["full_name"] = payload.pop("full_name")

    # USER_PROFILES collection
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
