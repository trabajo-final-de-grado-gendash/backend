"""Viz Agent - Agente de visualización con Gemini AI"""

__version__ = "0.1.0"

from .models import (
    VizAgentInput,
    VizAgentOutput,
    DataFrameMetadata,
    ValidationResult,
    GeminiResponse,
    CorrectionRequest,
    CodeCorrectionResponse,
    ChartModificationResponse,
)
from .agent import VizAgent
from .config import Settings
from .analyzer import DataFrameAnalyzer
from .validator import CodeValidator
from .gemini_client import GeminiClient
from .logger import VizAgentLogger

__all__ = [
    "VizAgentInput",
    "VizAgentOutput",
    "DataFrameMetadata",
    "ValidationResult",
    "GeminiResponse",
    "CorrectionRequest",
    "CodeCorrectionResponse",
    "ChartModificationResponse",
    "VizAgent",
    "Settings",
    "DataFrameAnalyzer",
    "CodeValidator",
    "GeminiClient",
    "VizAgentLogger",
]
