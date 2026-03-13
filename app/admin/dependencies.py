from fastapi import Depends, HTTPException, status
from app.core.dependencies import get_current_firebase_user
from app.core.database import db


async def admin_required(
    firebase_user=Depends(get_current_firebase_user),
):
    firebase_uid = firebase_user["uid"]

    user = await db.users.find_one({"firebase_uid": firebase_uid})

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # ✅ admin rolü VEYA panel_access yetkisi olanlar girebilir
    is_admin = user.get("role") == "admin"
    has_panel_access = user.get("panel_access") is True

    if not (is_admin or has_panel_access):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    return user
