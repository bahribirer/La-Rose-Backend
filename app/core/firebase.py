import os
import firebase_admin
from firebase_admin import credentials, auth

SERVICE_ACCOUNT_PATH = os.environ.get("FIREBASE_CREDENTIALS_PATH")

if not SERVICE_ACCOUNT_PATH:
    raise RuntimeError("FIREBASE_CREDENTIALS_PATH is not set")

cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)

# 🔥 KRİTİK: Firebase Başlatma
if not firebase_admin._apps:
    print(f"🔥 INITIALIZING FIREBASE ADMIN with: {SERVICE_ACCOUNT_PATH}")
    cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
    firebase_admin.initialize_app(cred)
else:
    print("✅ FIREBASE ADMIN ALREADY INITIALIZED")

def verify_firebase_token(token: str) -> dict:
    return auth.verify_id_token(
        token,
        clock_skew_seconds=60
    )
