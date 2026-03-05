from fastapi import FastAPI
from app.core import firebase
from app.auth.router import router as auth_router
from app.users.router import router as users_router
from fastapi.staticfiles import StaticFiles
from app.scan.router import router as scan_router
from app.products.router import router as products_router
from app.sales.router import router as sales_router
from app.admin.router import router as admin_router
from fastapi.middleware.cors import CORSMiddleware
from app.competitions.router import router as competitions_router
from app.pharmacies.router import router as pharmacies_router
from app.notifications.router import router as notifications_router
from app.field_visits.router import router as field_visits_router
from datetime import datetime
import os

# 🔥 Startup tracking
_STARTED_AT = datetime.utcnow()

app = FastAPI(
    title="La Rosee API",
    version="1.0.0",
    docs_url="/docs" if os.getenv("DEBUG", "false") == "true" else None,
    redoc_url=None,
)

# 🔐 CORS — production'da sıkılaştır
ALLOWED_ORIGINS = [
    "https://rosa-admin.vercel.app",
    "https://rose-admin.vercel.app",
    "http://localhost:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========================
# 🏥 HEALTH CHECK
# ========================
from app.core.database import db

@app.get("/health")
async def health_check():
    # MongoDB bağlantı kontrolü
    mongo_ok = False
    try:
        await db.command("ping")
        mongo_ok = True
    except Exception:
        pass

    uptime = (datetime.utcnow() - _STARTED_AT).total_seconds()

    return {
        "status": "ok" if mongo_ok else "degraded",
        "mongo": "connected" if mongo_ok else "disconnected",
        "uptime_seconds": round(uptime),
        "version": "1.0.0",
    }


# 🔥 ROUTER'LARI EKLE
app.include_router(auth_router)
app.include_router(users_router)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.include_router(scan_router)
app.include_router(products_router)
app.include_router(sales_router)
app.include_router(admin_router)
app.include_router(competitions_router)
app.include_router(pharmacies_router)
app.include_router(notifications_router)
app.include_router(field_visits_router)
