from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Unmer Monitor API"
    SERPAPI_KEY: str
    SUPABASE_URL: str
    SUPABASE_KEY: str
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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()