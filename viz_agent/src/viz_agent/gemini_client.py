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
        self.model = "gemini-2.5-flash"
        
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
        response_data = json.loads(response.text)
        correction = CodeCorrectionResponse(**response_data)
        return correction.corrected_code
    
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
