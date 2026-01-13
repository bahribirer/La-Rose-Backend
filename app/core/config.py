from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str
    MONGO_URI: str
    DB_NAME: str
    JWT_SECRET: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # 🔐 Secrets
    OPENAI_API_KEY: str
    GOOGLE_APPLICATION_CREDENTIALS: str      # Document AI
    FIREBASE_CREDENTIALS_PATH: str           # 🔥 Firebase Admin

    # 📩 Twilio
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    TWILIO_VERIFY_SID: str
    TWILIO_FROM_NUMBER: str

    # 🌐 API
    API_BASE_URL: str

    class Config:
        env_file = ".env"

settings = Settings()

