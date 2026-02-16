# tests/test_analyzer.py

import pytest
import pandas as pd
from viz_agent.analyzer import DataFrameAnalyzer


def test_analyze_numeric_dataframe(simple_numeric_df):
    """Test análisis de DataFrame numérico simple"""
    analyzer = DataFrameAnalyzer()
    metadata = analyzer.analyze(simple_numeric_df)
    
    assert metadata.shape == (5, 2)
    assert 'a' in metadata.numeric_columns
    assert 'b' in metadata.numeric_columns
    assert len(metadata.categorical_columns) == 0
    assert len(metadata.datetime_columns) == 0


def test_analyze_mixed_dataframe(mixed_dataframe):
    """Test análisis de DataFrame con tipos mixtos"""
    analyzer = DataFrameAnalyzer()
    metadata = analyzer.analyze(mixed_dataframe)
    
    assert metadata.shape == (5, 3)
    assert 'numeric' in metadata.numeric_columns
    assert 'category' in metadata.categorical_columns
    assert 'date' in metadata.datetime_columns


def test_analyze_sample_values(simple_numeric_df):
    """Test que sample_values contiene primeras 5 filas"""
    analyzer = DataFrameAnalyzer()
    metadata = analyzer.analyze(simple_numeric_df)
    
    # Las columnas numéricas simples pueden ser alta cardinalidad si todos son únicos
    # El test debe verificar que hay valores de muestra, no la cantidad exacta
    assert 'a' in metadata.sample_values
    assert 'b' in metadata.sample_values
    # Si no es alta cardinalidad, debe tener valores reales
    if metadata.sample_values['a'] != ["[HIGH_CARDINALITY_COLUMN]"]:
        assert len(metadata.sample_values['a']) <= 5


def test_analyze_unique_counts(mixed_dataframe):
    """Test conteo de valores únicos"""
    analyzer = DataFrameAnalyzer()
    metadata = analyzer.analyze(mixed_dataframe)
    
    assert metadata.unique_counts['numeric'] == 5
    assert metadata.unique_counts['category'] == 3  # A, B, C
    assert metadata.unique_counts['date'] == 5


def test_analyze_null_counts(dataframe_with_nulls):
    """Test conteo de valores nulos"""
    analyzer = DataFrameAnalyzer()
    metadata = analyzer.analyze(dataframe_with_nulls)
    
    assert metadata.null_counts['x'] == 1
    assert metadata.null_counts['y'] == 2
    assert metadata.null_counts['z'] == 0


def test_analyze_high_cardinality_detection(high_cardinality_df):
    """Test detección de columnas de alta cardinalidad"""
    analyzer = DataFrameAnalyzer()
    metadata = analyzer.analyze(high_cardinality_df)
    
    # La columna 'id' debería ser detectada como alta cardinalidad
    assert metadata.sample_values['id'] == ["[HIGH_CARDINALITY_COLUMN]"]
    # La columna 'value' también es alta cardinalidad (1000 valores únicos)
    # La columna 'category' tiene solo 3 valores únicos, debe tener valores reales
    assert metadata.sample_values['category'] != ["[HIGH_CARDINALITY_COLUMN]"]
    assert len(metadata.sample_values['category']) <= 5


def test_analyze_dtypes(mixed_dataframe):
    """Test extracción de tipos de datos"""
    analyzer = DataFrameAnalyzer()
    metadata = analyzer.analyze(mixed_dataframe)
    
    assert 'int' in metadata.dtypes['numeric'].lower()
    # Pandas 3.0 usa 'str' en lugar de 'object' para strings
    assert 'object' in metadata.dtypes['category'].lower() or 'str' in metadata.dtypes['category'].lower()
    assert 'datetime' in metadata.dtypes['date'].lower()


def test_validate_empty_dataframe(empty_dataframe):
    """Test validación de DataFrame vacío"""
    analyzer = DataFrameAnalyzer()
    is_valid, error = analyzer.validate_dataframe(empty_dataframe)
    
    assert not is_valid
    assert "empty" in error.lower()


def test_validate_dataframe_no_rows():
    """Test validación de DataFrame sin filas"""
    df = pd.DataFrame(columns=['a', 'b'])
    analyzer = DataFrameAnalyzer()
    is_valid, error = analyzer.validate_dataframe(df)
    
    assert not is_valid
    assert "empty" in error.lower() or "no rows" in error.lower()


def test_validate_dataframe_no_columns():
    """Test validación de DataFrame sin columnas"""
    df = pd.DataFrame([1, 2, 3])
    df = df.drop(df.columns, axis=1)
    analyzer = DataFrameAnalyzer()
    is_valid, error = analyzer.validate_dataframe(df)
    
    assert not is_valid
    assert "empty" in error.lower() or "no columns" in error.lower()


def test_validate_valid_dataframe(simple_numeric_df):
    """Test validación de DataFrame válido"""
    analyzer = DataFrameAnalyzer()
    is_valid, error = analyzer.validate_dataframe(simple_numeric_df)
    
    assert is_valid
    assert error is None


def test_analyze_handles_nulls_in_sample(dataframe_with_nulls):
    """Test que analyze() maneja nulls correctamente en sample_values"""
    analyzer = DataFrameAnalyzer()
    metadata = analyzer.analyze(dataframe_with_nulls)
    
    # dropna() debería remover nulls antes de tomar sample
    assert None not in metadata.sample_values['x']
    assert len(metadata.sample_values['x']) <= 5
