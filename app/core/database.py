from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
import certifi

client = AsyncIOMotorClient(
    settings.MONGO_URI,
    # tls=True, # Production'da SSL/TLS sertifikaları ayarlandığında aktif edilebilir
    serverSelectionTimeoutMS=30000,
)

db = client[settings.DB_NAME]
