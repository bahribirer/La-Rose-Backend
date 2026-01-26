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
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = SERVICE_ACCOUNT_PATH
cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)

def get_firebase_app():
    try:
        return firebase_admin.get_app("rosap")
    except ValueError:
        return firebase_admin.initialize_app(cred, name="rosap")

# Initialize default app as well for other services
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)
else:
    # Ensure default app has credentials too
    try:
        default_app = firebase_admin.get_app()
        # If we can't be sure it has creds, just use the named app elsewhere
    except:
        pass

# Trigger initialization
get_firebase_app()

def verify_firebase_token(token: str) -> dict:
    return auth.verify_id_token(
        token,
        clock_skew_seconds=60
    )
