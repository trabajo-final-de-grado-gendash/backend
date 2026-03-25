"""
models.py — Modelos Pydantic del vanna_agent.

Referencia: plan.md §Vanna Agent
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class Text2SQLInput(BaseModel):
    """Input para la operación text_to_sql del VannaAgent."""

    query: str


class Text2SQLOutput(BaseModel):
    """
    Output de la operación text_to_sql del VannaAgent.

    En caso de éxito: success=True, sql contiene el SELECT generado.
    En caso de fallo: success=False, error describe el problema.
    """

    sql: Optional[str] = None
    query: Optional[str] = None  # Reflejo de la query original
    success: bool
    error: Optional[str] = None
