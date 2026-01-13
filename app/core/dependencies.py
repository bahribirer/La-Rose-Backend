from typing import Optional
from fastapi import HTTPException, Header
from app.core.firebase import verify_firebase_token
import time


async def get_current_firebase_user(
    authorization: Optional[str] = Header(None),
):
    print("AUTH HEADER:", authorization)

    if not authorization:
        raise HTTPException(401, "Authorization header missing")

    if not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Invalid Authorization header format")

    token = authorization[7:].strip()

    if not token:
        raise HTTPException(401, "Empty token")

    # 🔁 RETRY MEKANİZMASI (KRİTİK)
    last_error = None

    for attempt in range(2):
        try:
            decoded = verify_firebase_token(token)
            print("DECODED UID:", decoded.get("uid"))
            return decoded

        except Exception as e:
            print(f"VERIFY ERROR (attempt {attempt + 1}):", str(e))
            last_error = e
            time.sleep(0.5)  # Firebase token refresh için nefes

    raise HTTPException(
        status_code=401,
        detail="Invalid or expired Firebase token",
    )
