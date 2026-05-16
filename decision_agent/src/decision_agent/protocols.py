"""
protocols.py — Abstracciones Protocol para el Agente Decisor.

Define los contratos (interfaces) que deben cumplir los agentes subyacentes
(SQL y Visualización) para ser inyectados en el DecisionAgent, siguiendo
el Principio de Inversión de Dependencias.
"""

from typing import Any, Protocol, runtime_checkable

import pandas as pd

from decision_agent.models import DecisionAgentInput, DecisionAgentOutput


@runtime_checkable
class Text2SQLAgent(Protocol):
    """Protocolo para agentes de generación de SQL (ej. VannaAgent)."""

    async def text_to_sql(self, query: str, schema_context: str = "") -> Any:
        ...

    async def execute_sql(self, sql: str) -> pd.DataFrame:
        ...


@runtime_checkable
class VizAgentProtocol(Protocol):
    """Protocolo para agentes de visualización."""

    async def run(self, input_data: Any) -> Any:
        ...

    async def generate_visualization(self, input_data: Any) -> Any:
        ...


@runtime_checkable
class DecisionAgentProtocol(Protocol):
    """Protocolo para el agente decisor principal (exposición hacia la API)."""

    async def run(self, input_data: DecisionAgentInput) -> DecisionAgentOutput:
        ...
