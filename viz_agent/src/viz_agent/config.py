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
