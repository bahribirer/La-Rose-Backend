from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "La Rosee API"
    
    # 🗄️ MongoDB Configuration
    MONGO_HOST: str = "localhost"
    MONGO_PORT: int = 27017
    MONGO_USER: str | None = None
    MONGO_PASS: str | None = None
    DB_NAME: str = "rosap_db"
    
    @property
    def MONGO_URI(self) -> str:
        if self.MONGO_USER and self.MONGO_PASS:
            # Docker/Production with Auth
            return f"mongodb://{self.MONGO_USER}:{self.MONGO_PASS}@{self.MONGO_HOST}:{self.MONGO_PORT}/{self.DB_NAME}?authSource=admin"
        # Local without Auth
        return f"mongodb://{self.MONGO_HOST}:{self.MONGO_PORT}/{self.DB_NAME}"

    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # 🔐 Secrets
    OPENAI_API_KEY: str
    GROQ_API_KEY: str | None = None          # 🚀 Groq / Llama 3 (Optional)
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

