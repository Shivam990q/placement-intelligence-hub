import os
from typing import List, Optional, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # App Settings
    APP_NAME: str = "Placement Intelligence Hub"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: List[str] = ["*"]
    
    # Database Settings (Defaults to zero-dependency SQLite async, supports PostgreSQL)
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///placement_hub.db",
        description="Async database connection string."
    )
    
    # Telegram Bot Settings
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHANNEL_ID: Optional[str] = ""
    TELEGRAM_FORUM_GROUP_ID: Optional[str] = ""
    TELEGRAM_ADMIN_IDS: List[int] = Field(default_factory=list)
    
    # Forum Topic Message Thread IDs
    TELEGRAM_TOPIC_INTERNSHIPS: Optional[int] = None
    TELEGRAM_TOPIC_FULLTIME: Optional[int] = None
    TELEGRAM_TOPIC_MASSHIRING: Optional[int] = None
    TELEGRAM_TOPIC_GENAI_OPS: Optional[int] = None
    TELEGRAM_TOPIC_RESOURCES: Optional[int] = None
    TELEGRAM_TOPIC_DISCUSSIONS: Optional[int] = None
    
    # Watchdog & Crawler Settings
    WATCHDOG_ENABLED: bool = True
    ETHARA_CHECK_INTERVAL_MINUTES: int = 15
    AMAZON_CHECK_INTERVAL_MINUTES: int = 30
    ATS_CHECK_INTERVAL_MINUTES: int = 60
    
    # Target Roles & Filtering Criteria
    TARGET_BATCHES: List[str] = ["2026", "2027", "2028"]
    TARGET_ROLES_KEYWORDS: List[str] = [
        "LLM", "GenOPS", "Post-Training", "Prompt", "SDE", "Software", "Intern", 
        "Graduate", "Associate", "Developer", "AI", "Machine Learning"
    ]

    @field_validator("TELEGRAM_ADMIN_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, v):
        if not v:
            return []
        if isinstance(v, list):
            return [int(x) for x in v]
        if isinstance(v, (int, float)):
            return [int(v)]
        if isinstance(v, str):
            v_clean = v.strip().strip("[]'\"")
            if not v_clean:
                return []
            return [int(x.strip()) for x in v_clean.split(",") if x.strip().isdigit()]
        return []

    @field_validator(
        "TELEGRAM_TOPIC_INTERNSHIPS",
        "TELEGRAM_TOPIC_FULLTIME",
        "TELEGRAM_TOPIC_MASSHIRING",
        "TELEGRAM_TOPIC_GENAI_OPS",
        "TELEGRAM_TOPIC_RESOURCES",
        "TELEGRAM_TOPIC_DISCUSSIONS",
        mode="before"
    )
    @classmethod
    def parse_optional_topic_id(cls, v):
        if v is None or v == "" or (isinstance(v, str) and not v.strip()):
            return None
        return int(v)

settings = Settings()
