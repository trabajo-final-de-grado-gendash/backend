# tests/test_config.py

import pytest
import os
from viz_agent.config import Config


def test_config_initialization():
    """Test inicialización directa de Config"""
    config = Config(
        gemini_api_key="test_key_123",
        log_dir="custom_logs",
        max_correction_attempts=3
    )
    
    assert config.gemini_api_key == "test_key_123"
    assert config.log_dir == "custom_logs"
    assert config.max_correction_attempts == 3


def test_config_defaults():
    """Test valores por defecto"""
    config = Config(gemini_api_key="test_key")
    
    assert config.gemini_api_key == "test_key"
    assert config.log_dir == "logs"
    assert config.max_correction_attempts == 5


def test_config_from_env(monkeypatch):
    """Test carga desde variables de entorno"""
    monkeypatch.setenv("GEMINI_API_KEY", "env_test_key")
    monkeypatch.setenv("LOG_DIR", "env_logs")
    monkeypatch.setenv("MAX_CORRECTION_ATTEMPTS", "10")
    
    config = Config.from_env()
    
    assert config.gemini_api_key == "env_test_key"
    assert config.log_dir == "env_logs"
    assert config.max_correction_attempts == 10


def test_config_from_env_defaults(monkeypatch):
    """Test defaults cuando no hay variables de entorno"""
    # Limpiar variables de entorno
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("LOG_DIR", raising=False)
    monkeypatch.delenv("MAX_CORRECTION_ATTEMPTS", raising=False)
    
    config = Config.from_env()
    
    assert config.gemini_api_key == ""
    assert config.log_dir == "logs"
    assert config.max_correction_attempts == 5


def test_config_from_env_partial(monkeypatch):
    """Test con solo algunas variables de entorno"""
    monkeypatch.setenv("GEMINI_API_KEY", "partial_key")
    monkeypatch.delenv("LOG_DIR", raising=False)
    
    config = Config.from_env()
    
    assert config.gemini_api_key == "partial_key"
    assert config.log_dir == "logs"  # Default
