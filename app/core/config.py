import os
from pathlib import Path
from pydantic_settings import BaseSettings


BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"


class Settings(BaseSettings):
    PROJECT_NAME: str = "TaskMaster AI"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./tasks.db")

    GEMINI_API_KEY: str
    TELEGRAM_TOKEN: str

    SECRET_KEY: str  # Obligatorio — sin fallback. Debe estar en .env
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    SECURE_COOKIES: bool = False   # True en producción (HTTPS)
    COOKIE_SAMESITE: str = "lax"

    # SSRF: calendarios (vacío = solo bloquear IPs privadas/loopback)
    ALLOWED_CALENDAR_HOSTS: list[str] = []
    CALENDAR_REQUIRE_HTTPS: bool = False  # True en producción si solo quieres https

    class Config:

        env_file = str(ENV_PATH)
        env_file_encoding = 'utf-8'

        extra = "ignore"


settings = Settings()