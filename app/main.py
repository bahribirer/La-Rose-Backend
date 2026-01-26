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







app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*"
         # 🔥 SENİN PORT
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



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
