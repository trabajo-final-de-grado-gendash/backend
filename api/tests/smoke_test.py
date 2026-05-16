import pytest
import uuid
from unittest.mock import MagicMock, AsyncMock
from decision_agent.models import DecisionAgentOutput, ResponseType

@pytest.mark.asyncio
async def test_health_check(async_client):
    client, _ = async_client
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_generate_end_to_end_mock(async_client):
    client, app = async_client
    
    mock_pipeline = MagicMock()
    mock_result = MagicMock()
    mock_session = MagicMock()
    
    from api.dependencies import get_pipeline_service, get_result_service, get_session_service
    
    app.dependency_overrides[get_pipeline_service] = lambda: mock_pipeline
    app.dependency_overrides[get_result_service] = lambda: mock_result
    app.dependency_overrides[get_session_service] = lambda: mock_session

    # Setup mock behavior
    mock_pipeline.run = AsyncMock(return_value=DecisionAgentOutput(
        response_type=ResponseType.VISUALIZATION,
        sql="SELECT 1",
        viz_result=MagicMock(plotly_json={"data": []}, plotly_code="import plotly"),
        message="Success"
    ))
    
    mock_id = uuid.uuid4()
    mock_result.save_result = AsyncMock(return_value=MagicMock(id=mock_id))
    mock_session.get_context_window = AsyncMock(return_value=[])
    mock_session.save_message = AsyncMock()
    
    payload = {
        "query": "test query",
        "session_id": str(uuid.uuid4())
    }
    
    response = await client.post("/api/v1/generate", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["response_type"] == "visualization"
    assert data["result_id"] == str(mock_id)
    assert data["sql"] == "SELECT 1"

@pytest.mark.asyncio
async def test_get_history_not_found(async_client):
    client, app = async_client
    mock_session = MagicMock()
    mock_session.get_session = AsyncMock(return_value=None)
    
    from api.dependencies import get_session_service
    app.dependency_overrides[get_session_service] = lambda: mock_session
    
    u = uuid.uuid4()
    response = await client.get(f"/api/v1/sessions/{u}/history")
    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found"

@pytest.mark.asyncio
async def test_get_result_not_found(async_client):
    client, app = async_client
    mock_result = MagicMock()
    mock_result.get_result_by_id = AsyncMock(return_value=None)
    
    from api.dependencies import get_result_service
    app.dependency_overrides[get_result_service] = lambda: mock_result
    
    u = uuid.uuid4()
    response = await client.get(f"/api/v1/results/{u}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Result not found"
