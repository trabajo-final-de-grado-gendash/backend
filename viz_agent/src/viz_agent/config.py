# viz_agent/config.py

from __future__ import annotations
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuración del agente de visualización con Pydantic.
    
    Busca variables en orden:
    1. .env local
    2. .env en la raíz de viz_agent
    3. .env en la raíz de backend/ (maestro)
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
    VIZ_LOG_DIR: str = "logs"
    MAX_CORRECT_ATTEMPTS: int = 5

    # LangSmith observability (opcional)
    LANGCHAIN_TRACING_V2: str | None = None
    LANGCHAIN_ENDPOINT: str | None = None
    LANGCHAIN_API_KEY: str | None = None
    LANGCHAIN_PROJECT: str | None = None
