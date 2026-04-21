# tests/test_config.py

import pytest
import os
from viz_agent.config import Settings

def test_config_init():
    """Test inicialización directa de Settings"""
    settings = Settings(
        GEMINI_API_KEY="test_key",
        GEMINI_MODEL="gemini-2.1-flash"
    )
    assert settings.GEMINI_API_KEY == "test_key"
    assert settings.GEMINI_MODEL == "gemini-2.1-flash"

def test_config_default_model():
    """Test modelo por defecto"""
    settings = Settings(GEMINI_API_KEY="test_key")
    assert settings.GEMINI_MODEL == "gemini-2.5-flash"

def test_config_from_env(monkeypatch):
    """Test carga desde variables de entorno"""
    monkeypatch.setenv("GEMINI_API_KEY", "env_key")
    monkeypatch.setenv("GEMINI_MODEL", "env_model")
    settings = Settings()
    assert settings.GEMINI_API_KEY == "env_key"
    assert settings.GEMINI_MODEL == "env_model"

def test_config_missing_key(monkeypatch):
    """Test error cuando falta la API Key"""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "partial_key")
    monkeypatch.delenv("LOG_DIR", raising=False)
    
    config = Config.from_env()
    
    assert config.gemini_api_key == "partial_key"
    assert config.log_dir == "logs"  # Default
