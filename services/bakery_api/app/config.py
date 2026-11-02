from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg://bakery:bakery@bakery-postgres:5432/bakery"
    ALLOW_DEMO_LOGIN: bool = True
    SECRET_KEY: str = "demo-secret-key-change-in-production"
    SESSION_COOKIE_NAME: str = "bakery_session"
    SESSION_MAX_AGE: int = 86400  # 24 hours
    CORS_ORIGINS: List[str] = [
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3000",
    ]
    SPECS_PATH: str = "/specs"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                import json

                return json.loads(v)
            return [x.strip() for x in v.split(",") if x.strip()]
        return v


@lru_cache()
def get_settings() -> Settings:
    return Settings()
