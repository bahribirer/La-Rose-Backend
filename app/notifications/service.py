from datetime import datetime
from app.core.database import db
from bson import ObjectId

async def create_notification(user_id: ObjectId, title: str, body: str, type: str = "info"):
    """
    Creates a persistent notification in MongoDB.
    """
    notification = {
        "user_id": user_id,
        "title": title,
        "body": body,
        "type": type,
        "is_read": False,
        "created_at": datetime.utcnow()
    }
    
    await db.notifications.insert_one(notification)
    print(f"✅ NOTIFICATION SAVED TO DB: {title} -> {user_id}")

async def create_admin_notification(title: str, body: str, type: str = "goal_reached", data: dict = None):
    """
    Creates a notification intended for the Admin Panel.
    """
    notification = {
        "title": title,
        "body": body,
        "type": type,
        "data": data or {},
        "is_read": False,
        "created_at": datetime.utcnow()
    }
    await db.admin_notifications.insert_one(notification)
    print(f"👮 ADMIN NOTIFICATION: {title}")

async def mark_notification_as_read(user_id: ObjectId, notification_id: str):
    await db.notifications.update_one(
        {"_id": ObjectId(notification_id), "user_id": user_id},
        {"$set": {"is_read": True}}
    )

async def mark_all_read(user_id: ObjectId):
    await db.notifications.update_many(
        {"user_id": user_id, "is_read": False},
        {"$set": {"is_read": True}}
    )

async def delete_notification(user_id: ObjectId, notification_id: str):
    await db.notifications.delete_one(
        {"_id": ObjectId(notification_id), "user_id": user_id}
    )

async def delete_all_notifications(user_id: ObjectId):
    await db.notifications.delete_many(
        {"user_id": user_id}
    )
