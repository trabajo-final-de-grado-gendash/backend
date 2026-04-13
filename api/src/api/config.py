"""
config.py — Configuración de la API con Pydantic BaseSettings.
"""

from __future__ import annotations
from pathlib import Path
from typing import Annotated, Any, Union
from pydantic import BeforeValidator
from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_cors_origins(v: Any) -> list[str]:
    """Validador para convertir strings sep. por coma en listas."""
    if isinstance(v, str):
        return [i.strip() for i in v.split(",")]
    return v


class Settings(BaseSettings):
    """
    Configuración central de la API.
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

    # Database
    APP_DB_URL: str

    # Security
    CORS_ORIGINS: Annotated[list[str], BeforeValidator(parse_cors_origins)] = [
        "http://localhost:3000"
    ]

    # AI Shared
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.5-flash"
    CONTEXT_WINDOW_SIZE: int = 5
