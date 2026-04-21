from typing import Any, Optional
from pydantic import BaseModel, Field

class ErrorResponse(BaseModel):
    """
    Representación estructurada de un error del backend.
    """
    error_type: str = Field(..., description="Identificador único del tipo de error (ej: sql_validation_error)")
    message: str = Field(..., description="Descripción del error apta para mostrar al usuario")
    context: Optional[dict[str, Any]] = Field(default_factory=dict, description="Metadatos adicionales para depuración")
