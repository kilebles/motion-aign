from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class BotSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BOT_", env_file=".env", extra="ignore")

    token: str
