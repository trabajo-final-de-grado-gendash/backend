"""
config.py — Configuración del decision_agent con Pydantic BaseSettings.

Carga automáticamente las variables de entorno desde .env.
Referencia: plan.md §Contexto Técnico
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuración del agente decisor.

    Variables de entorno requeridas / opcionales:
        GEMINI_API_KEY       : API key de Google Gemini (obligatorio)
        GEMINI_MODEL         : Modelo Gemini a usar (default: gemini-2.5-flash)
        CHINOOK_DB_URL       : Connection string de la BD Chinook (obligatorio)
        CONTEXT_WINDOW_SIZE  : Tamaño de la ventana conversacional (default: 5)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.5-flash"
    CHINOOK_DB_URL: str
    CONTEXT_WINDOW_SIZE: int = 5
