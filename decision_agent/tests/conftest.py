"""
conftest.py — Fixtures compartidos para los tests del decision_agent.
"""

import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_gemini_client():
    """Mock del cliente Gemini para evitar llamadas reales al LLM en unit tests."""
    return MagicMock()


@pytest.fixture
def mock_vanna_agent():
    """Mock del VannaAgent para aislar el DecisionAgent."""
    return MagicMock()


@pytest.fixture
def mock_viz_agent():
    """Mock del VizAgent para aislar el pipeline."""
    return MagicMock()


@pytest.fixture
def sample_query() -> str:
    return "total de ventas por género de cliente"


@pytest.fixture
def empty_conversation_history() -> list:
    return []
