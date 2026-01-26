from datetime import datetime
from app.core.database import db
from bson import ObjectId
from firebase_admin import messaging

async def send_push_notification(user_id: ObjectId, title: str, body: str, data: dict = None):
    """
    Sends a Firebase Cloud Message to the user's registered devices.
    """
    try:
        user = await db.users.find_one({"_id": user_id})
        if not user or not user.get("device_tokens"):
            return

        tokens = [t for t in user.get("device_tokens", []) if t]
        if not tokens:
            return

        # 🎯 Sadece en son kaydedilen (güncel) cihaza gönder
        target_token = tokens[-1]
        print(f"📡 SENDING PUSH TO LAST TOKEN for USER {user_id}: {target_token}")

        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data={
                **(data or {}),
                "click_action": "FLUTTER_NOTIFICATION_CLICK"
            },
            tokens=[target_token],
            apns=messaging.APNSConfig(
                headers={
                    "apns-priority": "10",
                    "apns-topic": "com.bahribirer.rosap",
                },
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        alert=messaging.ApsAlert(
                            title=title,
                            body=body,
                        ),
                        sound="default",
                        badge=1,
                        mutable_content=True,
                        content_available=True,
                    ),
                ),
            ),
        )

        response = messaging.send_each_for_multicast(message)
        print(f"🔥 FCM SENT: {response.success_count} success, {response.failure_count} failure")
        
        # Optional: Clean up invalid tokens
        if response.failure_count > 0:
            responses = response.responses
            failed_tokens = []
            for idx, resp in enumerate(responses):
                if not resp.success:
                    print(f"❌ FCM TOKEN FAILURE [{idx}]: {resp.exception}")
                    failed_tokens.append(tokens[idx])
            
            if failed_tokens:
                await db.users.update_one(
                    {"_id": user_id},
                    {"$pull": {"device_tokens": {"$in": failed_tokens}}}
                )
                print(f"🧹 Removed {len(failed_tokens)} invalid tokens")

    except Exception as e:
        print(f"❌ FCM ERROR: {e}")

async def create_notification(user_id: ObjectId, title: str, body: str, type: str = "info"):
    """
    Creates a persistent notification in MongoDB and sends a Push Notification.
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

    # 🔥 SEND COMPANION PUSH
    await send_push_notification(user_id, title, body, data={"type": type})

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
