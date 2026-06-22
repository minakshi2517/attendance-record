from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ✅ SQLite — koi install nahi chahiye
    DATABASE_URL: str = "sqlite:///./attendance.db"
    SECRET_KEY: str   = "change-this-in-production"
    ALGORITHM: str    = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    CHECKOUT_LOCKOUT_MINUTES: int    = 2
    TIMEZONE: str = "Asia/Kolkata"
    DEFAULT_ADMIN_USER: str = "admin"
    DEFAULT_ADMIN_PASSWORD: str = "admin123"
    DEFAULT_ADMIN_EMAIL: str = "admin@office.com"

    class Config:
        env_file = ".env"

settings = Settings()