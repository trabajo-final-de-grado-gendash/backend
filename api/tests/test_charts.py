"""
tests/test_charts.py — Tests para los endpoints de actualización de gráficos.

TFG-56: PATCH /api/v1/charts/{chart_id}/metadata
TFG-57: POST  /api/v1/charts/{chart_id}/regenerate
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_VIZ_JSON = {
    "data": [
        {
            "type": "bar",
            "x": ["A", "B", "C"],
            "y": [10, 20, 30],
        }
    ],
    "layout": {
        "title": {"text": "Original Title"},
        "xaxis": {"title": {"text": "Categories"}},
        "yaxis": {"title": {"text": "Values"}},
    },
}


def _make_mock_chart(
    chart_id: uuid.UUID | None = None,
    viz_json: dict | None = None,
):
    """Crea un mock de GenerationResult con los campos necesarios."""
    mock = MagicMock()
    mock.id = chart_id or uuid.uuid4()
    mock.session_id = uuid.uuid4()
    mock.query = "ventas por categoría"
    mock.sql = "SELECT category, SUM(sales) FROM sales GROUP BY category"
    mock.viz_json = viz_json or SAMPLE_VIZ_JSON.copy()
    mock.plotly_code = "import plotly.express as px; fig = px.bar(...)"
    mock.chart_type = "bar"
    mock.created_at = "2026-04-12T00:00:00Z"
    return mock


# ===========================================================================
# TFG-56: Update Metadata Tests
# ===========================================================================


class TestUpdateMetadata:
    """Tests para PATCH /api/v1/charts/{chart_id}/metadata."""

    @pytest.mark.asyncio
    async def test_update_metadata_title(self, async_client):
        """Actualizar solo el título del gráfico."""
        client, app = async_client
        chart_id = uuid.uuid4()

        mock_chart = _make_mock_chart(chart_id)
        updated_viz_json = SAMPLE_VIZ_JSON.copy()
        updated_viz_json["layout"] = {
            **SAMPLE_VIZ_JSON["layout"],
            "title": {"text": "New Title"},
        }
        mock_updated = _make_mock_chart(chart_id, updated_viz_json)

        mock_service = AsyncMock()
        mock_service.update_metadata.return_value = (mock_updated, ["title"])

        from api.dependencies import get_chart_service
        app.dependency_overrides[get_chart_service] = lambda: mock_service

        response = await client.patch(
            f"/api/v1/charts/{chart_id}/metadata",
            json={"title": "New Title"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["chart_id"] == str(chart_id)
        assert "title" in data["updated_fields"]
        assert data["plotly_json"]["layout"]["title"]["text"] == "New Title"

    @pytest.mark.asyncio
    async def test_update_metadata_axes(self, async_client):
        """Actualizar ejes X e Y."""
        client, app = async_client
        chart_id = uuid.uuid4()

        mock_chart = _make_mock_chart(chart_id)
        mock_service = AsyncMock()
        mock_service.update_metadata.return_value = (
            mock_chart,
            ["xaxis_title", "yaxis_title"],
        )

        from api.dependencies import get_chart_service
        app.dependency_overrides[get_chart_service] = lambda: mock_service

        response = await client.patch(
            f"/api/v1/charts/{chart_id}/metadata",
            json={"xaxis_title": "New X", "yaxis_title": "New Y"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "xaxis_title" in data["updated_fields"]
        assert "yaxis_title" in data["updated_fields"]

    @pytest.mark.asyncio
    async def test_update_metadata_all_fields(self, async_client):
        """Actualizar título, ejes y extra_layout juntos."""
        client, app = async_client
        chart_id = uuid.uuid4()

        mock_chart = _make_mock_chart(chart_id)
        all_fields = ["title", "xaxis_title", "yaxis_title", "template"]
        mock_service = AsyncMock()
        mock_service.update_metadata.return_value = (mock_chart, all_fields)

        from api.dependencies import get_chart_service
        app.dependency_overrides[get_chart_service] = lambda: mock_service

        response = await client.patch(
            f"/api/v1/charts/{chart_id}/metadata",
            json={
                "title": "Full Update",
                "xaxis_title": "X Axis",
                "yaxis_title": "Y Axis",
                "extra_layout": {"template": "plotly_dark"},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["updated_fields"]) == 4

    @pytest.mark.asyncio
    async def test_update_metadata_not_found(self, async_client):
        """404 si el chart_id no existe."""
        client, app = async_client
        chart_id = uuid.uuid4()

        mock_service = AsyncMock()
        mock_service.update_metadata.side_effect = ValueError(
            f"Result {chart_id} not found"
        )

        from api.dependencies import get_chart_service
        app.dependency_overrides[get_chart_service] = lambda: mock_service

        response = await client.patch(
            f"/api/v1/charts/{chart_id}/metadata",
            json={"title": "Test"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_metadata_empty_body(self, async_client):
        """422 si no se envía ningún campo."""
        client, app = async_client
        chart_id = uuid.uuid4()

        response = await client.patch(
            f"/api/v1/charts/{chart_id}/metadata",
            json={},
        )

        assert response.status_code == 422


# ===========================================================================
# TFG-57: Regenerate Chart Tests
# ===========================================================================


class TestRegenerateChart:
    """Tests para POST /api/v1/charts/{chart_id}/regenerate."""

    @pytest.mark.asyncio
    async def test_regenerate_chart_success(self, async_client):
        """Happy path: regenerar gráfico con un prompt."""
        client, app = async_client
        chart_id = uuid.uuid4()

        # Mock del chart existente
        mock_chart = _make_mock_chart(chart_id)
        # Mock del chart_service
        mock_chart_service = AsyncMock()
        mock_chart_service.get_chart_by_id.return_value = mock_chart

        modified_viz_json = {
            **SAMPLE_VIZ_JSON,
            "layout": {**SAMPLE_VIZ_JSON["layout"], "template": "plotly_dark"},
        }
        mock_updated = _make_mock_chart(chart_id, modified_viz_json)
        mock_updated.chart_type = "bar"
        mock_chart_service.update_viz_json.return_value = mock_updated

        # Mock del VizAgent
        mock_viz_output = MagicMock()
        mock_viz_output.success = True
        mock_viz_output.plotly_json = modified_viz_json
        mock_viz_output.plotly_code = "import plotly.express as px; fig = px.bar(...) # modified"
        mock_viz_output.chart_type = "bar"

        mock_viz_agent = MagicMock()
        mock_viz_agent.modify_chart = AsyncMock(return_value=mock_viz_output)

        # Mock del VannaAgent para re-ejecutar el SQL
        import pandas as pd
        mock_df = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
        mock_vanna_agent = MagicMock()
        mock_vanna_agent.execute_sql = AsyncMock(return_value=mock_df)

        mock_pipeline = MagicMock()
        mock_pipeline.decision_agent.viz_agent = mock_viz_agent
        mock_pipeline.decision_agent.text2sql_agent = mock_vanna_agent

        from api.dependencies import get_chart_service, get_pipeline_service
        app.dependency_overrides[get_chart_service] = lambda: mock_chart_service
        app.dependency_overrides[get_pipeline_service] = lambda: mock_pipeline

        response = await client.post(
            f"/api/v1/charts/{chart_id}/regenerate",
            json={"prompt": "Cambiá el color a azul"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["chart_id"] == str(chart_id)
        assert data["plotly_json"] is not None
        assert data["chart_type"] == "bar"

        # Verificar que se llamó a modify_chart con los args correctos
        # (ahora asíncrono)
        mock_viz_agent.modify_chart.assert_called_once_with(
            plotly_code=mock_chart.plotly_code,
            dataframe=mock_df,
            user_prompt="Cambiá el color a azul",
            conversation_history=[],
        )

    @pytest.mark.asyncio
    async def test_regenerate_chart_not_found(self, async_client):
        """404 si el chart_id no existe."""
        client, app = async_client
        chart_id = uuid.uuid4()

        mock_chart_service = AsyncMock()
        mock_chart_service.get_chart_by_id.return_value = None

        from api.dependencies import get_chart_service, get_pipeline_service
        app.dependency_overrides[get_chart_service] = lambda: mock_chart_service
        app.dependency_overrides[get_pipeline_service] = lambda: MagicMock()

        response = await client.post(
            f"/api/v1/charts/{chart_id}/regenerate",
            json={"prompt": "Test prompt"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_regenerate_chart_agent_failure(self, async_client):
        """500 si el VizAgent falla al modificar."""
        client, app = async_client
        chart_id = uuid.uuid4()

        mock_chart = _make_mock_chart(chart_id)

        mock_chart_service = AsyncMock()
        mock_chart_service.get_chart_by_id.return_value = mock_chart

        mock_viz_output = MagicMock()
        mock_viz_output.success = False
        mock_viz_output.error_message = "Gemini API timeout"

        mock_viz_agent = MagicMock()
        mock_viz_agent.modify_chart = AsyncMock(return_value=mock_viz_output)

        import pandas as pd
        mock_vanna_agent = MagicMock()
        mock_vanna_agent.execute_sql = AsyncMock(return_value=pd.DataFrame({"x": [1], "y": [2]}))

        mock_pipeline = MagicMock()
        mock_pipeline.decision_agent.viz_agent = mock_viz_agent
        mock_pipeline.decision_agent.text2sql_agent = mock_vanna_agent

        from api.dependencies import get_chart_service, get_pipeline_service
        app.dependency_overrides[get_chart_service] = lambda: mock_chart_service
        app.dependency_overrides[get_pipeline_service] = lambda: mock_pipeline

        response = await client.post(
            f"/api/v1/charts/{chart_id}/regenerate",
            json={"prompt": "Cambiar colores"},
        )

        assert response.status_code == 500


    @pytest.mark.asyncio
    async def test_regenerate_chart_no_plotly_code(self, async_client):
        """422 si el chartado no tiene plotly_code (no se puede regenerar)."""
        client, app = async_client
        chart_id = uuid.uuid4()

        mock_chart = _make_mock_chart(chart_id)
        mock_chart.plotly_code = None  # Sin código

        mock_chart_service = AsyncMock()
        mock_chart_service.get_chart_by_id.return_value = mock_chart

        from api.dependencies import get_chart_service, get_pipeline_service
        app.dependency_overrides[get_chart_service] = lambda: mock_chart_service
        app.dependency_overrides[get_pipeline_service] = lambda: MagicMock()

        response = await client.post(
            f"/api/v1/charts/{chart_id}/regenerate",
            json={"prompt": "Cambiar colores"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_regenerate_chart_empty_prompt(self, async_client):
        """422 si el prompt está vacío."""
        client, app = async_client
        chart_id = uuid.uuid4()

        response = await client.post(
            f"/api/v1/charts/{chart_id}/regenerate",
            json={"prompt": ""},
        )

        assert response.status_code == 422
