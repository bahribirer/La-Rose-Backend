import os
import firebase_admin
from firebase_admin import credentials, auth

# 🔥 CI/CD MOCK CHECK
IS_CI_MOCK = os.environ.get("CI_MOCK", "false").lower() == "true"

SERVICE_ACCOUNT_PATH = os.environ.get("FIREBASE_CREDENTIALS_PATH")

if not SERVICE_ACCOUNT_PATH and not IS_CI_MOCK:
    raise RuntimeError("FIREBASE_CREDENTIALS_PATH is not set")

if not IS_CI_MOCK:
    # 🔥 KRİTİK: Google Auth Fallback
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = SERVICE_ACCOUNT_PATH
    cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = SERVICE_ACCOUNT_PATH
else:
    # Mock creds for import checks
    class MockCred: pass
    cred = MockCred()

def get_firebase_app():
    if IS_CI_MOCK:
        class MockApp: pass
        return MockApp()

    # 💥 FORCE RESET: Delete existing app to ensure credentials are re-loaded
    try:
        existing_app = firebase_admin.get_app("rosap")
        firebase_admin.delete_app(existing_app)
        print("♻️ EXISTING APP DELETED FOR RE-AUTH")
    except ValueError:
        pass

    # 🔐 FORCE SCOPES
    print("🔐 CREATING SCOPED CREDENTIALS...")
    cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
    if hasattr(cred, 'create_scoped'):
        cred = cred.create_scoped([
            "https://www.googleapis.com/auth/firebase.messaging",
            "https://www.googleapis.com/auth/cloud-platform"
        ])
    
    return firebase_admin.initialize_app(cred, name="rosap")

# Initialize default app as well for other services
if not IS_CI_MOCK:
    if not firebase_admin._apps:
        print("🔥 INITIALIZING DEFAULT APP...")
        cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
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
