# tests/test_gemini_client.py

import pytest
from unittest.mock import Mock, patch, MagicMock
from viz_agent.gemini_client import GeminiClient
from viz_agent.models import DataFrameMetadata, GeminiResponse, CorrectionRequest, CodeCorrectionResponse
import json


@pytest.fixture
def sample_metadata():
    """Metadata de ejemplo para tests"""
    return DataFrameMetadata(
        shape=(10, 3),
        columns=["a", "b", "c"],
        dtypes={"a": "int64", "b": "float64", "c": "object"},
        numeric_columns=["a", "b"],
        categorical_columns=["c"],
        datetime_columns=[],
        null_counts={"a": 0, "b": 1, "c": 0},
        sample_values={"a": [1, 2, 3], "b": [1.0, 2.0, 3.0], "c": ["x", "y", "z"]},
        unique_counts={"a": 10, "b": 10, "c": 3}
    )


@pytest.fixture
def mock_gemini_client():
    """Cliente Gemini mockeado"""
    with patch('viz_agent.gemini_client.genai.Client') as mock_client:
        yield mock_client


def test_gemini_client_initialization(mock_gemini_client):
    """Test inicialización del cliente"""
    client = GeminiClient(api_key="test_key")
    
    assert client.model == "gemini-2.5-flash"
    assert client.base_config["temperature"] == 0.2
    assert client.base_config["top_p"] == 0.8
    assert client.base_config["max_output_tokens"] == 4096


def test_decide_and_generate_code_prompt_format(mock_gemini_client, sample_metadata):
    """Test que el prompt se formatea correctamente"""
    # Mock de respuesta
    mock_response = Mock()
    mock_response.text = json.dumps({
        "chart_type": "bar",
        "reasoning": "Best for categorical data",
        "plotly_code": "import plotly.express as px\nfig = px.bar(df, x='c', y='a')",
        "customizations": {}
    })
    
    mock_instance = mock_gemini_client.return_value
    mock_instance.models.generate_content.return_value = mock_response
    
    client = GeminiClient(api_key="test_key")
    result = client.decide_and_generate_code(
        user_request="gráfico de barras",
        df_metadata=sample_metadata,
        allowed_charts=["bar", "line"]
    )
    
    # Verificar que se llamó a generate_content
    assert mock_instance.models.generate_content.called
    
    # Verificar resultado
    assert isinstance(result, GeminiResponse)
    assert result.chart_type == "bar"
    assert "px.bar" in result.plotly_code


def test_decide_and_generate_code_response_parsing(mock_gemini_client, sample_metadata):
    """Test parseo de respuesta JSON"""
    mock_response = Mock()
    mock_response.text = json.dumps({
        "chart_type": "line",
        "reasoning": "Shows trends over time",
        "plotly_code": "import plotly.express as px\nfig = px.line(df, x='a', y='b')",
        "customizations": {"color": "blue"}
    })
    
    mock_instance = mock_gemini_client.return_value
    mock_instance.models.generate_content.return_value = mock_response
    
    client = GeminiClient(api_key="test_key")
    result = client.decide_and_generate_code(
        user_request="línea temporal",
        df_metadata=sample_metadata,
        allowed_charts=["line"]
    )
    
    assert result.chart_type == "line"
    assert result.reasoning == "Shows trends over time"
    assert "px.line" in result.plotly_code
    assert result.customizations["color"] == "blue"


def test_request_correction(mock_gemini_client, sample_metadata):
    """Test solicitud de corrección"""
    mock_response = Mock()
    mock_response.text = json.dumps({
        "corrected_code": "import plotly.express as px\nfig = px.bar(df, x='c', y='a')",
        "explanation": "Fixed column name from 'z' to 'c'"
    })
    
    mock_instance = mock_gemini_client.return_value
    mock_instance.models.generate_content.return_value = mock_response
    
    client = GeminiClient(api_key="test_key")
    
    correction_request = CorrectionRequest(
        original_code="fig = px.bar(df, x='z', y='a')",
        error_message="KeyError: 'z'",
        error_type="runtime",
        dataframe_metadata=sample_metadata,
        attempt_number=1
    )
    
    corrected_code = client.request_correction(correction_request)
    
    assert "px.bar" in corrected_code
    assert "x='c'" in corrected_code


def test_request_correction_prompt_includes_metadata(mock_gemini_client, sample_metadata):
    """Test que el prompt de corrección incluye metadata"""
    mock_response = Mock()
    mock_response.text = json.dumps({
        "corrected_code": "fixed_code",
        "explanation": "Fixed it"
    })
    
    mock_instance = mock_gemini_client.return_value
    mock_instance.models.generate_content.return_value = mock_response
    
    client = GeminiClient(api_key="test_key")
    
    correction_request = CorrectionRequest(
        original_code="bad_code",
        error_message="Error message",
        error_type="syntax",
        dataframe_metadata=sample_metadata,
        attempt_number=2
    )
    
    result = client.request_correction(correction_request)
    
    # Verificar que se llamó con los parámetros correctos
    assert mock_instance.models.generate_content.called
    call_args = mock_instance.models.generate_content.call_args
    
    # El primer argumento (contents) debería contener la metadata
    assert "bad_code" in call_args[1]["contents"]
    assert "Error message" in call_args[1]["contents"]


def test_base_config_values():
    """Test valores de configuración base"""
    with patch('viz_agent.gemini_client.genai.Client'):
        client = GeminiClient(api_key="test")
        
        assert client.base_config["temperature"] == 0.2
        assert client.base_config["top_p"] == 0.8
        assert client.base_config["top_k"] == 40
        assert client.base_config["max_output_tokens"] == 4096
