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

async def mark_notification_as_read(user_id: ObjectId, notification_id: str):
    await db.notifications.update_one(
        {"_id": ObjectId(notification_id), "user_id": user_id},
        {"$set": {"is_read": True}}
    )

    await db.notifications.update_many(
        {"user_id": user_id, "is_read": False},
        {"$set": {"is_read": True}}
    )

async def delete_notification(user_id: ObjectId, notification_id: str):
    await db.notifications.delete_one(
        {"_id": ObjectId(notification_id), "user_id": user_id}
    )
