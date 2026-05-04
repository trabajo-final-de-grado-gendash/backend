# viz_agent/agent.py

import time
import json
from typing import List, Optional
import pandas as pd
from .models import (
    VizAgentInput,
    VizAgentOutput,
    DataFrameMetadata,
    CorrectionRequest,
    ValidationResult,
)
from .analyzer import DataFrameAnalyzer
from .gemini_client import GeminiClient
from .validator import CodeValidator
from .logger import VizAgentLogger
from .config import Settings


class VizAgent:
    """Agente de visualización principal"""

    def __init__(self, config: Settings):
        self.config = config
        self.analyzer = DataFrameAnalyzer()
        self.gemini_client = GeminiClient(config=config)
        self.validator = CodeValidator()
        self.logger = VizAgentLogger(log_dir=config.VIZ_LOG_DIR)
        self.max_correction_attempts = config.MAX_CORRECT_ATTEMPTS

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_visualization(self, input_data: VizAgentInput) -> VizAgentOutput:
        """
        Genera una visualización completa a partir de un DataFrame y una consulta.

        Flow:
        1. Validar DataFrame
        2. Analizar DataFrame
        3. Llamar a Gemini para decisión + código inicial
        4. Ejecutar el código con loop de corrección (máx MAX_CORRECT_ATTEMPTS)
        5. Retornar VizAgentOutput con éxito o error
        """
        start_time = time.time()
        session_data = {
            "user_request": input_data.user_request,
            "dataframe_shape": input_data.dataframe.shape,
            "allowed_charts": input_data.allowed_charts,
            "corrections": [],
        }

        try:
            self.logger.log_request(input_data.user_request, input_data.dataframe.shape)

            # 1. Validar DataFrame
            is_valid, error_msg = self.analyzer.validate_dataframe(input_data.dataframe)
            if not is_valid:
                self.logger.log_error(f"Invalid DataFrame: {error_msg}")
                return VizAgentOutput(success=False, error_message=error_msg)

            # 2. Analizar DataFrame
            df_metadata = self.analyzer.analyze(input_data.dataframe)
            session_data["dataframe_metadata"] = df_metadata.model_dump()

            # 3. Decisión y generación de código (Gemini)
            gemini_response = self.gemini_client.decide_and_generate_code(
                user_request=input_data.user_request,
                df_metadata=df_metadata,
                allowed_charts=input_data.allowed_charts,
            )

            self.logger.log_decision(gemini_response.chart_type, gemini_response.reasoning)
            self.logger.log_code_generated(gemini_response.plotly_code)

            session_data["chart_type"] = gemini_response.chart_type
            session_data["reasoning"] = gemini_response.reasoning
            session_data["initial_code"] = gemini_response.plotly_code

            # 4 & 5. Ejecutar con loop de corrección
            final_code, validation_result, corrections = self._execute_with_correction_loop(
                initial_code=gemini_response.plotly_code,
                dataframe=input_data.dataframe,
                df_metadata=df_metadata,
            )
            session_data["corrections"] = corrections

            execution_time = time.time() - start_time

            if validation_result.success:
                plotly_json = json.loads(validation_result.figure.to_json())
                session_data["final_code"] = final_code
                session_data["attempts"] = len(corrections) + 1
                session_data["execution_time"] = execution_time

                self.logger.log_final_result(True, len(corrections) + 1, execution_time)
                self.logger.create_session_log(session_data)

                return VizAgentOutput(
                    success=True,
                    plotly_code=final_code,
                    plotly_json=plotly_json,
                    chart_type=gemini_response.chart_type,
                    metadata={
                        "attempts": len(corrections) + 1,
                        "decision_reasoning": gemini_response.reasoning,
                        "corrections_made": corrections,
                        "execution_time": execution_time,
                    },
                )

            # Todos los intentos fallaron
            self.logger.log_final_result(False, self.max_correction_attempts, execution_time)
            self.logger.create_session_log(session_data)

            return VizAgentOutput(
                success=False,
                error_message=(
                    f"Failed to generate valid code after {self.max_correction_attempts} "
                    f"attempts. Last error: {validation_result.error_message}"
                ),
                metadata={
                    "attempts": self.max_correction_attempts,
                    "corrections_made": corrections,
                    "execution_time": execution_time,
                    "last_code": final_code,
                },
            )

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Unexpected error: {str(e)}"
            self.logger.log_error(error_msg)
            return VizAgentOutput(
                success=False,
                error_message=error_msg,
                metadata={"execution_time": execution_time},
            )

    def modify_chart(
        self,
        plotly_code: str,
        dataframe: pd.DataFrame,
        user_prompt: str,
        conversation_history: Optional[List] = None,
    ) -> VizAgentOutput:
        """
        Modifica un gráfico existente según instrucciones del usuario.

        Toma el plotly_code guardado en BD, pide a Gemini que lo modifique
        según el prompt, ejecuta el código resultante con el DataFrame real
        y retorna el nuevo viz_json + plotly_code (siempre sincronizados).

        Args:
            plotly_code: Código Python Plotly del gráfico actual.
            dataframe: DataFrame obtenido re-ejecutando el SQL guardado en BD.
            user_prompt: Instrucción del usuario para modificar el gráfico.
            conversation_history: Historial de conversación para contexto adicional.
        """
        start_time = time.time()

        try:
            self.logger.log_request(f"[MODIFY] {user_prompt}", dataframe.shape)

            # 1. Analizar DataFrame — necesario antes de llamar a Gemini para
            #    que el prompt incluya los valores reales (columnas, únicos, etc.)
            df_metadata = self.analyzer.analyze(dataframe)

            # 2. Pedir a Gemini el código modificado
            modified_code, changes_description = self.gemini_client.modify_chart_code(
                plotly_code=plotly_code,
                user_prompt=user_prompt,
                df_metadata=df_metadata,
                conversation_history=conversation_history,
            )
            self.logger.log_code_generated(f"[MODIFY]\n{modified_code}")

            # 3. Ejecutar con loop de corrección
            final_code, validation_result, corrections = self._execute_with_correction_loop(
                initial_code=modified_code,
                dataframe=dataframe,
                df_metadata=df_metadata,
            )

            execution_time = time.time() - start_time

            if validation_result.success:
                plotly_json = json.loads(validation_result.figure.to_json())
                chart_type = (plotly_json.get("data") or [{}])[0].get("type")

                self.logger.log_final_result(True, len(corrections) + 1, execution_time)

                return VizAgentOutput(
                    success=True,
                    plotly_code=final_code,
                    plotly_json=plotly_json,
                    chart_type=chart_type,
                    metadata={
                        "modification_prompt": user_prompt,
                        "changes_description": changes_description,
                        "attempts": len(corrections) + 1,
                        "execution_time": execution_time,
                    },
                )

            self.logger.log_final_result(False, self.max_correction_attempts, execution_time)

            return VizAgentOutput(
                success=False,
                error_message=(
                    f"Failed to modify chart after {self.max_correction_attempts} "
                    f"attempts. Last error: {validation_result.error_message}"
                ),
                metadata={"execution_time": execution_time},
            )

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Chart modification failed: {str(e)}"
            self.logger.log_error(error_msg)
            return VizAgentOutput(
                success=False,
                error_message=error_msg,
                metadata={"execution_time": execution_time},
            )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _execute_with_correction_loop(
        self,
        initial_code: str,
        dataframe: pd.DataFrame,
        df_metadata: DataFrameMetadata,
    ) -> tuple[str, ValidationResult, list[dict]]:
        """
        Ejecuta `initial_code` y, si falla, pide correcciones a Gemini en un
        loop de hasta `max_correction_attempts` intentos.

        Returns:
            (final_code, last_validation_result, corrections_log)

        El caller decide qué hacer según `last_validation_result.success`.
        """
        current_code = initial_code
        corrections: list[dict] = []

        for attempt in range(1, self.max_correction_attempts + 1):
            validation_result = self.validator.execute_and_validate(
                code=current_code,
                dataframe=dataframe,
            )
            self.logger.log_validation_result(
                validation_result.success,
                validation_result.error_message,
            )

            if validation_result.success:
                return current_code, validation_result, corrections

            # Último intento — no intentar corregir más
            if attempt == self.max_correction_attempts:
                break

            self.logger.log_correction_attempt(attempt, validation_result.error_type)

            # Truncar mensaje de error para que Gemini no falle o se coma
            # los max output tokens generando un error interminable.
            raw_error = validation_result.error_message or "Unknown error"
            truncated_error = raw_error if len(raw_error) < 1000 else raw_error[:-1000] + "\n...[TRUNCATED_DUE_TO_LENGTH]"

            correction_request = CorrectionRequest(
                original_code=current_code,
                error_message=truncated_error,
                error_type=validation_result.error_type or "unknown",
                dataframe_metadata=df_metadata,
                attempt_number=attempt,
            )
            corrected_code = self.gemini_client.request_correction(correction_request)

            corrections.append({
                "attempt": attempt,
                "error_type": validation_result.error_type,
                "error_message": validation_result.error_message,
                "corrected_code": corrected_code,
            })

            current_code = corrected_code
            self.logger.log_code_generated(f"[CORRECTION {attempt}]\n{current_code}")

        return current_code, validation_result, corrections
