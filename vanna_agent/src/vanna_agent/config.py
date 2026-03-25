"""
config.py — Configuración del vanna_agent con Pydantic BaseSettings.

Carga automáticamente las variables de entorno desde .env.
Referencia: plan.md §Vanna Agent, vanna.ai/docs/configure/gemini/postgres
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuración del Vanna AI wrapper.

    Variables de entorno requeridas / opcionales:
        GEMINI_API_KEY  : API key de Google Gemini (obligatorio)
        GEMINI_MODEL    : Modelo Gemini a usar (default: gemini-2.5-pro)
        CHINOOK_DB_URL  : Connection string de PostgreSQL Chinook (obligatorio)
                          Ejemplo: postgresql://user:pass@host:5432/chinook
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.5-pro"
    CHINOOK_DB_URL: str
