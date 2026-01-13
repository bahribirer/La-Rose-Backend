from datetime import datetime
from bson import ObjectId
from app.core.database import db


async def activate_competition_by_admin(competition_id: ObjectId):
    now = datetime.utcnow()

    comp = await db.competitions.find_one({ "_id": competition_id })
    if not comp:
        raise ValueError("Competition not found")

    if comp.get("status") == "active":
        return  # 🔒 idempotent

    await db.competitions.update_one(
        { "_id": competition_id },
        {
            "$set": {
                "status": "active",
                "activated_at": now,
            }
        }
    )

    regs = db.competition_registrations.find({
        "competition_id": competition_id,
        "status": "registered",
    })

    async for r in regs:
        await db.competition_participants.insert_one({
            "user_id": r["user_id"],
            "competition_id": competition_id,
            "accepted_at": now,
            "auto": True,
            "source": "admin_activation",
        })

    await db.competition_registrations.update_many(
        {
            "competition_id": competition_id,
            "status": "registered",
        },
        { "$set": { "status": "active" } }
    )
