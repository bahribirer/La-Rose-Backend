from fastapi import Depends, HTTPException, status
from app.core.dependencies import get_current_firebase_user
from app.core.database import db


async def admin_required(
    firebase_user=Depends(get_current_firebase_user),
):
    firebase_uid = firebase_user["uid"]

    user = await db.users.find_one({"firebase_uid": firebase_uid})

    print("🔥 ADMIN CHECK USER:", user)  # 👈 BUNU EKLE

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    return user
