"""
exceptions.py — Jerarquía de excepciones compartida del decision_agent.

Todas las excepciones extienden AgentError para permitir un manejo
centralizado con campos estructurados de diagnóstico.

Referencia: plan.md §Detalle de Componentes, FR-004, FR-007
"""

from __future__ import annotations

from typing import Any


class AgentError(Exception):
    """
    Excepción base del agente decisor.

    Attributes:
        error_type: Identificador del tipo de error (snake_case).
        message:    Descripción legible por humanos.
        context:    Datos adicionales de diagnóstico (query, sql, stage…).
    """

    def __init__(
        self,
        error_type: str,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.message = message
        self.context: dict[str, Any] = context or {}

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"error_type={self.error_type!r}, "
            f"message={self.message!r}, "
            f"context={self.context!r})"
        )

    def to_dict(self) -> dict[str, Any]:
        """Serializa la excepción al formato JSON de error de la API."""
        return {
            "error_type": self.error_type,
            "message": self.message,
            "context": self.context,
        }


class LLMError(AgentError):
    """
    Error al interactuar con el LLM (Gemini).

    Se lanza cuando la llamada al modelo falla, el timeout se supera
    o la respuesta no puede parsearse como structured output.
    """

    def __init__(
        self,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(error_type="llm_error", message=message, context=context)


class SQLValidationError(AgentError):
    """
    Error de validación de SQL bloqueado por el SQLValidator.

    Se lanza cuando el SQL generado por Vanna contiene statements
    distintos de SELECT (DELETE, DROP, UPDATE, INSERT, etc.).

    FR-004, FR-024, NFR-007
    """

    def __init__(
        self,
        message: str,
        sql: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        ctx = context or {}
        if sql:
            ctx["sql"] = sql
        super().__init__(
            error_type="sql_validation_error",
            message=message,
            context=ctx,
        )


class PipelineError(AgentError):
    """
    Error a nivel del pipeline de orquestación.

    Se lanza ante fallos inesperados durante la ejecución del pipeline
    completo (timeout, fallo del viz_agent, fallo de ejecución de SQL, etc.).
    """

    def __init__(
        self,
        message: str,
        stage: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        ctx = context or {}
        if stage:
            ctx["stage"] = stage
        super().__init__(
            error_type="pipeline_error",
            message=message,
            context=ctx,
        )
