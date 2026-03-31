"""
conftest.py — Fixtures compartidos para los tests del vanna_agent.
"""

import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_gemini_llm():
    """Mock del servicio LLM de Gemini para unit tests rápidos."""
    return MagicMock()


@pytest.fixture
def mock_postgres_runner():
    """Mock del runner de PostgreSQL para unit tests rápidos."""
    return MagicMock()


@pytest.fixture
def sample_nl_query() -> str:
    return "total de ventas por género de cliente"


@pytest.fixture
def sample_sql() -> str:
    return "SELECT c.Gender, SUM(i.Total) AS total_sales FROM Customer c JOIN Invoice i ON c.CustomerId = i.CustomerId GROUP BY c.Gender"
