"""Application configuration with safe development defaults."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None


@dataclass(frozen=True)
class Settings:
    environment: str
    database_path: Path
    gemini_api_key: str
    model_name: str

    @property
    def has_model_api_key(self) -> bool:
        return bool(self.gemini_api_key.strip())


def get_settings() -> Settings:
    """Load settings from environment variables and an optional .env file."""
    if load_dotenv is not None:
        load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        # Streamlit Community Cloud stores secrets in st.secrets, not os.environ.
        try:
            import streamlit as st

            api_key = str(st.secrets.get("GEMINI_API_KEY", "")).strip()
        except Exception:
            # Keep local development and non-Streamlit test environments usable.
            api_key = ""
    return Settings(
        environment=os.getenv("FORGEAI_ENV", "development").strip() or "development",
        database_path=Path(os.getenv("FORGEAI_DB_PATH", "data/forgeai.db")),
        gemini_api_key=api_key,
        model_name=os.getenv("FORGEAI_MODEL", "gemini-3.8-flash").strip() or "gemini-3.8-flash",
    )
