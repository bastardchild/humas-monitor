from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Unmer Monitor API"
    SERPAPI_KEY: str
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    DATABASE_PATH: str = "./data/app.db"
    LITESTREAM_REPLICA_URL: Optional[str] = None
    LITESTREAM_S3_ENDPOINT: Optional[str] = None
    USE_SUPABASE: bool = False  # feature flag for rollback
    APIFY_API_TOKEN: Optional[str] = None
    APIFY_ACTOR_ID: str = "apify/instagram-post-scraper"
    APIFY_TIKTOK_ACTOR_ID: str = "clockworks/tiktok-scraper"
    
    # LLM Switcher
    LLM_PROVIDER: str = "gemini"  # Options: "deepseek", "gemini"

    # DeepSeek API Settings
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_API_BASE: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-flash-v4"

    # Gemini API Settings
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"

    FIRECRAWL_API_KEY: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()