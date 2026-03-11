from __future__ import annotations

from typing import List, Optional
from pathlib import Path

from pydantic import field_validator, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # LLM
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"
    
    # Environment
    environment: str = "development"

    # Database & Storage
    database_url: str = "sqlite:///./incidents.db"
    upload_dir: Path = Path("uploads")

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    @computed_field
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @field_validator('openai_api_key', mode='before')
    @classmethod
    def clean_api_key(cls, v):
        if isinstance(v, str):
            return v.strip().replace('\n', '').replace('\r', '')
        return v

    @field_validator('database_url', mode='before')
    @classmethod 
    def fix_postgres_prefix(cls, v):
        """Fix postgres:// to postgresql:// for SQLAlchemy compatibility"""
        if isinstance(v, str) and v.startswith('postgres://'):
            return v.replace('postgres://', 'postgresql://', 1)
        return v

    # Modern Pydantic V2 configuration
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"  # Prevents crashes if extra vars are in .env
    )


settings = Settings()

# Ensure the upload directory exists as soon as the app starts
settings.upload_dir.mkdir(parents=True, exist_ok=True)

# Critical: Fail fast if OpenAI API key is missing in production
if not settings.openai_api_key and settings.environment == "production":
    import sys
    print("CRITICAL: OPENAI_API_KEY not found in production environment. This is required for AI features.")
    sys.exit(1)
