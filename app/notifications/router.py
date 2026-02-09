from fastapi import APIRouter, Depends, HTTPException, Query
from bson import ObjectId
from typing import List, Optional
from app.core.dependencies import get_current_firebase_user
from pydantic import BaseModel
from app.core.database import db
from app.users.router import get_current_db_user
from app.admin.dependencies import admin_required
from app.notifications.schemas import NotificationResponse
from app.notifications.service import mark_notification_as_read, mark_all_read, delete_notification, delete_all_notifications

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

    await mark_all_read(current_user["_id"])
    return {"status": "success"}

@router.delete("/{notification_id}")
async def remove_notification(
    notification_id: str,
    current_user=Depends(get_current_db_user),
):
    await delete_notification(current_user["_id"], notification_id)
    return {"status": "success"}

@router.delete("/")
async def remove_all_notifications(
    current_user=Depends(get_current_db_user),
):
    await delete_all_notifications(current_user["_id"])
    return {"status": "success"}

# ================= ADMIN NOTIFICATIONS =================
@router.get("/admin/notifications")
async def get_admin_notifications(
    limit: int = 10,
    user=Depends(admin_required)
):
    cursor = db.admin_notifications.find().sort("created_at", -1).limit(limit)
    
    notifications = []
    async for n in cursor:
        notifications.append({
            "id": str(n["_id"]),
            "title": n.get("title"),
            "body": n.get("body"),
            "type": n.get("type"),
            "is_read": n.get("is_read", False),
            "created_at": n["created_at"],
            "data": n.get("data", {})
        })
        
    return notifications

@router.delete("/admin/notifications/{notification_id}")
async def delete_admin_notification(
    notification_id: str,
    user=Depends(admin_required)
):
    if not ObjectId.is_valid(notification_id):
        raise HTTPException(400, "Invalid ID")
        
    result = await db.admin_notifications.delete_one({"_id": ObjectId(notification_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(404, "Notification not found")
        
    return {"status": "success"}

class SendNotificationRequest(BaseModel):
    user_id: Optional[str] = None
    title: str
    body: str

@router.post("/admin/send")
async def send_admin_notification(
    payload: SendNotificationRequest,
    user=Depends(admin_required)
):
    from app.notifications.service import create_notification
    
    # If user_id provided, send to that user
    if payload.user_id:
        if not ObjectId.is_valid(payload.user_id):
            raise HTTPException(400, "Invalid User ID")
        
        await create_notification(
            user_id=ObjectId(payload.user_id),
            title=payload.title,
            body=payload.body,
            type="admin_message"
        )
        return {"status": "sent", "target": "single"}
    
    # If no user_id, send to ALL users (Broadcast) - dangerous but powerful
    # For now, let's just find all users with tokens
    users = await db.users.find({"device_tokens": {"$exists": True, "$ne": []}}).to_list(None)
    
    count = 0
    for u in users:
        await create_notification(
            user_id=u["_id"],
            title=payload.title,
            body=payload.body,
            type="admin_broadcast"
        )
        count += 1
        
    return {"status": "sent", "target": "broadcast", "count": count}
