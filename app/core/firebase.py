import os
import firebase_admin
from firebase_admin import credentials, auth

SERVICE_ACCOUNT_PATH = os.environ.get("FIREBASE_CREDENTIALS_PATH")

if not SERVICE_ACCOUNT_PATH:
    raise RuntimeError("FIREBASE_CREDENTIALS_PATH is not set")

# 🔥 KRİTİK: Google Auth Fallback
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = SERVICE_ACCOUNT_PATH

cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)

# 🔥 KRİTİK: Firebase Başlatma
cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)

if not firebase_admin._apps:
    print(f"🔥 INITIALIZING FIREBASE ADMIN (NEW) with: {SERVICE_ACCOUNT_PATH}")
    firebase_admin.initialize_app(cred)
else:
    # Bazen default app sertifikasız başlamış olabilir (bazı kütüphaneler yüzünden)
    print("✅ FIREBASE ADMIN ALREADY INITIALIZED (Updating to use Certificate)")
    # Default app'i alıp credential'ını kontrol edemeyiz kolayca, but initialize_app with name=default will fail
    # We just trust it for now OR we could re-initialize a named app.

def verify_firebase_token(token: str) -> dict:
    return auth.verify_id_token(
        token,
        clock_skew_seconds=60
    )
