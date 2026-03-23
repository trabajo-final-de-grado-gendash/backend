# tests/conftest.py

import pytest
import pandas as pd
import os
from pathlib import Path


@pytest.fixture
def simple_numeric_df():
    """DataFrame simple con columnas numéricas"""
    return pd.DataFrame({
        'a': [1, 2, 3, 4, 5],
        'b': [10, 20, 30, 40, 50]
    })


@pytest.fixture
def mixed_dataframe():
    """DataFrame con tipos mixtos"""
    return pd.DataFrame({
        'numeric': [1, 2, 3, 4, 5],
        'category': ['A', 'B', 'C', 'A', 'B'],
        'date': pd.date_range('2024-01-01', periods=5)
    })


@pytest.fixture
def empty_dataframe():
    """DataFrame vacío"""
    return pd.DataFrame()


@pytest.fixture
def dataframe_with_nulls():
    """DataFrame con valores nulos"""
    return pd.DataFrame({
        'x': [1, 2, None, 4, 5],
        'y': [10, None, 30, None, 50],
        'z': ['A', 'B', 'C', 'D', 'E']
    })


@pytest.fixture
def high_cardinality_df():
    """DataFrame con columna de alta cardinalidad (IDs)"""
    return pd.DataFrame({
        'id': range(1000),
        'value': [i * 2 for i in range(1000)],
        'category': ['A', 'B', 'C'] * 333 + ['A']
    })
