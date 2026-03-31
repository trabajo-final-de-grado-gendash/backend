"""
models/schemas.py — Schemas Pydantic de request/response para la API REST.

Referencia: data-model.md §Pydantic Models (Application Layer), contracts/api-v1.md
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from decision_agent.models import IntentCategory, MessageRole, ResponseType

# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class GenerateRequest(BaseModel):
    """Request al endpoint POST /api/v1/generate."""

    query: str = Field(..., min_length=1, max_length=2000, description="Consulta en lenguaje natural")
    session_id: Optional[uuid.UUID] = Field(
        None,
        description="ID de sesión existente. Si se omite, se genera automáticamente.",
    )


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class GenerateResponse(BaseModel):
    """Response del endpoint POST /api/v1/generate."""

    response_type: ResponseType
    session_id: uuid.UUID
    result_id: Optional[uuid.UUID] = None
    message: Optional[str] = None
    plotly_json: Optional[dict[str, Any]] = None
    sql: Optional[str] = None
    plotly_code: Optional[str] = None
    chart_type: Optional[str] = None


class ComponentHealth(BaseModel):
    """Estado de un componente del sistema."""

    status: str  # "up" | "down"
    latency_ms: Optional[float] = None


class HealthResponse(BaseModel):
    """Response del endpoint GET /api/v1/health."""

    status: str  # "healthy" | "degraded" | "unhealthy"
    components: dict[str, ComponentHealth]


class MessageItem(BaseModel):
    """Mensaje individual en el historial de sesión."""

    role: MessageRole
    content: str
    response_type: Optional[ResponseType] = None
    timestamp: datetime


class SessionHistoryResponse(BaseModel):
    """Response del endpoint GET /api/v1/sessions/{session_id}/history."""

    session_id: uuid.UUID
    messages: list[MessageItem]


class ResultResponse(BaseModel):
    """Response del endpoint GET /api/v1/results/{result_id}."""

    result_id: uuid.UUID
    query: str
    sql: str
    plotly_json: dict[str, Any]
    plotly_code: Optional[str] = None
    chart_type: Optional[str] = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Error response (unified format)
# ---------------------------------------------------------------------------


class ErrorResponse(BaseModel):
    """Cuerpo de respuesta de error estructurado."""

    error_type: str
    message: str
    context: dict[str, Any] = Field(default_factory=dict)
