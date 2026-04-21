# viz_agent/analyzer.py

import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from .models import DataFrameMetadata


class DataFrameAnalyzer:
    """Analiza DataFrames y extrae metadata"""
    
    def analyze(self, df: pd.DataFrame) -> DataFrameMetadata:
        """Analiza el DataFrame y retorna metadata estructurada"""
        
        # 1. Identificar tipos de columnas
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'category', 'string']).columns.tolist()
        datetime_cols = df.select_dtypes(include=['datetime64']).columns.tolist()
        
        # 2. Calcular valores únicos (para identificar categorías vs. IDs)
        unique_counts = {col: df[col].nunique() for col in df.columns}
        
        # 3. Detectar columnas de alta cardinalidad (probablemente IDs, no útiles para viz)
        high_cardinality_threshold = len(df) * 0.9
        potential_id_columns = [
            col for col, count in unique_counts.items() 
            if count > high_cardinality_threshold
        ]
        
        # 4. Muestrear valores para dar contexto a Gemini
        sample_values = {}
        unique_values = {}
        for col in df.columns:
            if col in potential_id_columns:
                sample_values[col] = ["[HIGH_CARDINALITY_COLUMN]"]
            else:
                sample_values[col] = df[col].dropna().head(5).tolist()
                
            # Si es categórica y tiene pocos valores, enviamos todos los únicos
            # para que Gemini sepa exactamente qué etiquetas existen (ej: países)
            if col in categorical_cols and unique_counts[col] <= 50:
                unique_values[col] = df[col].dropna().unique().tolist()
        
        # 5. Contar nulls
        null_counts = df.isnull().sum().to_dict()
        
        return DataFrameMetadata(
            shape=df.shape,
            columns=df.columns.tolist(),
            dtypes={col: str(dtype) for col, dtype in df.dtypes.items()},
            numeric_columns=numeric_cols,
            categorical_columns=categorical_cols,
            datetime_columns=datetime_cols,
            null_counts=null_counts,
            sample_values=sample_values,
            unique_counts=unique_counts,
            unique_values=unique_values
        )
    
    def validate_dataframe(self, df: pd.DataFrame) -> Tuple[bool, Optional[str]]:
        """Valida que el DataFrame sea utilizable"""
        
        if df.empty:
            return False, "DataFrame is empty"
        
        return True, None
