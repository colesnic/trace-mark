"""Application configuration via pydantic-settings.

All secrets come from environment variables / a local .env file. Nothing
secret is ever hardcoded.
"""

from __future__ import annotations

import base64
import secrets

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TRACEMARK_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: str = Field(default="development", alias="TRACEMARK_ENV")

    database_url: str = "sqlite+aiosqlite:///./tracemark.db"

    # Base64-encoded root master key. If unset and running in development,
    # a random key is derived so the project runs out of the box. Never rely
    # on the auto-generated key for real deployments.
    master_key: str | None = None

    # Development-only admin bearer token for admin endpoints.
    admin_token: str | None = None

    # Provider API keys (loaded from environment, never logged).
    openai_api_key: str | None = None
    deepseek_api_key: str | None = None
    anthropic_api_key: str | None = None

    # Development-only raw content retention (prompts/responses in the DB).
    retain_raw: bool = False

    @property
    def is_development(self) -> bool:
        return self.env.lower() == "development"

    def resolve_master_key(self) -> bytes:
        """Return the root master key as raw bytes.

        When unset and running in development, generate a fresh random key
        and persist it to .env so subsequent processes stay consistent.
        """
        if self.master_key:
            try:
                return base64.b64decode(self.master_key)
            except Exception as exc:  # pragma: no cover - defensive
                raise ValueError("TRACEMARK_MASTER_KEY is not valid base64") from exc

        if not self.is_development:
            raise RuntimeError(
                "TRACEMARK_MASTER_KEY must be configured outside development mode"
            )

        fresh = secrets.token_bytes(32)
        encoded = base64.b64encode(fresh).decode()
        self._persist_env_master_key(encoded)
        return fresh

    def _persist_env_master_key(self, encoded: str) -> None:
        import os

        env_path = ".env"
        line = f"TRACEMARK_MASTER_KEY={encoded}\n"
        existing = ""
        if os.path.exists(env_path):
            with open(env_path, encoding="utf-8") as fh:
                existing = fh.read()
        if "TRACEMARK_MASTER_KEY=" in existing:
            return
        with open(env_path, "a", encoding="utf-8") as fh:
            fh.write(line)

    def resolve_admin_token(self) -> str | None:
        if self.admin_token:
            return self.admin_token
        if self.is_development:
            return "dev-admin-token"
        return None

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


def get_settings() -> Settings:
    return Settings()
