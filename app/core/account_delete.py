from app.core.database import db
from app.sales.cleanup import delete_user_sales
from app.users.service import delete_user_profile

async def delete_account(user: dict):
    user_id = user["_id"]

    try:
        # 🧹 SALES
        await delete_user_sales(user_id)

        # 🏆 COMPETITIONS
        await db.competition_registrations.delete_many({"user_id": user_id})
        await db.competition_participants.delete_many({"user_id": user_id})

        # 📊 SCOREBOARD
        await db.scores.delete_many({"user_id": user_id})

        # 🔔 NOTIFICATIONS
        await db.notifications.delete_many({"user_id": user_id})

        # 📅 FIELD VISITS
        await db.field_visits.delete_many({"user_id": user_id})

        # ⚙️ USER SETTINGS (SAFE)
        if "user_settings" in await db.list_collection_names():
            await db.user_settings.delete_one({"user_id": user_id})

        # 👤 PROFILE + AVATAR
        await delete_user_profile(user_id)

        # 🔥 USER (EN SON)
        await db.users.delete_one({"_id": user_id})

    except Exception as e:
        print("❌ DELETE ACCOUNT ERROR:", e)
        raise
