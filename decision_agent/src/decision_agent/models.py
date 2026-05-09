"""
models.py — Modelos Pydantic del agente decisor.

Referencia: data-model.md §Decision Agent Models
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ResponseType(str, Enum):
    VISUALIZATION = "visualization"
    CLARIFICATION = "clarification"
    MESSAGE = "message"


class IntentCategory(str, Enum):
    VALID_AND_CLEAR = "valid_and_clear"
    VALID_BUT_AMBIGUOUS = "valid_but_ambiguous"
    OUT_OF_SCOPE = "out_of_scope"
    CONVERSATIONAL = "conversational"


class MessageRole(str, Enum):
    USER = "user"
    SYSTEM = "system"


class ConversationContext(BaseModel):
    """Mensaje de contexto conversacional pasado al agente."""

    role: MessageRole
    content: str
    response_type: Optional[ResponseType] = None


class DecisionAgentInput(BaseModel):
    """Input para el agente decisor."""

    query: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[uuid.UUID] = None
    conversation_history: list[ConversationContext] = Field(default_factory=list)
    cached_sql: Optional[str] = None


class IntentClassification(BaseModel):
    """
    Resultado de clasificación de intención (structured output de Gemini).

    Este modelo se usa directamente con google-genai response_schema.
    """

    category: IntentCategory
    reasoning: str
    clarification_question: Optional[str] = None
    suggested_interpretations: list[str] = Field(default_factory=list)
    resolved_query: Optional[str] = Field(
        default=None,
        description=(
            "Query reformulada y auto-contenida para usar en lugar de la original. "
            "Solo se rellena cuando category=valid_and_clear y la query del usuario "
            "depende de mensajes anteriores para ser interpretada correctamente. "
            "Si la query original ya es auto-contenida, este campo es None."
        ),
    )



class DecisionAgentOutput(BaseModel):
    """Output del agente decisor."""

    response_type: ResponseType
    message: Optional[str] = None
    sql: Optional[str] = None
    # viz_result se tipea como Any para evitar una dependencia circular con viz_agent
    viz_result: Optional[Any] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
