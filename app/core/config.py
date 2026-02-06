from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "TaskMaster AI"
    # Si usas Turso: "sqlite+libsql://dbname.turso.io?authToken=..."
    # Si usas Local: "sqlite:///./tasks.db"
    DATABASE_URL: str = "sqlite:///./tasks.db"
    GEMINI_API_KEY: str

    class Config:
        env_file = ".env"


settings = Settings()