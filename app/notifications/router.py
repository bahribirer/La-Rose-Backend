from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
from app.core.dependencies import get_current_firebase_user
from app.core.database import db
from app.users.router import get_current_db_user
from app.notifications.schemas import NotificationResponse
from app.notifications.service import mark_notification_as_read, mark_all_read

router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.get("", response_model=List[NotificationResponse])
async def get_my_notifications(
    current_user=Depends(get_current_db_user),
    limit: int = 50,
):
    cursor = db.notifications.find(
        {"user_id": current_user["_id"]}
    ).sort("created_at", -1).limit(limit)
    
    notifications = []
    async for doc in cursor:
        notifications.append({
            "_id": str(doc["_id"]),
            "title": doc.get("title"),
            "body": doc.get("body"),
            "type": doc.get("type", "info"),
            "is_read": doc.get("is_read", False),
            "created_at": doc.get("created_at"),
        })
        
    return notifications

@router.patch("/{notification_id}/read")
async def read_notification(
    notification_id: str,
    current_user=Depends(get_current_db_user),
):
    await mark_notification_as_read(current_user["_id"], notification_id)
    return {"status": "success"}

@router.patch("/read-all")
async def read_all_notifications(
    current_user=Depends(get_current_db_user),
):
    await mark_all_read(current_user["_id"])
    return {"status": "success"}
