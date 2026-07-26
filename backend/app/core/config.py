# backend/app/core/config.py

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Unmer Monitor API"
    SERPAPI_KEY: str
    SUPABASE_URL: str
    SUPABASE_KEY: str
    APIFY_API_TOKEN: Optional[str] = None
    APIFY_ACTOR_ID: str = "nH2AHrwxeTRJoN5hX"  # Default fallback jika tidak ada di .env

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()