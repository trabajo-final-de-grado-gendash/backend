import os
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock

# Set dummy env vars for Settings validation before importing anything from api
os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost:5432/db"

@pytest.fixture
async def async_client():
    """Cliente HTTP async para tests de endpoints FastAPI."""
    from api.main import create_app
    from api.dependencies import get_db_session
    
    # Mock database engine to avoid real connection attempts
    with patch("api.main.get_engine"), patch("api.main.dispose_engine"):
        app = create_app()
        
        # Override dependency
        from unittest.mock import AsyncMock
        mock_session = AsyncMock()
        async def override_db_session():
            yield mock_session
            
        app.dependency_overrides[get_db_session] = override_db_session
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client, app
