import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    project_name: str = "CRM SaaS"
    api_v1_str: str = "/api/v1"
    
    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]
    
    # Database
    database_url: str
    test_database_url: str | None = None
    
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

settings = Settings()
