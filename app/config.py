from __future__ import annotations

from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"
    
    # Environment
    environment: str = "development"

    @field_validator('openai_api_key', mode='before')
    @classmethod
    def clean_api_key(cls, v):
        if v:
            return str(v).strip().replace('\n', '').replace('\r', '')
        return v

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # Database
    database_url: str = "sqlite:///./incidents.db"

    # Uploads
    upload_dir: str = "uploads"

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
