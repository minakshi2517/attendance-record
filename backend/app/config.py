import re

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./attendance.db"
    SECRET_KEY: str
    SETUP_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    CHECKOUT_LOCKOUT_MINUTES: int = 2
    TIMEZONE: str = "Asia/Kolkata"
    DEFAULT_ADMIN_USER: str
    DEFAULT_ADMIN_PASSWORD: str
    DEFAULT_ADMIN_EMAIL: str = "admin@ananta.local"
    ALLOWED_ORIGINS: str = "http://127.0.0.1:5173,http://localhost:5173"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        if value in {"change-this-in-production", "apna-random-secret-key-yahan-likho"}:
            raise ValueError("SECRET_KEY must be a unique random value from .env")
        return value

    @field_validator("SETUP_KEY")
    @classmethod
    def validate_setup_key(cls, value: str) -> str:
        if len(value) < 16:
            raise ValueError("SETUP_KEY must be at least 16 characters")
        if value == "SETUP_ATTENDANCE_2024":
            raise ValueError("SETUP_KEY must be rotated — use scripts/generate_env.py")
        return value

    @field_validator("DEFAULT_ADMIN_PASSWORD")
    @classmethod
    def validate_admin_password(cls, value: str) -> str:
        if len(value) < 12:
            raise ValueError("DEFAULT_ADMIN_PASSWORD must be at least 12 characters")
        if value.lower() in {"admin123", "password", "password123", "admin@123"}:
            raise ValueError("DEFAULT_ADMIN_PASSWORD is too weak")
        if not re.search(r"[A-Z]", value):
            raise ValueError("DEFAULT_ADMIN_PASSWORD needs an uppercase letter")
        if not re.search(r"[a-z]", value):
            raise ValueError("DEFAULT_ADMIN_PASSWORD needs a lowercase letter")
        if not re.search(r"\d", value):
            raise ValueError("DEFAULT_ADMIN_PASSWORD needs a digit")
        if not re.search(r"[!@#$%^&*]", value):
            raise ValueError("DEFAULT_ADMIN_PASSWORD needs a special character (!@#$%^&*)")
        return value

    @field_validator("DEFAULT_ADMIN_USER")
    @classmethod
    def validate_admin_user(cls, value: str) -> str:
        if value.lower() in {"admin", "root", "administrator"}:
            raise ValueError("DEFAULT_ADMIN_USER must not be a common default username")
        if len(value) < 6:
            raise ValueError("DEFAULT_ADMIN_USER must be at least 6 characters")
        return value

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]


settings = Settings()
