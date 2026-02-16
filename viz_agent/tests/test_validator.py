# tests/test_validator.py

import pytest
import pandas as pd
from viz_agent.validator import CodeValidator


def test_valid_code_execution(simple_numeric_df):
    """Test ejecución de código válido"""
    code = """
import plotly.express as px
fig = px.bar(df, x='a', y='b')
"""
    validator = CodeValidator()
    result = validator.execute_and_validate(code, simple_numeric_df)
    
    assert result.success
    assert result.figure is not None
    assert result.error_type is None
    assert result.error_message is None


def test_syntax_error_detection():
    """Test detección de error de sintaxis"""
    code = "fig = px.bar(df, x='a', y='b'"  # Missing closing parenthesis
    df = pd.DataFrame({'a': ['A'], 'b': [1]})
    validator = CodeValidator()
    result = validator.execute_and_validate(code, df)
    
    assert not result.success
    assert result.error_type == "syntax"
    assert result.figure is None
    assert result.traceback is not None


def test_runtime_error_detection():
    """Test detección de error de runtime"""
    code = """
import plotly.express as px
fig = px.bar(df, x='nonexistent_column', y='b')
"""
    df = pd.DataFrame({'a': ['A'], 'b': [1]})
    validator = CodeValidator()
    result = validator.execute_and_validate(code, df)
    
    assert not result.success
    assert result.error_type == "runtime"
    assert result.figure is None


def test_empty_figure_detection():
    """Test detección de figura vacía"""
    code = """
import plotly.graph_objects as go
fig = go.Figure()  # Empty figure
"""
    df = pd.DataFrame({'a': ['A'], 'b': [1]})
    validator = CodeValidator()
    result = validator.execute_and_validate(code, df)
    
    assert not result.success
    assert result.error_type == "empty"


def test_missing_figure_variable():
    """Test cuando no se crea variable 'fig'"""
    code = """
import plotly.express as px
chart = px.bar(df, x='a', y='b')  # Wrong variable name
"""
    df = pd.DataFrame({'a': ['A'], 'b': [1]})
    validator = CodeValidator()
    result = validator.execute_and_validate(code, df)
    
    # Debería encontrar 'chart' como fallback
    assert result.success or result.error_type == "runtime"


def test_figure_with_go():
    """Test ejecución con plotly.graph_objects"""
    code = """
import plotly.graph_objects as go
fig = go.Figure(data=[go.Bar(x=['A', 'B'], y=[1, 2])])
"""
    df = pd.DataFrame({'a': ['A'], 'b': [1]})
    validator = CodeValidator()
    result = validator.execute_and_validate(code, df)
    
    assert result.success
    assert result.figure is not None


def test_figure_with_dataframe(simple_numeric_df):
    """Test usando DataFrame real"""
    code = """
import plotly.express as px
fig = px.line(df, x='a', y='b')
"""
    validator = CodeValidator()
    result = validator.execute_and_validate(code, simple_numeric_df)
    
    assert result.success
    assert result.figure is not None


def test_code_with_null_handling(dataframe_with_nulls):
    """Test código que maneja nulls"""
    code = """
import plotly.express as px
df_clean = df.dropna()
fig = px.scatter(df_clean, x='x', y='y')
"""
    validator = CodeValidator()
    result = validator.execute_and_validate(code, dataframe_with_nulls)
    
    assert result.success
    assert result.figure is not None


def test_multiple_operations(mixed_dataframe):
    """Test código con múltiples operaciones"""
    code = """
import plotly.express as px
df_agg = df.groupby('category')['numeric'].sum().reset_index()
fig = px.bar(df_agg, x='category', y='numeric')
"""
    validator = CodeValidator()
    result = validator.execute_and_validate(code, mixed_dataframe)
    
    assert result.success
    assert result.figure is not None


def test_stdout_stderr_capture():
    """Test que stdout/stderr se capturan correctamente"""
    code = """
import plotly.express as px
print("This should not appear")
fig = px.bar(df, x='a', y='b')
"""
    df = pd.DataFrame({'a': ['A'], 'b': [1]})
    validator = CodeValidator()
    result = validator.execute_and_validate(code, df)
    
    # El código debería ejecutarse sin que el print cause problemas
    assert result.success


def test_figure_without_data_attribute():
    """Test figura sin atributo 'data'"""
    code = """
class FakeFig:
    pass

fig = FakeFig()
"""
    df = pd.DataFrame({'a': [1], 'b': [2]})
    validator = CodeValidator()
    result = validator.execute_and_validate(code, df)
    
    # No debería encontrar una figura válida
    assert not result.success


def test_figure_with_pie_chart():
    """Test con gráfico de torta (usa 'values')"""
    code = """
import plotly.express as px
fig = px.pie(df, names='a', values='b')
"""
    df = pd.DataFrame({'a': ['X', 'Y'], 'b': [10, 20]})
    validator = CodeValidator()
    result = validator.execute_and_validate(code, df)
    
    assert result.success
    assert result.figure is not None


def test_extract_figure_fallback():
    """Test extracción de figura cuando no se llama 'fig'"""
    code = """
import plotly.express as px
my_chart = px.bar(df, x='a', y='b')
"""
    df = pd.DataFrame({'a': ['A'], 'b': [1]})
    validator = CodeValidator()
    result = validator.execute_and_validate(code, df)
    
    # Debería encontrar la figura con el fallback
    assert result.success
    assert result.figure is not None


def test_figure_with_empty_traces():
    """Test figura con traces pero sin datos"""
    code = """
import plotly.graph_objects as go
fig = go.Figure()
fig.add_trace(go.Bar(x=[], y=[]))
"""
    df = pd.DataFrame({'a': [1], 'b': [2]})
    validator = CodeValidator()
    result = validator.execute_and_validate(code, df)
    
    assert not result.success
    assert result.error_type == "empty"
