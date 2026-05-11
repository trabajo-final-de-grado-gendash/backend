# viz_agent/gemini_client.py

from google import genai
from google.genai import types
from langsmith import traceable, wrappers
from typing import List, Optional
from .models import (
    DataFrameMetadata,
    GeminiResponse,
    CorrectionRequest,
    CodeCorrectionResponse,
    ChartModificationResponse,
)
from .prompts.decision_prompt import DECISION_PROMPT_TEMPLATE
from .prompts.correction_prompt import CORRECTION_PROMPT_TEMPLATE
from .prompts.modification_prompt import MODIFICATION_PROMPT_TEMPLATE
import json
from .config import Settings
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception

def is_503_error(e: BaseException) -> bool:
    return "503 unavailable" in str(e).lower() or "503 unavailable" in repr(e).lower()


class GeminiClient:
    """Cliente para interactuar con Gemini usando el modelo configurado"""
    
    def __init__(self, config: Settings):
        self.client = wrappers.wrap_gemini(genai.Client(api_key=config.GEMINI_API_KEY))
        self.model = config.GEMINI_MODEL
        
        # Configuración base de generación
        self.base_config = {
            "temperature": 0.2,  # Baja temperatura para consistencia
            "top_p": 0.8,
            "top_k": 40,
            "max_output_tokens": 8192,
        }
    
    @traceable(name="VizAgent.decide_and_generate", run_type="chain")
    @retry(stop=stop_after_attempt(4), wait=wait_fixed(3), retry=retry_if_exception(is_503_error), reraise=True)
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
            unique_values=json.dumps(df_metadata.unique_values, indent=2),
            allowed_charts=", ".join(allowed_charts)
        )
        
        # Generar schema desde Pydantic y limpiar additionalProperties
        schema = GeminiResponse.model_json_schema()
        schema = self._clean_schema(schema)
        
        # Configurar schema usando JSON Schema limpio
        config = types.GenerateContentConfig(
            **self.base_config,
            response_mime_type="application/json",
            response_schema=schema,
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
    
    @traceable(name="VizAgent.request_correction", run_type="chain")
    @retry(stop=stop_after_attempt(4), wait=wait_fixed(3), retry=retry_if_exception(is_503_error), reraise=True)
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
        
        # Generar schema desde Pydantic y limpiar additionalProperties
        schema = CodeCorrectionResponse.model_json_schema()
        schema = self._clean_schema(schema)
        
        # Configurar schema para corrección
        config = types.GenerateContentConfig(
            **self.base_config,
            response_mime_type="application/json",
            response_schema=schema,
        )
        
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config
        )
        
        # Parsear y retornar solo el código corregido
        try:
            response_data = json.loads(response.text)
        except json.JSONDecodeError as e:
            finish_reason = getattr(response.candidates[0], "finish_reason", "UNKNOWN") if response.candidates else "NO_CANDIDATES"
            raise ValueError(
                f"Gemini returned invalid JSON (truncated? finish_reason: {finish_reason}). Error: {e}\nRaw text:\n{response.text}"
            ) from e
        correction = CodeCorrectionResponse(**response_data)
        return correction.corrected_code

    @traceable(name="VizAgent.modify_chart", run_type="chain")
    @retry(stop=stop_after_attempt(4), wait=wait_fixed(3), retry=retry_if_exception(is_503_error), reraise=True)
    def modify_chart_code(
        self,
        plotly_code: str,
        user_prompt: str,
        df_metadata: "DataFrameMetadata",
        conversation_history: Optional[List] = None,
    ) -> tuple[str, str]:
        """
        Modifica el código Python Plotly de un gráfico según instrucciones del usuario.

        Envía el código actual + metadata del DataFrame + prompt a Gemini y
        recibe el código modificado.

        Args:
            conversation_history: Lista de ConversationContext con el historial
                                  de la sesión (últimos N mensajes).

        Returns:
            Tupla (modified_code, changes_description)
        """
        # Serializar historial a texto legible para el prompt
        history_text = "(No prior conversation context)"
        if conversation_history:
            lines = []
            for msg in conversation_history:
                role_label = msg.role.value.upper() if hasattr(msg.role, "value") else str(msg.role).upper()
                lines.append(f"{role_label}: {msg.content}")
            history_text = "\n".join(lines)

        prompt = MODIFICATION_PROMPT_TEMPLATE.format(
            plotly_code=plotly_code,
            user_prompt=user_prompt,
            df_shape=df_metadata.shape,
            columns=", ".join(df_metadata.columns),
            numeric_columns=", ".join(df_metadata.numeric_columns),
            categorical_columns=", ".join(df_metadata.categorical_columns),
            datetime_columns=", ".join(df_metadata.datetime_columns),
            sample_values=json.dumps(df_metadata.sample_values, indent=2),
            unique_counts=json.dumps(df_metadata.unique_counts, indent=2),
            unique_values=json.dumps(df_metadata.unique_values, indent=2),
            conversation_history=history_text,
        )

        schema = ChartModificationResponse.model_json_schema()
        schema = self._clean_schema(schema)

        config = types.GenerateContentConfig(
            **self.base_config,
            response_mime_type="application/json",
            response_schema=schema,
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )

        # Parsear y retornar el código modificado
        try:
            response_data = json.loads(response.text)
        except json.JSONDecodeError as e:
            # Inspeccionar por qué terminó la respuesta
            finish_reason = getattr(response.candidates[0], "finish_reason", "UNKNOWN") if response.candidates else "NO_CANDIDATES"
            
            # Si el JSON es inválido, soltar un error más claro con el texto parcial
            raise ValueError(
                f"Gemini returned invalid JSON (truncated? finish_reason: {finish_reason}). Error: {e}\nRaw text:\n{response.text}"
            ) from e
        modification = ChartModificationResponse(**response_data)
        return modification.modified_code, modification.changes_description


    def _clean_schema(self, schema: dict) -> dict:
        """
        Limpia el JSON Schema para que sea compatible con Gemini API.
        Remueve 'additionalProperties' y otros campos no soportados.
        """
        if isinstance(schema, dict):
            # Remover additionalProperties recursivamente
            schema.pop('additionalProperties', None)
            schema.pop('$defs', None)  # También remover definiciones extras
            
            # Limpiar recursivamente
            for key, value in schema.items():
                if isinstance(value, dict):
                    schema[key] = self._clean_schema(value)
                elif isinstance(value, list):
                    schema[key] = [self._clean_schema(item) if isinstance(item, dict) else item for item in value]
        
        return schema
