from __future__ import annotations

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class GoogleAISettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GOOGLE_", env_file=".env", extra="ignore")

    api_key: str
    model: str = "gemini-2.5-flash"


class Settings(BaseModel):
    google: GoogleAISettings


def get_settings() -> Settings:
    return Settings(google=GoogleAISettings())
