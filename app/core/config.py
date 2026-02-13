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
    
    SECRET_KEY: str = "your-secret-key-here" # Fallback only for dev, should be in .env
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:

        env_file = str(ENV_PATH)
        env_file_encoding = 'utf-8'

        extra = "ignore"


settings = Settings()