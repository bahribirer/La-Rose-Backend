from datetime import datetime
from app.core.database import db
from app.core import firebase
from bson import ObjectId
import firebase_admin
from firebase_admin import messaging, credentials
import os

async def send_push_notification(user_id: ObjectId, title: str, body: str, data: dict = None):
    """
    Sends a Firebase Cloud Message using RAW HTTP (Bypassing SDK Auth Issues).
    """
    try:
        # 1. Get User & Token
        user = await db.users.find_one({"_id": user_id})
        if not user or not user.get("device_tokens"):
            return

        tokens = [t for t in user.get("device_tokens", []) if t]
        if not tokens:
            return

        target_token = tokens[-1]
        print(f"📡 SENDING RAW HTTP PUSH to: {target_token}")

        # 2. Manual Auth (Proven Working)
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request
        import os
        import requests
        import json

        creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        scopes = ["https://www.googleapis.com/auth/firebase.messaging"]
        
        creds = service_account.Credentials.from_service_account_file(creds_path, scopes=scopes)
        creds.refresh(Request())
        access_token = creds.token
        project_id = creds.project_id

        # 3. Construct Raw Payload (FCM V1)
        endpoint = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
        
        payload = {
            "message": {
                "token": target_token,
                "notification": {
                    "title": title,
                    "body": body
                },
                "data": {
                    **(data or {}),
                    "click_action": "FLUTTER_NOTIFICATION_CLICK"
                },
                "apns": {
                    "headers": {
                        "apns-priority": "10",
                        "apns-topic": "com.bahribirer.rosap"
                    },
                    "payload": {
                        "aps": {
                            "alert": {
                                "title": title,
                                "body": body
                            },
                            "sound": "default",
                            "badge": 1,
                            "content-available": 1,
                            "mutable-content": 1
                        }
                    }
                }
            }
        }

        # 4. Send Request
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        response = requests.post(endpoint, headers=headers, data=json.dumps(payload))
        
        if response.status_code == 200:
            print(f"🔥 RAW FCM SUCCESS: {response.json()}")
            return response.json()
        elif response.status_code in [401, 403, 404, 400] and ("UNREGISTERED" in response.text or "BadEnvironmentKeyInToken" in response.text):
            print(f"🧹 Removing invalid token (Unregistered or Bad Env): {target_token}")
            await db.users.update_one(
                {"_id": user_id},
                {"$pull": {"device_tokens": target_token}}
            )
        else:
            print(f"❌ RAW FCM ERROR ({response.status_code}): {response.text}")

    except Exception as e:
        print(f"❌ GENERAL RAW PUSH ERROR: {str(e)}")

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
