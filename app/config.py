# app/config.py
import os
import sys
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Read from OPENAI_API_KEY first, then API_KEY
    api_key: str = Field(
        default="",
        validation_alias="OPENAI_API_KEY",
    )
    # Optional second alias support (API_KEY) handled in _load_settings fallback.

    model_name: str = Field(default="gpt-4o-mini", validation_alias="MODEL_NAME")

    # Database path can be overridden; in Docker we usually use /app/data/intake_eval.db
    database_path: str = Field(default="intake_eval.db", validation_alias="DATABASE_PATH")

    jwt_secret: str = Field(default="", validation_alias="JWT_SECRET")
    env: str = Field(default="dev", validation_alias="ENV")
    cors_origins: str = Field(default="", validation_alias="CORS_ORIGINS")
    admin_secret: str = Field(default="", validation_alias="ADMIN_SECRET")
    in_docker: str = Field(default="", validation_alias="IN_DOCKER")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


def _load_settings() -> Settings:
    s = Settings()

    # --- API KEY: accept OPENAI_API_KEY or API_KEY, forbid placeholder ---
    # If OPENAI_API_KEY wasn't set, allow API_KEY as fallback.
    if not s.api_key:
        s.api_key = os.getenv("API_KEY", "").strip()

    if not s.api_key:
        print(
            "ERROR: OpenAI key not set. Provide OPENAI_API_KEY or API_KEY in environment/.env",
            file=sys.stderr,
        )
        sys.exit(1)

    if "your-openai-api-key-here" in s.api_key:
        print(
            "ERROR: OpenAI key is still the placeholder value. Fix OPENAI_API_KEY/API_KEY.",
            file=sys.stderr,
        )
        sys.exit(1)

    # --- JWT SECRET: required ---
    if not s.jwt_secret:
        print("ERROR: JWT_SECRET environment variable is required but not set.", file=sys.stderr)
        sys.exit(1)
    if len(s.jwt_secret) < 32:
        print("ERROR: JWT_SECRET must be at least 32 characters.", file=sys.stderr)
        sys.exit(1)

    # --- ADMIN SECRET: required ---
    if not s.admin_secret:
        print("ERROR: ADMIN_SECRET environment variable is required but not set.", file=sys.stderr)
        sys.exit(1)
    if len(s.admin_secret) < 16:
        print("ERROR: ADMIN_SECRET must be at least 16 characters.", file=sys.stderr)
        sys.exit(1)

    # --- DB PATH: normalize ---
    # If path is relative, make it relative to project root.
    # In Docker, DATABASE_PATH should already be absolute (/app/data/...)
    try:
        p = Path(s.database_path)
        if not p.is_absolute():
            # Resolve relative to current working dir (should be /app in container)
            s.database_path = str((Path.cwd() / p).resolve())
    except Exception:
        pass

    return s


settings = _load_settings()
