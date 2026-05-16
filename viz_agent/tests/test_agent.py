# tests/test_agent.py

import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from viz_agent.agent import VizAgent
from viz_agent.config import Config
from viz_agent.models import (
    VizAgentInput,
    VizAgentOutput,
    DataFrameMetadata,
    GeminiResponse,
    ValidationResult
)
import plotly.express as px


@pytest.fixture
def mock_config():
    """Settings mockeado"""
    return Settings(
        gemini_api_key="test_key",
        log_dir="test_logs",
        max_correction_attempts=3
    )


@pytest.fixture
def sample_dataframe():
    """DataFrame de ejemplo"""
    return pd.DataFrame({
        'category': ['A', 'B', 'C'],
        'value': [10, 20, 30]
    })


@pytest.fixture
def mock_agent_dependencies():
    """Mock de todas las dependencias del agent"""
    with patch('viz_agent.agent.DataFrameAnalyzer') as mock_analyzer, \
         patch('viz_agent.agent.GeminiClient') as mock_gemini, \
         patch('viz_agent.agent.CodeValidator') as mock_validator, \
         patch('viz_agent.agent.VizAgentLogger') as mock_logger:
        
        yield {
            'analyzer': mock_analyzer,
            'gemini': mock_gemini,
            'validator': mock_validator,
            'logger': mock_logger
        }


def test_agent_initialization(mock_config, mock_agent_dependencies):
    """Test inicialización del agente"""
    agent = VizAgent(mock_config)
    
    assert agent.config == mock_config
    assert agent.max_correction_attempts == 3


@pytest.mark.asyncio
async def test_generate_visualization_invalid_dataframe(mock_config, mock_agent_dependencies):
    """Test con DataFrame inválido"""
    agent = VizAgent(mock_config)
    
    # Mock analyzer retorna DataFrame inválido
    mock_analyzer_instance = mock_agent_dependencies['analyzer'].return_value
    mock_analyzer_instance.validate_dataframe.return_value = (False, "DataFrame is empty")
    
    empty_df = pd.DataFrame()
    input_data = VizAgentInput(
        dataframe=empty_df,
        user_request="gráfico"
    )
    
    result = await agent.generate_visualization(input_data)
    
    assert not result.success
    assert "empty" in result.error_message.lower()


@pytest.mark.asyncio
async def test_generate_visualization_success_first_attempt(mock_config, mock_agent_dependencies, sample_dataframe):
    """Test generación exitosa en primer intento"""
    agent = VizAgent(mock_config)
    
    # Mock analyzer
    mock_analyzer_instance = mock_agent_dependencies['analyzer'].return_value
    mock_analyzer_instance.validate_dataframe.return_value = (True, None)
    mock_analyzer_instance.analyze.return_value = DataFrameMetadata(
        shape=(3, 2),
        columns=["category", "value"],
        dtypes={"category": "object", "value": "int64"},
        numeric_columns=["value"],
        categorical_columns=["category"],
        datetime_columns=[],
        null_counts={"category": 0, "value": 0},
        sample_values={"category": ["A", "B", "C"], "value": [10, 20, 30]},
        unique_counts={"category": 3, "value": 3}
    )
    
    # Mock Gemini
    mock_gemini_instance = mock_agent_dependencies['gemini'].return_value
    from unittest.mock import AsyncMock
    mock_gemini_instance.decide_and_generate_code = AsyncMock(return_value=GeminiResponse(
        chart_type="bar",
        reasoning="Bar chart for categories",
        plotly_code="import plotly.express as px\nfig = px.bar(df, x='category', y='value')",
        customizations={}
    ))
    
    # Mock validator (éxito)
    mock_validator_instance = mock_agent_dependencies['validator'].return_value
    mock_fig = px.bar(sample_dataframe, x='category', y='value')
    mock_validator_instance.execute_and_validate.return_value = ValidationResult(
        success=True,
        figure=mock_fig
    )
    
    input_data = VizAgentInput(
        dataframe=sample_dataframe,
        user_request="gráfico de barras"
    )
    
    result = await agent.generate_visualization(input_data)
    
    assert result.success
    assert result.chart_type == "bar"
    assert result.plotly_code is not None
    assert result.plotly_json is not None
    assert result.metadata["attempts"] == 1


@pytest.mark.asyncio
async def test_generate_visualization_with_correction(mock_config, mock_agent_dependencies, sample_dataframe):
    """Test generación con corrección (segundo intento)"""
    agent = VizAgent(mock_config)
    
    # Mock analyzer
    mock_analyzer_instance = mock_agent_dependencies['analyzer'].return_value
    mock_analyzer_instance.validate_dataframe.return_value = (True, None)
    mock_analyzer_instance.analyze.return_value = DataFrameMetadata(
        shape=(3, 2),
        columns=["category", "value"],
        dtypes={"category": "object", "value": "int64"},
        numeric_columns=["value"],
        categorical_columns=["category"],
        datetime_columns=[],
        null_counts={"category": 0, "value": 0},
        sample_values={"category": ["A", "B", "C"], "value": [10, 20, 30]},
        unique_counts={"category": 3, "value": 3}
    )
    
    # Mock Gemini
    mock_gemini_instance = mock_agent_dependencies['gemini'].return_value
    from unittest.mock import AsyncMock
    mock_gemini_instance.decide_and_generate_code = AsyncMock(return_value=GeminiResponse(
        chart_type="bar",
        reasoning="Bar chart",
        plotly_code="bad_code",
        customizations={}
    ))
    mock_gemini_instance.request_correction = AsyncMock(return_value="import plotly.express as px\nfig = px.bar(df, x='category', y='value')")
    
    # Mock validator (primero falla, luego éxito)
    mock_validator_instance = mock_agent_dependencies['validator'].return_value
    mock_validator_instance.execute_and_validate.side_effect = [
        ValidationResult(success=False, error_type="syntax", error_message="Syntax error"),
        ValidationResult(success=True, figure=px.bar(sample_dataframe, x='category', y='value'))
    ]
    
    input_data = VizAgentInput(
        dataframe=sample_dataframe,
        user_request="gráfico de barras"
    )
    
    result = await agent.generate_visualization(input_data)
    
    assert result.success
    assert result.metadata["attempts"] == 2
    assert len(result.metadata["corrections_made"]) == 1


@pytest.mark.asyncio
async def test_generate_visualization_max_attempts_exceeded(mock_config, mock_agent_dependencies, sample_dataframe):
    """Test cuando se exceden los intentos máximos"""
    agent = VizAgent(mock_config)
    
    # Mock analyzer
    mock_analyzer_instance = mock_agent_dependencies['analyzer'].return_value
    mock_analyzer_instance.validate_dataframe.return_value = (True, None)
    mock_analyzer_instance.analyze.return_value = DataFrameMetadata(
        shape=(3, 2),
        columns=["category", "value"],
        dtypes={"category": "object", "value": "int64"},
        numeric_columns=["value"],
        categorical_columns=["category"],
        datetime_columns=[],
        null_counts={"category": 0, "value": 0},
        sample_values={"category": ["A", "B", "C"], "value": [10, 20, 30]},
        unique_counts={"category": 3, "value": 3}
    )
    
    # Mock Gemini
    mock_gemini_instance = mock_agent_dependencies['gemini'].return_value
    from unittest.mock import AsyncMock
    mock_gemini_instance.decide_and_generate_code = AsyncMock(return_value=GeminiResponse(
        chart_type="bar",
        reasoning="Bar chart",
        plotly_code="bad_code",
        customizations={}
    ))
    mock_gemini_instance.request_correction = AsyncMock(return_value="still_bad_code")
    
    # Mock validator (siempre falla)
    mock_validator_instance = mock_agent_dependencies['validator'].return_value
    mock_validator_instance.execute_and_validate.return_value = ValidationResult(
        success=False,
        error_type="runtime",
        error_message="Always fails"
    )
    
    input_data = VizAgentInput(
        dataframe=sample_dataframe,
        user_request="gráfico de barras"
    )
    
    result = await agent.generate_visualization(input_data)
    
    assert not result.success
    assert "Failed to generate valid code after 3 attempts" in result.error_message
    assert result.metadata["attempts"] == 3


@pytest.mark.asyncio
async def test_generate_visualization_unexpected_error(mock_config, mock_agent_dependencies, sample_dataframe):
    """Test manejo de error inesperado"""
    agent = VizAgent(mock_config)
    
    # Mock analyzer lanza excepción
    mock_analyzer_instance = mock_agent_dependencies['analyzer'].return_value
    mock_analyzer_instance.validate_dataframe.side_effect = Exception("Unexpected error")
    
    input_data = VizAgentInput(
        dataframe=sample_dataframe,
        user_request="gráfico"
    )
    
    result = await agent.generate_visualization(input_data)
    
    assert not result.success
    assert "Unexpected error" in result.error_message
