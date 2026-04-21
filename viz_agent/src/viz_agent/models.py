# viz_agent/models.py

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
import pandas as pd


class VizAgentInput(BaseModel):
    """Input del agente de visualización"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    dataframe: pd.DataFrame = Field(..., description="DataFrame con los datos a visualizar")
    user_request: str = Field(..., description="Request del usuario en lenguaje natural")
    allowed_charts: List[str] = Field(
        default=["bar", "line", "pie", "scatter", "histogram", "heatmap", "box"],
        description="Lista de tipos de gráficos permitidos"
    )


class DataFrameMetadata(BaseModel):
    """Metadata extraída del DataFrame para enviar a Gemini"""
    shape: tuple[int, int]
    columns: List[str]
    dtypes: Dict[str, str]
    numeric_columns: List[str]
    categorical_columns: List[str]
    datetime_columns: List[str]
    null_counts: Dict[str, int]
    sample_values: Dict[str, List[Any]]  # Primeras 5 filas de cada columna
    unique_counts: Dict[str, int]  # Cantidad de valores únicos por columna
    unique_values: Dict[str, List[Any]] = Field(default_factory=dict)  # Valores únicos (limitado a <=50)

class VizAgentOutput(BaseModel):
    """Output del agente de visualización"""
    success: bool
    plotly_code: Optional[str] = None
    plotly_json: Optional[Dict[str, Any]] = None
    chart_type: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Metadata incluye:
    # - attempts: int (cantidad de intentos)
    # - decision_reasoning: str (por qué eligió ese gráfico)
    # - corrections_made: List[str] (errores corregidos)
    # - execution_time: float (tiempo en segundos)


class ValidationResult(BaseModel):
    """Resultado de validar código Plotly"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    success: bool
    figure: Optional[Any] = None  # plotly.graph_objects.Figure
    error_type: Optional[str] = None  # "syntax" | "runtime" | "empty"
    error_message: Optional[str] = None
    traceback: Optional[str] = None


class GeminiResponse(BaseModel):
    """Respuesta estructurada de Gemini usando structured output"""
    model_config = ConfigDict(extra='forbid')  # No permitir campos adicionales para Gemini
    
    chart_type: str = Field(..., description="Tipo de gráfico elegido de la lista permitida")
    reasoning: str = Field(..., description="Explicación de por qué se eligió este tipo de gráfico")
    plotly_code: str = Field(..., description="Código Python completo con Plotly para generar la visualización")
    customizations: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Personalizaciones aplicadas (colores, títulos, etc.)"
    )


class CorrectionRequest(BaseModel):
    """Request de corrección a Gemini"""
    original_code: str
    error_message: str
    error_type: str
    dataframe_metadata: DataFrameMetadata
    attempt_number: int


class CodeCorrectionResponse(BaseModel):
    """Respuesta de corrección de código usando structured output"""
    model_config = ConfigDict(extra='forbid')  # No permitir campos adicionales para Gemini
    
    corrected_code: str = Field(..., description="Código Python corregido y ejecutable")
    explanation: str = Field(..., description="Explicación breve de qué se corrigió")


class ChartModificationResponse(BaseModel):
    """Respuesta de modificación de gráfico usando structured output"""
    model_config = ConfigDict(extra='forbid')
    
    modified_code: str = Field(
        ..., 
        description="Código Python Plotly modificado según la instrucción del usuario. Solo el código, sin markdown ni explicaciones."
    )
    changes_description: str = Field(
        ..., 
        description="Descripción breve de los cambios realizados"
    )
