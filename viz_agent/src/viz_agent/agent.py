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
        
        self.max_correction_attempts = config.max_correction_attempts
    
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
