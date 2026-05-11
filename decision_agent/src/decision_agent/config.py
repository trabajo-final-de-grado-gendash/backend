"""
config.py — Configuración del decision_agent con Pydantic BaseSettings.
"""

from __future__ import annotations
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuración del agente decisor.
    """

    model_config = SettingsConfigDict(
        env_file=[
            ".env",
            str(Path(__file__).resolve().parent.parent.parent / ".env"),
            str(Path(__file__).resolve().parent.parent.parent.parent / ".env")
        ],
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.5-flash"
    SOURCE_DB_URL: str
    CONTEXT_WINDOW_SIZE: int = 5
    PIPELINE_TIMEOUT_SECONDS: int = 60
