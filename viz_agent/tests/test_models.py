# tests/test_models.py

import pytest
import pandas as pd
from viz_agent.models import (
    VizAgentInput,
    VizAgentOutput,
    DataFrameMetadata,
    ValidationResult,
    GeminiResponse,
    CorrectionRequest,
    CodeCorrectionResponse,
)


def test_viz_agent_input_creation():
    """Test creación de VizAgentInput"""
    df = pd.DataFrame({'a': [1, 2, 3]})
    input_data = VizAgentInput(
        dataframe=df,
        user_request="gráfico de barras"
    )
    
    assert input_data.dataframe.equals(df)
    assert input_data.user_request == "gráfico de barras"
    assert "bar" in input_data.allowed_charts


def test_viz_agent_input_custom_allowed_charts():
    """Test VizAgentInput con allowed_charts custom"""
    df = pd.DataFrame({'a': [1, 2, 3]})
    input_data = VizAgentInput(
        dataframe=df,
        user_request="gráfico",
        allowed_charts=["bar", "line"]
    )
    
    assert len(input_data.allowed_charts) == 2
    assert "pie" not in input_data.allowed_charts


def test_dataframe_metadata_creation():
    """Test creación de DataFrameMetadata"""
    metadata = DataFrameMetadata(
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
    
    assert metadata.shape == (10, 3)
    assert len(metadata.columns) == 3
    assert len(metadata.numeric_columns) == 2


def test_viz_agent_output_success():
    """Test VizAgentOutput exitoso"""
    output = VizAgentOutput(
        success=True,
        plotly_code="fig = px.bar(df, x='a', y='b')",
        plotly_json='{"data": []}',
        chart_type="bar",
        metadata={"attempts": 1, "execution_time": 1.5}
    )
    
    assert output.success
    assert output.chart_type == "bar"
    assert output.error_message is None
    assert output.metadata["attempts"] == 1


def test_viz_agent_output_failure():
    """Test VizAgentOutput con error"""
    output = VizAgentOutput(
        success=False,
        error_message="DataFrame is empty",
        metadata={"attempts": 0}
    )
    
    assert not output.success
    assert output.plotly_code is None
    assert "empty" in output.error_message.lower()


def test_validation_result_success():
    """Test ValidationResult exitoso"""
    result = ValidationResult(
        success=True,
        figure={"data": []},  # Mock figure
        error_type=None,
        error_message=None
    )
    
    assert result.success
    assert result.figure is not None
    assert result.error_type is None


def test_validation_result_syntax_error():
    """Test ValidationResult con error de sintaxis"""
    result = ValidationResult(
        success=False,
        error_type="syntax",
        error_message="SyntaxError: invalid syntax",
        traceback="Traceback..."
    )
    
    assert not result.success
    assert result.error_type == "syntax"
    assert result.figure is None


def test_gemini_response_creation():
    """Test creación de GeminiResponse"""
    response = GeminiResponse(
        chart_type="bar",
        reasoning="Bar chart is best for categorical comparison",
        plotly_code="fig = px.bar(df, x='category', y='value')",
        customizations={"color": "blue", "title": "My Chart"}
    )
    
    assert response.chart_type == "bar"
    assert "comparison" in response.reasoning.lower()
    assert "px.bar" in response.plotly_code
    assert response.customizations["color"] == "blue"


def test_correction_request_creation():
    """Test creación de CorrectionRequest"""
    metadata = DataFrameMetadata(
        shape=(5, 2),
        columns=["x", "y"],
        dtypes={"x": "int64", "y": "int64"},
        numeric_columns=["x", "y"],
        categorical_columns=[],
        datetime_columns=[],
        null_counts={"x": 0, "y": 0},
        sample_values={"x": [1, 2, 3], "y": [4, 5, 6]},
        unique_counts={"x": 5, "y": 5}
    )
    
    request = CorrectionRequest(
        original_code="fig = px.bar(df, x='z', y='y')",
        error_message="KeyError: 'z'",
        error_type="runtime",
        dataframe_metadata=metadata,
        attempt_number=1
    )
    
    assert request.error_type == "runtime"
    assert request.attempt_number == 1
    assert "z" in request.original_code


def test_code_correction_response_creation():
    """Test creación de CodeCorrectionResponse"""
    response = CodeCorrectionResponse(
        corrected_code="fig = px.bar(df, x='x', y='y')",
        explanation="Fixed column name from 'z' to 'x'"
    )
    
    assert "x='x'" in response.corrected_code
    assert "Fixed" in response.explanation
