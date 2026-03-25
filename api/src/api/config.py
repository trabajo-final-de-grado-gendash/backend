"""
config.py — Configuración de la API con Pydantic BaseSettings.

Carga automáticamente las variables de entorno desde .env.
Referencia: plan.md §API
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuración de la API REST de Gen BI.

    Variables de entorno requeridas / opcionales:
        DATABASE_URL          : Connection string de PostgreSQL para persistencia (obligatorio)
                                Ejemplo: postgresql+asyncpg://user:pass@host:5432/genbi_db
        CORS_ORIGINS          : Orígenes CORS permitidos separados por coma
                                (default: ["http://localhost:3000"])
        CONTEXT_WINDOW_SIZE   : Tamaño de la ventana de contexto conversacional (default: 5)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    DATABASE_URL: str
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    CONTEXT_WINDOW_SIZE: int = 5
