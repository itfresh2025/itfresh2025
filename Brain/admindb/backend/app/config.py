from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "AdminDB Web"
    SECRET_KEY: str = "change-me-in-production-use-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours

    DATABASE_URL: str = "sqlite:///./admindb.db"

    FERNET_KEY: str = ""  # Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

    FIRST_ADMIN_USERNAME: str = "admin"
    FIRST_ADMIN_PASSWORD: str = "admin123"

    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_NOTIFY_CHAT_ID: str = ""

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
