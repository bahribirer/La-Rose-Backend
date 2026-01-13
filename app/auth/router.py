from fastapi import APIRouter, Depends
from datetime import datetime
from app.core.database import db
from app.core.dependencies import get_current_firebase_user

from fastapi import HTTPException
from pydantic import BaseModel

from app.core.twilio_client import twilio_client, TWILIO_VERIFY_SID

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.get("/me")
async def auth_me(firebase_user=Depends(get_current_firebase_user)):
    firebase_uid = firebase_user["uid"]
    email = firebase_user.get("email")

    user = await db.users.find_one({"firebase_uid": firebase_uid})

    if not user:
        user = {
            "firebase_uid": firebase_uid,
            "email": email,
            "created_at": datetime.utcnow(),

            # 🔥 KRİTİK DEFAULT STATE’LER
            "onboarding_completed": False,
            "phone_verified": False,
            "email_verified": False,
        }

        result = await db.users.insert_one(user)
        user["_id"] = result.inserted_id

    return {
    "id": str(user["_id"]),
    "firebase_uid": user["firebase_uid"],
    "email": user.get("email"),

    # 🔥 ADMIN PANEL İÇİN KRİTİK
    "role": user.get("role", "user"),

    # 🔥 MOBİL İÇİN
    "onboarding_completed": user.get("onboarding_completed", False),
    "phone_verified": user.get("phone_verified", False),
    "email_verified": user.get("email_verified", False),
}

class SendPhoneCodeRequest(BaseModel):
    phone: str  # +905xxxxxxxxx


class VerifyPhoneCodeRequest(BaseModel):
    phone: str
    code: str


@router.post("/phone/send-code")
async def send_phone_code(
    payload: SendPhoneCodeRequest,
    firebase_user=Depends(get_current_firebase_user),
):
    try:
        twilio_client.verify.services(
            TWILIO_VERIFY_SID
        ).verifications.create(
            to=payload.phone,
            channel="sms",
        )

        return {"status": "sent"}

    except Exception as e:
        print("❌ TWILIO SEND ERROR TYPE:", type(e))
        print("❌ TWILIO SEND ERROR:", repr(e))
        raise HTTPException(status_code=400, detail=str(e))



@router.post("/phone/verify-code")
async def verify_phone_code(
    payload: VerifyPhoneCodeRequest,
    firebase_user=Depends(get_current_firebase_user),
):
    try:
        result = twilio_client.verify.services(
            TWILIO_VERIFY_SID
        ).verification_checks.create(
            to=payload.phone,
            code=payload.code,
        )

        if result.status != "approved":
            raise HTTPException(status_code=401, detail="Kod hatalı")

        # ✅ DOĞRU UPDATE
        await db.users.update_one(
            {"firebase_uid": firebase_user["uid"]},
            {
                "$set": {
                    "phone_verified": True,
                    "phone_verified_at": datetime.utcnow(),
                }
            },
        )

        fresh_user = await db.users.find_one(
            {"firebase_uid": firebase_user["uid"]}
        )

        return {
            "verified": True,
            "phone_verified": fresh_user.get("phone_verified"),
            "phone_verified_at": fresh_user.get("phone_verified_at"),
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
