# viz_agent/logger.py

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


class VizAgentLogger:
    """Sistema de logging para el agente de visualización"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Configurar logger de Python
        self.logger = logging.getLogger("VizAgent")
        self.logger.setLevel(logging.DEBUG)
        
        # Limpiar handlers existentes para evitar duplicados
        self.logger.handlers.clear()
        
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
