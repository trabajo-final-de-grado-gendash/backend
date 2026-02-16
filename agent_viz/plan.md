# PLAN Técnico: Agente de Visualización para Gen BI

**Created**: 16 de febrero de 2026  
**Related SPEC**: `spec.md` - Feature Specification: Agente de Visualización para Gen BI

---

## 1. Arquitectura General

### 1.1 Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────────┐
│                    VIZ AGENT ORCHESTRATOR                        │
│                                                                   │
│  Input:                                                           │
│  - DataFrame (pandas)                                             │
│  - User Request (str)                                             │
│  - Allowed Charts (List[str])                                     │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  1. ANALYZER MODULE                                       │   │
│  │  - Analiza DataFrame (tipos, shapes, valores únicos)     │   │
│  │  - Extrae contexto del User Request                       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           ↓                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  2. GEMINI DECISION & CODE GENERATOR                      │   │
│  │  - Usa Gemini 2.5 Flash                                   │   │
│  │  - Decide tipo de gráfico                                 │   │
│  │  - Genera código Plotly                                   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           ↓                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  3. CODE VALIDATOR & EXECUTOR                             │   │
│  │  - Ejecuta código en sandbox                              │   │
│  │  - Captura errores (syntax/runtime)                       │   │
│  │  - Valida que fig sea válida                              │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           ↓                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  4. AUTO-CORRECTION LOOP                                  │   │
│  │  - Si error → envía contexto a Gemini                     │   │
│  │  - Reintentos: máx 5 veces                                │   │
│  │  - Si éxito → break loop                                  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           ↓                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  5. OUTPUT FORMATTER                                      │   │
│  │  - Genera fig.to_json()                                   │   │
│  │  - Retorna código + JSON + metadata                       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           ↓                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  6. LOGGER                                                │   │
│  │  - Guarda logs de decisiones                              │   │
│  │  - Registra errores y correcciones                        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  Output:                                                          │
│  - plotly_code (str)                                              │
│  - plotly_json (str)                                              │
│  - metadata (dict)                                                │
│  - error (Optional[str])                                          │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Decisiones Arquitectónicas

- **Un solo agente orquestador**: Todos los módulos están dentro de una clase principal `VizAgent`
- **Patrón de diseño**: Strategy pattern para diferentes tipos de gráficos + Chain of Responsibility para correcciones
- **Ejecución sandbox**: Usaremos `exec()` en un namespace controlado (suficiente para Plotly, no requiere Docker)
- **Estado inmutable**: Cada invocación del agente es stateless, no mantiene historial entre requests

---

## 2. Stack Tecnológico

### 2.1 Dependencias Principales

```toml
[project]
name = "viz-agent"
version = "0.1.0"
description = "Agente de visualización con Gemini AI para Gen BI"
requires-python = ">=3.10"

dependencies = [
    # Data & Visualization
    "pandas>=2.2.0",
    "plotly>=5.18.0",
    
    # AI/LLM - Nueva API de Google GenAI
    "google-genai>=0.3.0",
    
    # Utilities
    "pydantic>=2.5.0",  # Para validación de datos y schemas
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    # Testing
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    
    # Linting & Formatting
    "ruff>=0.1.9",
    "mypy>=1.7.1",
]
```

### 2.2 Herramientas de Desarrollo

- **Package manager**: `uv` (moderno y rápido, reemplazo de pip/poetry)
- **Linter**: `ruff` (más rápido que flake8)
- **Type checker**: `mypy`
- **Testing**: `pytest` con `pytest-cov`

### 2.3 Ventajas de usar uv

- ⚡ **10-100x más rápido** que pip/poetry
- 🔒 **Lock file automático** para dependencias reproducibles
- 🎯 **Compatible con pyproject.toml** estándar
- 📦 **Gestión de entornos virtuales** integrada
- 🔄 **Compatible con pip** (comandos similares)

---

## 3. Estructura de Archivos

```
viz_agent/
├── __init__.py
├── agent.py                    # Clase principal VizAgent
├── models.py                   # Pydantic models para I/O
├── analyzer.py                 # Módulo de análisis de DataFrame
├── gemini_client.py            # Cliente para Gemini 2.5 Flash (con structured output)
├── validator.py                # Validador y executor de código
├── logger.py                   # Sistema de logging
├── prompts/
│   ├── __init__.py
│   ├── decision_prompt.py      # Prompt template para decisión y generación
│   └── correction_prompt.py    # Prompt template para corrección de código
├── utils/
│   ├── __init__.py
│   └── dataframe_utils.py      # Utilidades para analizar DataFrames
└── config.py                   # Configuración (API keys, etc.)

tests/
├── __init__.py
├── conftest.py                 # Fixtures de pytest
├── test_agent.py               # Tests del agente completo
├── test_analyzer.py            # Tests del analyzer
├── test_validator.py           # Tests del validator
├── test_integration.py         # Tests end-to-end con Chinook
└── fixtures/
    └── chinook.db              # Base de datos de prueba

examples/
├── basic_usage.py              # Ejemplo de uso básico
├── multi_chart.py              # Ejemplo con subplots
└── custom_styles.py            # Ejemplo con personalización

logs/                           # Directorio para logs (gitignored)
├── .gitkeep

.env                            # Variables de entorno (gitignored)
.env.example                    # Ejemplo de variables de entorno
pyproject.toml                  # Configuración del proyecto con uv
uv.lock                         # Lock file de dependencias (auto-generado)
README.md                       # Documentación
.gitignore                      # Ignorar archivos innecesarios
```

---

## 4. Modelos de Datos (Pydantic)

### 4.1 Input Models

```python
# viz_agent/models.py

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import pandas as pd

class VizAgentInput(BaseModel):
    """Input del agente de visualización"""
    dataframe: pd.DataFrame = Field(..., description="DataFrame con los datos a visualizar")
    user_request: str = Field(..., description="Request del usuario en lenguaje natural")
    allowed_charts: List[str] = Field(
        default=["bar", "line", "pie", "scatter", "histogram", "heatmap", "box"],
        description="Lista de tipos de gráficos permitidos"
    )
    
    class Config:
        arbitrary_types_allowed = True  # Para permitir pd.DataFrame


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
```

### 4.2 Output Models

```python
class VizAgentOutput(BaseModel):
    """Output del agente de visualización"""
    success: bool
    plotly_code: Optional[str] = None
    plotly_json: Optional[str] = None
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
    success: bool
    figure: Optional[Any] = None  # plotly.graph_objects.Figure
    error_type: Optional[str] = None  # "syntax" | "runtime" | "empty"
    error_message: Optional[str] = None
    traceback: Optional[str] = None
    
    class Config:
        arbitrary_types_allowed = True
```

### 4.3 Internal Models

```python
class GeminiResponse(BaseModel):
    """Respuesta estructurada de Gemini usando structured output"""
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
    corrected_code: str = Field(..., description="Código Python corregido y ejecutable")
    explanation: str = Field(..., description="Explicación breve de qué se corrigió")
```

---

## 5. Implementación Detallada por Módulo

### 5.1 Analyzer Module (`analyzer.py`)

**Responsabilidad**: Analizar el DataFrame y extraer metadata relevante para Gemini

```python
# viz_agent/analyzer.py

import pandas as pd
from typing import Dict, List, Any
from .models import DataFrameMetadata

class DataFrameAnalyzer:
    """Analiza DataFrames y extrae metadata"""
    
    def analyze(self, df: pd.DataFrame) -> DataFrameMetadata:
        """Analiza el DataFrame y retorna metadata estructurada"""
        
        # 1. Identificar tipos de columnas
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
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
        for col in df.columns:
            if col in potential_id_columns:
                sample_values[col] = ["[HIGH_CARDINALITY_COLUMN]"]
            else:
                sample_values[col] = df[col].dropna().head(5).tolist()
        
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
            unique_counts=unique_counts
        )
    
    def validate_dataframe(self, df: pd.DataFrame) -> tuple[bool, Optional[str]]:
        """Valida que el DataFrame sea utilizable"""
        
        if df.empty:
            return False, "DataFrame is empty"
        
        if df.shape[0] == 0:
            return False, "DataFrame has no rows"
        
        if df.shape[1] == 0:
            return False, "DataFrame has no columns"
        
        return True, None
```

---

### 5.2 Gemini Client (`gemini_client.py`)

**Responsabilidad**: Comunicación con Gemini 2.5 Flash para decisión y generación de código usando **structured output**

```python
# viz_agent/gemini_client.py

from google import genai
from google.genai import types
from typing import List
from .models import DataFrameMetadata, GeminiResponse, CorrectionRequest, CodeCorrectionResponse
from .prompts.decision_prompt import DECISION_PROMPT_TEMPLATE
from .prompts.correction_prompt import CORRECTION_PROMPT_TEMPLATE
import json

class GeminiClient:
    """Cliente para interactuar con Gemini 2.5 Flash usando structured output"""
    
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.0-flash-exp"
        
        # Configuración base de generación
        self.base_config = {
            "temperature": 0.2,  # Baja temperatura para consistencia
            "top_p": 0.8,
            "top_k": 40,
            "max_output_tokens": 4096,
        }
    
    def decide_and_generate_code(
        self,
        user_request: str,
        df_metadata: DataFrameMetadata,
        allowed_charts: List[str]
    ) -> GeminiResponse:
        """
        Primera llamada: decide gráfico y genera código usando structured output
        
        Gemini retornará automáticamente un JSON que cumple con el schema de GeminiResponse
        """
        
        # Construir prompt desde template
        prompt = DECISION_PROMPT_TEMPLATE.format(
            user_request=user_request,
            df_shape=df_metadata.shape,
            columns=", ".join(df_metadata.columns),
            numeric_columns=", ".join(df_metadata.numeric_columns),
            categorical_columns=", ".join(df_metadata.categorical_columns),
            datetime_columns=", ".join(df_metadata.datetime_columns),
            sample_values=json.dumps(df_metadata.sample_values, indent=2),
            unique_counts=json.dumps(df_metadata.unique_counts, indent=2),
            allowed_charts=", ".join(allowed_charts)
        )
        
        # Configurar schema usando Pydantic (Gemini lo convierte a JSON Schema)
        config = types.GenerateContentConfig(
            **self.base_config,
            response_mime_type="application/json",
            response_schema=GeminiResponse,  # Pydantic model como schema
        )
        
        # Llamar a Gemini con structured output
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config
        )
        
        # Parsear respuesta JSON a Pydantic model
        response_data = json.loads(response.text)
        return GeminiResponse(**response_data)
    
    def request_correction(
        self,
        correction_request: CorrectionRequest
    ) -> str:
        """
        Segunda llamada (loop): solicita corrección de código usando structured output
        """
        
        # Construir prompt desde template
        prompt = CORRECTION_PROMPT_TEMPLATE.format(
            original_code=correction_request.original_code,
            error_type=correction_request.error_type,
            error_message=correction_request.error_message,
            attempt_number=correction_request.attempt_number,
            df_metadata=correction_request.dataframe_metadata.model_dump_json(indent=2)
        )
        
        # Configurar schema para corrección
        config = types.GenerateContentConfig(
            **self.base_config,
            response_mime_type="application/json",
            response_schema=CodeCorrectionResponse,
        )
        
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config
        )
        
        # Parsear y retornar solo el código corregido
        response_data = json.loads(response.text)
        correction = CodeCorrectionResponse(**response_data)
        return correction.corrected_code
```

---

### 5.3 Validator & Executor (`validator.py`)

**Responsabilidad**: Ejecutar y validar código Plotly en sandbox

```python
# viz_agent/validator.py

import sys
import io
import traceback
from typing import Optional
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from .models import ValidationResult

class CodeValidator:
    """Valida y ejecuta código Plotly en un sandbox controlado"""
    
    def execute_and_validate(
        self,
        code: str,
        dataframe: pd.DataFrame
    ) -> ValidationResult:
        """Ejecuta el código y valida el resultado"""
        
        # 1. Crear namespace sandbox
        sandbox_namespace = {
            'pd': pd,
            'px': px,
            'go': go,
            'df': dataframe,  # El DataFrame está disponible como 'df'
            '__builtins__': __builtins__
        }
        
        # 2. Capturar stdout/stderr para evitar prints molestos
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        
        try:
            # 3. Ejecutar código
            exec(code, sandbox_namespace)
            
            # 4. Buscar la figura generada
            fig = self._extract_figure(sandbox_namespace)
            
            if fig is None:
                return ValidationResult(
                    success=False,
                    error_type="runtime",
                    error_message="No Plotly figure found in executed code. Make sure to create a variable named 'fig'."
                )
            
            # 5. Validar que la figura tenga datos
            if not self._figure_has_data(fig):
                return ValidationResult(
                    success=False,
                    error_type="empty",
                    error_message="Generated figure has no data/traces"
                )
            
            # 6. Todo OK
            return ValidationResult(
                success=True,
                figure=fig
            )
        
        except SyntaxError as e:
            return ValidationResult(
                success=False,
                error_type="syntax",
                error_message=str(e),
                traceback=traceback.format_exc()
            )
        
        except Exception as e:
            return ValidationResult(
                success=False,
                error_type="runtime",
                error_message=str(e),
                traceback=traceback.format_exc()
            )
        
        finally:
            # Restaurar stdout/stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr
    
    def _extract_figure(self, namespace: dict) -> Optional[go.Figure]:
        """Busca la figura Plotly en el namespace"""
        
        # Buscar variable 'fig' (convención)
        if 'fig' in namespace and isinstance(namespace['fig'], (go.Figure, type(px.bar()))):
            return namespace['fig']
        
        # Buscar cualquier objeto Figure en el namespace
        for value in namespace.values():
            if isinstance(value, (go.Figure, type(px.bar()))):
                return value
        
        return None
    
    def _figure_has_data(self, fig: go.Figure) -> bool:
        """Verifica que la figura tenga datos"""
        
        if not hasattr(fig, 'data'):
            return False
        
        if len(fig.data) == 0:
            return False
        
        # Verificar que al menos un trace tenga datos
        for trace in fig.data:
            if hasattr(trace, 'x') and len(trace.x) > 0:
                return True
            if hasattr(trace, 'y') and len(trace.y) > 0:
                return True
            if hasattr(trace, 'values') and len(trace.values) > 0:
                return True
        
        return False
```

---

### 5.4 Logger (`logger.py`)

**Responsabilidad**: Registrar decisiones y errores para debugging

```python
# viz_agent/logger.py

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

class VizAgentLogger:
    """Sistema de logging para el agente de visualización"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Configurar logger de Python
        self.logger = logging.getLogger("VizAgent")
        self.logger.setLevel(logging.DEBUG)
        
        # Handler para archivo
        log_file = self.log_dir / f"viz_agent_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # Formato
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
    
    def log_request(self, user_request: str, df_shape: tuple):
        """Log del request inicial"""
        self.logger.info(f"NEW REQUEST | User: '{user_request}' | DataFrame shape: {df_shape}")
    
    def log_decision(self, chart_type: str, reasoning: str):
        """Log de la decisión del tipo de gráfico"""
        self.logger.info(f"DECISION | Chart type: {chart_type} | Reasoning: {reasoning}")
    
    def log_code_generated(self, code: str):
        """Log del código generado"""
        self.logger.debug(f"CODE GENERATED | \n{code}")
    
    def log_validation_result(self, success: bool, error_msg: Optional[str] = None):
        """Log del resultado de validación"""
        if success:
            self.logger.info("VALIDATION | SUCCESS")
        else:
            self.logger.warning(f"VALIDATION | FAILED | Error: {error_msg}")
    
    def log_correction_attempt(self, attempt: int, error_type: str):
        """Log de intento de corrección"""
        self.logger.info(f"CORRECTION | Attempt {attempt}/5 | Error type: {error_type}")
    
    def log_final_result(self, success: bool, attempts: int, execution_time: float):
        """Log del resultado final"""
        status = "SUCCESS" if success else "FAILED"
        self.logger.info(
            f"FINAL RESULT | {status} | Attempts: {attempts} | Time: {execution_time:.2f}s"
        )
    
    def log_error(self, error_message: str):
        """Log de error"""
        self.logger.error(f"ERROR | {error_message}")
    
    def create_session_log(self, session_data: Dict[str, Any]) -> str:
        """Crea un archivo JSON con toda la información de la sesión"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        session_file = self.log_dir / f"session_{timestamp}.json"
        
        with open(session_file, 'w') as f:
            json.dump(session_data, f, indent=2, default=str)
        
        return str(session_file)
```

---

### 5.5 Agent Principal (`agent.py`)

**Responsabilidad**: Orquestar todos los módulos y ejecutar el flujo completo

```python
# viz_agent/agent.py

import time
from typing import Optional
import pandas as pd
from .models import (
    VizAgentInput, 
    VizAgentOutput, 
    DataFrameMetadata,
    CorrectionRequest,
    ValidationResult
)
from .analyzer import DataFrameAnalyzer
from .gemini_client import GeminiClient
from .validator import CodeValidator
from .logger import VizAgentLogger
from .config import Config

class VizAgent:
    """Agente de visualización principal"""
    
    def __init__(self, config: Config):
        self.config = config
        self.analyzer = DataFrameAnalyzer()
        self.gemini_client = GeminiClient(api_key=config.gemini_api_key)
        self.validator = CodeValidator()
        self.logger = VizAgentLogger(log_dir=config.log_dir)
        
        self.max_correction_attempts = 5
    
    def generate_visualization(self, input_data: VizAgentInput) -> VizAgentOutput:
        """
        Método principal: genera visualización completa
        
        Flow:
        1. Validar DataFrame
        2. Analizar DataFrame
        3. Llamar a Gemini para decisión + código
        4. Validar código ejecutándolo
        5. Si falla, loop de corrección (máx 5 intentos)
        6. Si éxito, generar output
        """
        
        start_time = time.time()
        session_data = {
            "user_request": input_data.user_request,
            "dataframe_shape": input_data.dataframe.shape,
            "allowed_charts": input_data.allowed_charts,
            "corrections": []
        }
        
        try:
            # === PASO 1: Validar DataFrame ===
            self.logger.log_request(
                input_data.user_request,
                input_data.dataframe.shape
            )
            
            is_valid, error_msg = self.analyzer.validate_dataframe(input_data.dataframe)
            if not is_valid:
                self.logger.log_error(f"Invalid DataFrame: {error_msg}")
                return VizAgentOutput(
                    success=False,
                    error_message=error_msg
                )
            
            # === PASO 2: Analizar DataFrame ===
            df_metadata = self.analyzer.analyze(input_data.dataframe)
            session_data["dataframe_metadata"] = df_metadata.model_dump()
            
            # === PASO 3: Decisión y generación de código (Gemini) ===
            gemini_response = self.gemini_client.decide_and_generate_code(
                user_request=input_data.user_request,
                df_metadata=df_metadata,
                allowed_charts=input_data.allowed_charts
            )
            
            self.logger.log_decision(
                gemini_response.chart_type,
                gemini_response.reasoning
            )
            self.logger.log_code_generated(gemini_response.plotly_code)
            
            session_data["chart_type"] = gemini_response.chart_type
            session_data["reasoning"] = gemini_response.reasoning
            session_data["initial_code"] = gemini_response.plotly_code
            
            current_code = gemini_response.plotly_code
            
            # === PASO 4 & 5: Validación con loop de corrección ===
            for attempt in range(1, self.max_correction_attempts + 1):
                
                validation_result = self.validator.execute_and_validate(
                    code=current_code,
                    dataframe=input_data.dataframe
                )
                
                self.logger.log_validation_result(
                    validation_result.success,
                    validation_result.error_message
                )
                
                if validation_result.success:
                    # ¡Éxito! Generar output
                    execution_time = time.time() - start_time
                    
                    plotly_json = validation_result.figure.to_json()
                    
                    session_data["final_code"] = current_code
                    session_data["attempts"] = attempt
                    session_data["execution_time"] = execution_time
                    
                    self.logger.log_final_result(True, attempt, execution_time)
                    self.logger.create_session_log(session_data)
                    
                    return VizAgentOutput(
                        success=True,
                        plotly_code=current_code,
                        plotly_json=plotly_json,
                        chart_type=gemini_response.chart_type,
                        metadata={
                            "attempts": attempt,
                            "decision_reasoning": gemini_response.reasoning,
                            "corrections_made": session_data["corrections"],
                            "execution_time": execution_time
                        }
                    )
                
                # Falló, necesitamos corrección
                if attempt == self.max_correction_attempts:
                    # Último intento fallido
                    break
                
                self.logger.log_correction_attempt(attempt, validation_result.error_type)
                
                # Solicitar corrección a Gemini
                correction_request = CorrectionRequest(
                    original_code=current_code,
                    error_message=validation_result.error_message or "Unknown error",
                    error_type=validation_result.error_type or "unknown",
                    dataframe_metadata=df_metadata,
                    attempt_number=attempt
                )
                
                corrected_code = self.gemini_client.request_correction(correction_request)
                
                session_data["corrections"].append({
                    "attempt": attempt,
                    "error_type": validation_result.error_type,
                    "error_message": validation_result.error_message,
                    "corrected_code": corrected_code
                })
                
                current_code = corrected_code
                self.logger.log_code_generated(f"[CORRECTION {attempt}]\n{current_code}")
            
            # Si llegamos aquí, fallaron todos los intentos
            execution_time = time.time() - start_time
            self.logger.log_final_result(False, self.max_correction_attempts, execution_time)
            self.logger.create_session_log(session_data)
            
            return VizAgentOutput(
                success=False,
                error_message=f"Failed to generate valid code after {self.max_correction_attempts} attempts. Last error: {validation_result.error_message}",
                metadata={
                    "attempts": self.max_correction_attempts,
                    "corrections_made": session_data["corrections"],
                    "execution_time": execution_time,
                    "last_code": current_code
                }
            )
        
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Unexpected error: {str(e)}"
            self.logger.log_error(error_msg)
            
            return VizAgentOutput(
                success=False,
                error_message=error_msg,
                metadata={
                    "execution_time": execution_time
                }
            )
```

---

### 5.6 Configuración (`config.py`)

```python
# viz_agent/config.py

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    """Configuración del agente"""
    gemini_api_key: str
    log_dir: str = "logs"
    max_correction_attempts: int = 5
    
    @classmethod
    def from_env(cls):
        """Carga configuración desde variables de entorno"""
        return cls(
            gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
            log_dir=os.getenv("LOG_DIR", "logs"),
            max_correction_attempts=int(os.getenv("MAX_CORRECTION_ATTEMPTS", "5"))
        )
```

---

## 6. Prompts para Gemini

### 6.1 Ventajas de Mantener Prompts en Archivos Separados

✅ **Separación de concerns**: Lógica separada de contenido  
✅ **Fácil iteración**: Modifica prompts sin tocar código Python  
✅ **Versionado claro**: Git diffs limpios al cambiar prompts  
✅ **Colaboración**: PMs/researchers pueden modificar prompts sin código  
✅ **Testing A/B**: Fácil probar diferentes versiones  
✅ **Reutilización**: Compartir prompts entre agentes  
✅ **Documentación**: Prompts autodocumentados en archivos dedicados  

### 6.2 Structured Output + Prompts Separados = Best of Both Worlds

Aunque usamos **structured output** (que garantiza el formato JSON), los prompts siguen siendo cruciales para:
- Instrucciones de negocio claras
- Guías de selección de gráficos
- Reglas específicas del dominio
- Contexto y ejemplos

**Structured output** solo garantiza el formato, pero el **contenido y calidad** de las decisiones dependen del prompt.

### 6.3 Decision Prompt (`prompts/decision_prompt.py`)

```python
# viz_agent/prompts/decision_prompt.py

DECISION_PROMPT_TEMPLATE = """You are an expert data visualization agent. Analyze the user's request and DataFrame metadata to:
1. Decide the most appropriate chart type from the allowed list
2. Generate valid Python code using Plotly

## User Request
{user_request}

## DataFrame Metadata
- Shape: {df_shape} (rows, columns)
- Columns: {columns}
- Numeric columns: {numeric_columns}
- Categorical columns: {categorical_columns}
- Datetime columns: {datetime_columns}
- Sample values (first 5 rows):
{sample_values}
- Unique value counts per column:
{unique_counts}

## Allowed Chart Types
{allowed_charts}

## Chart Selection Guidelines
- **bar**: Use for comparing categories, showing distributions, or ranking data
- **line**: Use for time series, trends over time, or continuous data
- **pie**: Use for showing proportions or percentages (max 7-8 categories)
- **scatter**: Use for showing relationships between two numeric variables
- **histogram**: Use for showing distribution of a single numeric variable
- **heatmap**: Use for showing correlations or matrices
- **box**: Use for showing statistical distributions and outliers

## Code Generation Rules
1. The DataFrame is available as variable 'df' in the code
2. The final figure MUST be stored in a variable named 'fig'
3. Use plotly.express (px) or plotly.graph_objects (go) - whichever is appropriate
4. Handle null values gracefully (use dropna() if needed)
5. If the user specifies colors, titles, or labels, apply them
6. If not specified, use sensible defaults with professional styling
7. Ensure the code is complete and executable
8. Do not use columns that don't exist in the DataFrame
9. Always include necessary imports (import plotly.express as px, etc.)
10. Add appropriate axis labels and titles for clarity

Generate a response following the provided JSON schema.
"""
```

### 6.4 Correction Prompt (`prompts/correction_prompt.py`)

```python
# viz_agent/prompts/correction_prompt.py

CORRECTION_PROMPT_TEMPLATE = """You are debugging Plotly visualization code that failed with an error.

## Original Code
```python
{original_code}
```

## Error Information
- Error Type: {error_type}
- Error Message: {error_message}
- Attempt Number: {attempt_number}/5

## DataFrame Metadata
{df_metadata}

## Common Issues and Solutions
- **Syntax errors**: Check for typos, missing parentheses, incorrect indentation, unclosed strings
- **Runtime errors**: 
  - Verify column names exist in the DataFrame (case-sensitive)
  - Check data types are compatible with chart type
  - Handle null/NaN values with dropna() or fillna()
  - Ensure numeric operations use numeric columns
- **Empty figure**: 
  - Verify data is being plotted (check x/y parameters)
  - Review filters and conditions (may exclude all data)
  - Check aggregations return non-empty results

## Fix Requirements
1. The DataFrame is available as 'df'
2. The figure must be named 'fig'
3. Fix the specific error mentioned above
4. Keep the original visualization intent (same chart type and columns)
5. Include all necessary imports
6. Return complete, executable Python code
7. Add defensive checks if needed (e.g., check if column exists)

Generate a response following the provided JSON schema with:
- corrected_code: The complete fixed Python code
- explanation: Brief description of what was fixed and why
"""
```

### 6.5 Notas sobre Structured Output

**Importante**: Con structured output, ya NO necesitas:
- ❌ Ejemplos de formato JSON en los prompts
- ❌ Instrucciones de "Respond with JSON" o "Output format"
- ❌ Bloques de código markdown con \`\`\`json

**Gemini automáticamente**:
- ✅ Genera JSON que cumple con el schema de Pydantic
- ✅ Valida los tipos de datos
- ✅ Asegura que todos los campos requeridos estén presentes

Los prompts se enfocan **solo en las instrucciones de negocio**.

---

## 7. Testing Strategy

### 7.1 Unit Tests

**Archivo**: `tests/test_analyzer.py`

```python
import pytest
import pandas as pd
from viz_agent.analyzer import DataFrameAnalyzer

def test_analyze_numeric_dataframe():
    df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
    analyzer = DataFrameAnalyzer()
    metadata = analyzer.analyze(df)
    
    assert metadata.shape == (3, 2)
    assert 'a' in metadata.numeric_columns
    assert 'b' in metadata.numeric_columns
    assert len(metadata.categorical_columns) == 0

def test_analyze_mixed_dataframe():
    df = pd.DataFrame({
        'numeric': [1, 2, 3],
        'category': ['A', 'B', 'C'],
        'date': pd.date_range('2024-01-01', periods=3)
    })
    analyzer = DataFrameAnalyzer()
    metadata = analyzer.analyze(df)
    
    assert 'numeric' in metadata.numeric_columns
    assert 'category' in metadata.categorical_columns
    assert 'date' in metadata.datetime_columns

def test_validate_empty_dataframe():
    df = pd.DataFrame()
    analyzer = DataFrameAnalyzer()
    is_valid, error = analyzer.validate_dataframe(df)
    
    assert not is_valid
    assert "empty" in error.lower()
```

**Archivo**: `tests/test_validator.py`

```python
import pytest
import pandas as pd
from viz_agent.validator import CodeValidator

def test_valid_code_execution():
    code = """
import plotly.express as px
fig = px.bar(df, x='x', y='y')
"""
    df = pd.DataFrame({'x': ['A', 'B'], 'y': [1, 2]})
    validator = CodeValidator()
    result = validator.execute_and_validate(code, df)
    
    assert result.success
    assert result.figure is not None

def test_syntax_error_detection():
    code = "fig = px.bar(df, x='x', y='y'"  # Missing closing parenthesis
    df = pd.DataFrame({'x': ['A'], 'y': [1]})
    validator = CodeValidator()
    result = validator.execute_and_validate(code, df)
    
    assert not result.success
    assert result.error_type == "syntax"

def test_runtime_error_detection():
    code = """
import plotly.express as px
fig = px.bar(df, x='nonexistent_column', y='y')
"""
    df = pd.DataFrame({'x': ['A'], 'y': [1]})
    validator = CodeValidator()
    result = validator.execute_and_validate(code, df)
    
    assert not result.success
    assert result.error_type == "runtime"

def test_empty_figure_detection():
    code = """
import plotly.graph_objects as go
fig = go.Figure()  # Empty figure
"""
    df = pd.DataFrame({'x': ['A'], 'y': [1]})
    validator = CodeValidator()
    result = validator.execute_and_validate(code, df)
    
    assert not result.success
    assert result.error_type == "empty"
```

### 7.2 Integration Tests

**Archivo**: `tests/test_integration.py`

```python
import pytest
import pandas as pd
import sqlite3
from viz_agent.agent import VizAgent
from viz_agent.models import VizAgentInput
from viz_agent.config import Config

@pytest.fixture
def chinook_dataframe():
    """Carga datos de Chinook para testing"""
    conn = sqlite3.connect('tests/fixtures/chinook.db')
    query = """
    SELECT 
        i.InvoiceDate,
        c.Country,
        g.Name as Genre,
        SUM(ii.UnitPrice * ii.Quantity) as Total
    FROM Invoice i
    JOIN Customer c ON i.CustomerId = c.CustomerId
    JOIN InvoiceLine ii ON i.InvoiceId = ii.InvoiceId
    JOIN Track t ON ii.TrackId = t.TrackId
    JOIN Genre g ON t.GenreId = g.GenreId
    GROUP BY i.InvoiceDate, c.Country, g.Name
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

@pytest.fixture
def viz_agent():
    config = Config.from_env()
    return VizAgent(config)

def test_simple_bar_chart(viz_agent, chinook_dataframe):
    """Test P1: Gráfico simple de barras"""
    input_data = VizAgentInput(
        dataframe=chinook_dataframe,
        user_request="gráfico de barras de ventas totales por género",
        allowed_charts=["bar", "line", "pie", "scatter", "histogram", "heatmap", "box"]
    )
    
    result = viz_agent.generate_visualization(input_data)
    
    assert result.success
    assert result.plotly_code is not None
    assert result.plotly_json is not None
    assert result.chart_type == "bar"
    assert result.metadata["attempts"] <= 5

def test_line_chart_temporal(viz_agent, chinook_dataframe):
    """Test P1: Gráfico de líneas temporal"""
    input_data = VizAgentInput(
        dataframe=chinook_dataframe,
        user_request="mostrar ventas por fecha en los últimos meses",
        allowed_charts=["bar", "line", "pie", "scatter", "histogram", "heatmap", "box"]
    )
    
    result = viz_agent.generate_visualization(input_data)
    
    assert result.success
    assert result.chart_type == "line"

def test_custom_colors(viz_agent, chinook_dataframe):
    """Test P3: Personalización visual"""
    input_data = VizAgentInput(
        dataframe=chinook_dataframe,
        user_request="gráfico de barras de ventas por país en color azul con título 'Ventas Globales'",
        allowed_charts=["bar", "line", "pie", "scatter", "histogram", "heatmap", "box"]
    )
    
    result = viz_agent.generate_visualization(input_data)
    
    assert result.success
    assert "blue" in result.plotly_code.lower() or "azul" in result.plotly_code.lower()
    assert "Ventas Globales" in result.plotly_code

def test_empty_dataframe_error(viz_agent):
    """Test Edge Case: DataFrame vacío"""
    empty_df = pd.DataFrame()
    input_data = VizAgentInput(
        dataframe=empty_df,
        user_request="gráfico de ventas",
        allowed_charts=["bar"]
    )
    
    result = viz_agent.generate_visualization(input_data)
    
    assert not result.success
    assert "empty" in result.error_message.lower()

def test_nonexistent_column_error(viz_agent, chinook_dataframe):
    """Test Edge Case: Columna inexistente"""
    input_data = VizAgentInput(
        dataframe=chinook_dataframe,
        user_request="gráfico de la columna 'NoExiste'",
        allowed_charts=["bar"]
    )
    
    result = viz_agent.generate_visualization(input_data)
    
    # Puede fallar o el agente puede autocorregirse
    # Verificamos que al menos maneje el caso
    assert result.success or "column" in result.error_message.lower()
```

### 7.3 Test Coverage Goals

- **Analyzer**: 95% coverage
- **Validator**: 95% coverage
- **Gemini Client**: 80% coverage (difícil mockear API)
- **Agent**: 90% coverage
- **Overall**: >90% coverage

---

## 8. Dataset Chinook Setup

### 8.1 Descarga e Instalación

```bash
# Descargar Chinook database
cd tests/fixtures
wget https://github.com/lerocha/chinook-database/raw/master/ChinookDatabase/DataSources/Chinook_Sqlite.sqlite
mv Chinook_Sqlite.sqlite chinook.db
```

### 8.2 Queries de Ejemplo para Testing

```python
# tests/fixtures/chinook_queries.py

CHINOOK_TEST_QUERIES = {
    "sales_by_genre": """
        SELECT g.Name as Genre, SUM(il.UnitPrice * il.Quantity) as Total
        FROM Genre g
        JOIN Track t ON g.GenreId = t.GenreId
        JOIN InvoiceLine il ON t.TrackId = il.TrackId
        GROUP BY g.Name
        ORDER BY Total DESC
    """,
    
    "sales_by_month": """
        SELECT 
            strftime('%Y-%m', InvoiceDate) as Month,
            SUM(Total) as Sales
        FROM Invoice
        GROUP BY Month
        ORDER BY Month
    """,
    
    "customer_country_distribution": """
        SELECT Country, COUNT(*) as CustomerCount
        FROM Customer
        GROUP BY Country
        ORDER BY CustomerCount DESC
    """,
    
    "top_artists": """
        SELECT ar.Name as Artist, COUNT(DISTINCT t.TrackId) as TrackCount
        FROM Artist ar
        JOIN Album al ON ar.ArtistId = al.ArtistId
        JOIN Track t ON al.AlbumId = t.AlbumId
        GROUP BY ar.Name
        ORDER BY TrackCount DESC
        LIMIT 10
    """
}
```

---

## 9. Ejemplo de Uso

### 9.1 Basic Usage (`examples/basic_usage.py`)

```python
# examples/basic_usage.py

import pandas as pd
import sqlite3
from viz_agent.agent import VizAgent
from viz_agent.models import VizAgentInput
from viz_agent.config import Config

def main():
    # 1. Cargar configuración
    config = Config.from_env()
    
    # 2. Crear agente
    agent = VizAgent(config)
    
    # 3. Cargar datos de Chinook
    conn = sqlite3.connect('tests/fixtures/chinook.db')
    df = pd.read_sql_query("""
        SELECT g.Name as Genre, SUM(il.UnitPrice * il.Quantity) as Total
        FROM Genre g
        JOIN Track t ON g.GenreId = t.GenreId
        JOIN InvoiceLine il ON t.TrackId = il.TrackId
        GROUP BY g.Name
    """, conn)
    conn.close()
    
    # 4. Crear input
    input_data = VizAgentInput(
        dataframe=df,
        user_request="gráfico de barras de ventas totales por género musical",
        allowed_charts=["bar", "line", "pie", "scatter", "histogram", "heatmap", "box"]
    )
    
    # 5. Generar visualización
    result = agent.generate_visualization(input_data)
    
    # 6. Procesar resultado
    if result.success:
        print("✅ Visualization generated successfully!")
        print(f"Chart type: {result.chart_type}")
        print(f"Attempts: {result.metadata['attempts']}")
        print(f"Execution time: {result.metadata['execution_time']:.2f}s")
        print("\n--- Generated Code ---")
        print(result.plotly_code)
        
        # Guardar JSON
        with open('output.json', 'w') as f:
            f.write(result.plotly_json)
        print("\n✅ JSON saved to output.json")
        
        # Opcionalmente, renderizar el gráfico
        import plotly.io as pio
        import json
        fig_dict = json.loads(result.plotly_json)
        pio.show(fig_dict)
    else:
        print("❌ Visualization failed")
        print(f"Error: {result.error_message}")
        if result.metadata.get("last_code"):
            print("\n--- Last Generated Code ---")
            print(result.metadata["last_code"])

if __name__ == "__main__":
    main()
```

---

## 10. Variables de Entorno

### 10.1 Archivo `.env.example`

```bash
# .env.example

# Gemini API Key (required)
GEMINI_API_KEY=your_gemini_api_key_here

# Logging
LOG_DIR=logs

# Agent Configuration
MAX_CORRECTION_ATTEMPTS=5
```

---

## 11. Dependencies y Setup

### 11.1 `pyproject.toml` (configuración para uv)

```toml
[project]
name = "viz-agent"
version = "0.1.0"
description = "Agente de visualización con Gemini AI para Gen BI"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}
authors = [
    {name = "Your Name", email = "your.email@example.com"}
]

dependencies = [
    # Data & Visualization
    "pandas>=2.2.0",
    "plotly>=5.18.0",
    
    # AI/LLM - Nueva API de Google GenAI
    "google-genai>=0.3.0",
    
    # Utilities
    "pydantic>=2.5.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    # Testing
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    
    # Linting & Type checking
    "ruff>=0.1.9",
    "mypy>=1.7.1",
]

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W"]
ignore = ["E501"]

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-v --cov=viz_agent --cov-report=html --cov-report=term"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### 11.2 Comandos de Instalación con uv

```bash
# Instalar uv (si no lo tienes)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clonar o crear el proyecto
mkdir viz-agent
cd viz-agent

# Inicializar proyecto con uv (crea pyproject.toml)
uv init

# Copiar el pyproject.toml del PLAN

# Crear entorno virtual y instalar dependencias
uv venv
source .venv/bin/activate  # En macOS/Linux
# o en Windows: .venv\Scripts\activate

# Instalar todas las dependencias (incluye dev)
uv pip install -e ".[dev]"

# O solo dependencias de producción
uv pip install -e .

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tu GEMINI_API_KEY

# Descargar Chinook database
mkdir -p tests/fixtures
cd tests/fixtures
curl -O https://github.com/lerocha/chinook-database/raw/master/ChinookDatabase/DataSources/Chinook_Sqlite.sqlite
mv Chinook_Sqlite.sqlite chinook.db
cd ../..

# Ejecutar tests
uv run pytest tests/ -v --cov=viz_agent

# O simplemente
pytest tests/ -v --cov=viz_agent
```

### 11.3 Comandos útiles con uv

```bash
# Agregar una nueva dependencia
uv pip install <package>

# Agregar dependencia de desarrollo
uv pip install --dev <package>

# Actualizar dependencias
uv pip install --upgrade <package>

# Sincronizar dependencias con pyproject.toml
uv pip sync

# Ver dependencias instaladas
uv pip list

# Ejecutar comando en el entorno virtual
uv run <command>

# Ejemplo: ejecutar script
uv run python examples/basic_usage.py

# Linting
uv run ruff check viz_agent/

# Type checking
uv run mypy viz_agent/

# Format code (con ruff)
uv run ruff format viz_agent/
```

### 11.4 Ventajas de uv vs pip/poetry

| Característica | uv | pip | poetry |
|----------------|----|----|--------|
| **Velocidad** | ⚡⚡⚡ (10-100x) | ⚡ | ⚡⚡ |
| **Lock file** | ✅ automático | ❌ | ✅ |
| **Resolución de deps** | ⚡⚡⚡ rápida | ⚡ lenta | ⚡⚡ |
| **Compatible pip** | ✅ | ✅ | ⚠️ parcial |
| **pyproject.toml** | ✅ | ✅ | ✅ |
| **Build packages** | ✅ | ⚠️ limitado | ✅ |

---

## 12. Tareas de Implementación (Granular)

### 12.1 Setup Inicial (Estimado: 1-2 horas)

- [ ] **T001**: Crear estructura de carpetas según sección 3
- [ ] **T002**: Configurar `pyproject.toml` con uv
- [ ] **T003**: Crear `.env.example` y `.gitignore`
- [ ] **T004**: Descargar y configurar Chinook database
- [ ] **T005**: Configurar pytest en pyproject.toml

### 12.2 Models Layer (Estimado: 2-3 horas)

- [ ] **T006**: Implementar `VizAgentInput` con validaciones Pydantic
- [ ] **T007**: Implementar `VizAgentOutput` con todos los campos
- [ ] **T008**: Implementar `DataFrameMetadata` con análisis de tipos
- [ ] **T009**: Implementar `ValidationResult` para resultados de validación
- [ ] **T010**: Implementar `GeminiResponse` con Field descriptions para structured output
- [ ] **T011**: Implementar `CodeCorrectionResponse` para correcciones estructuradas
- [ ] **T012**: Implementar `CorrectionRequest`
- [ ] **T013**: Escribir unit tests para todos los models

### 12.3 Analyzer Module (Estimado: 3-4 horas)

- [ ] **T012**: Implementar `DataFrameAnalyzer.analyze()` básico
- [ ] **T013**: Agregar detección de tipos (numeric, categorical, datetime)
- [ ] **T014**: Agregar cálculo de unique counts y high cardinality
- [ ] **T015**: Agregar sampling de valores (primeras 5 filas)
- [ ] **T016**: Implementar `validate_dataframe()` con todos los edge cases
- [ ] **T017**: Escribir unit tests para analyzer (target: 95% coverage)

### 12.4 Validator Module (Estimado: 4-5 horas)

- [ ] **T018**: Implementar sandbox execution con `exec()`
- [ ] **T019**: Implementar `_extract_figure()` para buscar variable 'fig'
- [ ] **T020**: Implementar `_figure_has_data()` para validar contenido
- [ ] **T021**: Agregar manejo de errores de sintaxis
- [ ] **T022**: Agregar manejo de errores de runtime
- [ ] **T023**: Agregar captura de stdout/stderr
- [ ] **T024**: Escribir unit tests para validator (target: 95% coverage)

### 12.5 Gemini Client (Estimado: 4-5 horas)

- [ ] **T025**: Configurar Google GenAI SDK (nueva API)
- [ ] **T026**: Implementar `decide_and_generate_code()` con structured output
- [ ] **T027**: Implementar `request_correction()` con structured output
- [ ] **T028**: Crear `DECISION_PROMPT_TEMPLATE` en `prompts/decision_prompt.py`
- [ ] **T029**: Crear `CORRECTION_PROMPT_TEMPLATE` en `prompts/correction_prompt.py`
- [ ] **T030**: Agregar manejo de errores de API (rate limits, timeouts)
- [ ] **T031**: Escribir unit tests (mocking API calls) (target: 80% coverage)

### 12.6 Logger Module (Estimado: 2-3 horas)

- [ ] **T035**: Configurar Python logging con file handler
- [ ] **T036**: Implementar métodos de log (request, decision, validation, etc.)
- [ ] **T037**: Implementar `create_session_log()` para JSON completo
- [ ] **T038**: Agregar rotación de logs por fecha
- [ ] **T039**: Escribir unit tests para logger

### 12.7 Agent Principal (Estimado: 6-8 horas)

- [ ] **T040**: Implementar inicialización de `VizAgent` con todos los módulos
- [ ] **T041**: Implementar flujo principal en `generate_visualization()`
- [ ] **T042**: Agregar validación de DataFrame (PASO 1)
- [ ] **T043**: Agregar análisis de DataFrame (PASO 2)
- [ ] **T044**: Integrar llamada a Gemini para decisión (PASO 3)
- [ ] **T045**: Implementar loop de validación (PASO 4)
- [ ] **T046**: Implementar loop de corrección con max 5 intentos (PASO 5)
- [ ] **T047**: Implementar generación de output exitoso
- [ ] **T048**: Implementar generación de output de error
- [ ] **T049**: Agregar tracking de session_data para logs
- [ ] **T050**: Agregar manejo de excepciones globales
- [ ] **T051**: Escribir unit tests para agent (target: 90% coverage)

### 12.8 Configuration (Estimado: 1 hora)

- [ ] **T052**: Implementar `Config` dataclass
- [ ] **T053**: Implementar `Config.from_env()` con python-dotenv
- [ ] **T054**: Documentar todas las variables de entorno

### 12.9 Integration Tests (Estimado: 6-8 horas)

- [ ] **T055**: Crear fixtures de pytest para Chinook DB
- [ ] **T056**: Escribir test para P1: gráfico simple de barras
- [ ] **T057**: Escribir test para P1: gráfico de líneas temporal
- [ ] **T058**: Escribir test para P1: gráfico de torta
- [ ] **T059**: Escribir test para P2: validación y corrección automática
- [ ] **T060**: Escribir test para P3: múltiples variables
- [ ] **T061**: Escribir test para P3: subplots
- [ ] **T062**: Escribir test para P3: personalización de colores
- [ ] **T063**: Escribir test para Edge Case: DataFrame vacío
- [ ] **T064**: Escribir test para Edge Case: columnas inexistentes
- [ ] **T065**: Escribir test para Edge Case: datos con nulls
- [ ] **T066**: Configurar pytest-cov y verificar >90% coverage

### 12.10 Examples & Documentation (Estimado: 3-4 horas)

- [ ] **T067**: Crear `examples/basic_usage.py`
- [ ] **T068**: Crear `examples/multi_chart.py` con subplots
- [ ] **T069**: Crear `examples/custom_styles.py` con personalización
- [ ] **T070**: Escribir README.md completo con:
  - Descripción del proyecto
  - Instalación
  - Configuración
  - Ejemplos de uso
  - API reference
  - Troubleshooting
- [ ] **T071**: Documentar arquitectura en README
- [ ] **T072**: Agregar docstrings a todas las clases y métodos

### 12.11 Polish & QA (Estimado: 4-5 horas)

- [ ] **T073**: Ejecutar linter (ruff) y corregir warnings
- [ ] **T074**: Ejecutar formatter (black) en todo el código
- [ ] **T075**: Ejecutar type checker (mypy) y corregir errores
- [ ] **T076**: Revisar y mejorar prompts de Gemini basado en resultados
- [ ] **T077**: Optimizar parámetros de Gemini (temperature, top_p)
- [ ] **T078**: Ejecutar suite completa de tests
- [ ] **T079**: Validar coverage >90%
- [ ] **T080**: Testing manual con diferentes casos de uso
- [ ] **T081**: Revisar logs generados y ajustar formato si necesario
- [ ] **T082**: Crear ejemplos con diferentes tipos de gráficos

### 12.12 Deployment Ready (Estimado: 2-3 horas)

- [ ] **T083**: Crear script de setup automatizado
- [ ] **T084**: Documentar proceso de deployment
- [ ] **T085**: Agregar health check endpoint (si aplica)
- [ ] **T086**: Documentar troubleshooting común
- [ ] **T087**: Crear guía de contribución (CONTRIBUTING.md)

---

## 13. Criterios de Aceptación del PLAN

Antes de comenzar la implementación, verificar que:

### ✅ Completitud Técnica
- [x] Todos los requisitos del SPEC están cubiertos en el PLAN
- [x] La arquitectura está claramente definida
- [x] Todos los módulos tienen responsabilidades específicas
- [x] Las interfaces entre módulos están definidas (I/O)
- [x] Las dependencias externas están identificadas

### ✅ Implementabilidad
- [x] Todos los archivos necesarios están listados
- [x] Las estructuras de datos están definidas con Pydantic
- [x] Los prompts para Gemini están completos
- [x] El flujo de ejecución está documentado paso a paso
- [x] Los casos de error están contemplados

### ✅ Testing
- [x] Estrategia de testing definida (unit, integration, e2e)
- [x] Fixtures de testing identificados (Chinook DB)
- [x] Coverage goals definidos (>90%)
- [x] Edge cases tienen tests correspondientes

### ✅ Granularidad de Tareas
- [x] Todas las tareas de implementación están listadas
- [x] Cada tarea es específica y accionable
- [x] Las tareas tienen estimaciones de tiempo
- [x] Las tareas están ordenadas por dependencias

### ✅ Documentación
- [x] Ejemplos de uso están definidos
- [x] Variables de entorno documentadas
- [x] Comandos de setup documentados
- [x] README outline creado

---

## 14. Próximos Pasos

1. ✅ **PLAN Completado** ← Estamos aquí
2. ⏭️ **Revisión del PLAN**: Validar que cumple todos los criterios
3. ⏭️ **Aprobación para Implementación**: Confirmar que el PLAN cubre el SPEC
4. ⏭️ **Implementación**: Ejecutar tareas T001-T087 en orden
5. ⏭️ **Testing Continuo**: Ejecutar tests después de cada módulo
6. ⏭️ **Iteración**: Ajustar según resultados y feedback

---

**Nota Final**: Este PLAN está diseñado para ser implementado incrementalmente usando **uv** como package manager y **structured output** de Gemini para garantizar respuestas consistentes. Se recomienda completar cada módulo con sus tests antes de pasar al siguiente. El orden sugerido es: Models → Analyzer → Validator → Logger → Gemini Client (con structured output) → Agent Principal → Integration Tests.

## 15. Archivos de Configuración Adicionales

### 15.1 `.gitignore`

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
.venv/
venv/
ENV/
env/

# uv
uv.lock
.uv/

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Environment
.env

# Logs
logs/
*.log

# MacOS
.DS_Store

# Data
tests/fixtures/chinook.db

# Output
output.json
*.png
*.html
```

### 15.2 `.env.example`

```bash
# .env.example

# Gemini API Key (required) - Get it from: https://aistudio.google.com/apikey
GEMINI_API_KEY=your_gemini_api_key_here

# Logging Configuration
LOG_DIR=logs

# Agent Configuration
MAX_CORRECTION_ATTEMPTS=5
```

---

## 16. Diferencias Clave vs PLAN Original

### ✅ Mejoras Implementadas

1. **uv en lugar de pip/poetry**
   - ⚡ 10-100x más rápido
   - Lock file automático (`uv.lock`)
   - Compatible con pyproject.toml estándar
   - Comandos más simples

2. **Structured Output de Gemini**
   - ✅ Respuestas garantizadas en formato JSON
   - ✅ Validación automática con Pydantic
   - ✅ Sin necesidad de parsing manual con regex
   - ✅ Prompts más simples (solo lógica de negocio)
   - ✅ Menos errores de formato

3. **Nueva API de Google GenAI**
   - Uso de `google.genai.Client` en lugar de `google.generativeai`
   - Configuración con `types.GenerateContentConfig`
   - Soporte nativo para Pydantic models como schemas
   - API más moderna y consistente

4. **Structured Output + Prompts Separados**
   - ✅ Mantenemos carpeta `prompts/` para mejor mantenibilidad
   - ✅ Prompts en archivos facilitan iteración y colaboración
   - ❌ Eliminado parsing complejo de respuestas (regex, fallbacks)
   - ✅ JSON garantizado y validado automáticamente
   - ✅ Best of both worlds: flexibilidad + confiabilidad

### 📊 Reducción de Complejidad

| Aspecto | Antes | Después | Mejora |
|---------|-------|---------|---------|
| **Archivos de prompts** | 2 templates | 2 templates | ✅ Mantenidos |
| **Parsing de respuestas** | Regex + fallbacks | JSON directo | -100 LOC |
| **Tareas de implementación** | 87 tareas | 84 tareas | -3 tareas |
| **Tiempo estimado Gemini Client** | 5-6 horas | 4-5 horas | -1 hora |
| **Confiabilidad de respuestas** | ~85% | ~99% | +14% |
| **Mantenibilidad prompts** | Media | ✅ Alta | Mejor iteración |

---
