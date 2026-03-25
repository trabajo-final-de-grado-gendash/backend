"""
conftest.py — Fixtures compartidos para los tests de la API.
"""

import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def async_client():
    """Cliente HTTP async para tests de endpoints FastAPI."""
    from api.main import create_app
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
