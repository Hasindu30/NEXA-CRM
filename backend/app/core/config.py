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
    
    # Auth & JWT
    jwt_signing_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    session_max_age_days: int = 30
    
    # CORS / CSRF Origin Validation
    allowed_origins: list[str] = ["http://localhost:3000"]
    
    cookie_secure: bool = True
    
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

settings = Settings()
