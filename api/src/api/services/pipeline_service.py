"""
pipeline_service.py — Puente entre la API REST y los Agentes Subyacentes.

Referencia: plan.md §API §services, FR-013
"""

import uuid
from typing import Any

from fastapi import HTTPException

from decision_agent.models import DecisionAgentInput, DecisionAgentOutput
from decision_agent.agent import DecisionAgent
from decision_agent.exceptions import PipelineError, SQLValidationError

# Lazy initialization of the agent instance
_decision_agent_instance: DecisionAgent | None = None

def get_decision_agent() -> DecisionAgent:
    global _decision_agent_instance
    if _decision_agent_instance is None:
        try:
            from vanna_agent.agent import VannaAgent
            
            # Since viz_agent is just a mock for now, we'll try to load it or mock it
            try:
                from viz_agent.agent import VizAgent
                viz_agent = VizAgent()
            except ImportError:
                class MockVizAgent:
                    def generate_visualization(self, input_data: Any) -> Any:
                        class Output:
                            success = True
                            plotly_json = {"data": [], "layout": {}}
                            plotly_code = ""
                        return Output()
                viz_agent = MockVizAgent()
            
            vanna_agent = VannaAgent()
            
            _decision_agent_instance = DecisionAgent(
                text2sql_agent=vanna_agent,
                viz_agent=viz_agent
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize agents for PipelineService: {e}") from e
    return _decision_agent_instance

class PipelineService:
    """
    Servicio inyectable que encapsula el orquestador del pipeline.
    """
    def __init__(self):
        self.decision_agent = get_decision_agent()

    def run(
        self,
        query: str,
        session_id: uuid.UUID | None = None,
        conversation_history: list[Any] | None = None
    ) -> DecisionAgentOutput:
        """
        Ejecuta el pipeline orquestando de forma centralizada con el DecisionAgent,
        y mapea los errores a excepciones HTTP de FastAPI.
        """
        input_data = DecisionAgentInput(
            query=query,
            session_id=session_id,
            conversation_history=conversation_history or []
        )
        
        try:
            return self.decision_agent.run(input_data)
        except (SQLValidationError, PipelineError):
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail={"error_type": "InternalServerError", "message": "Unexpected error", "context": {"details": str(e)}}
            ) from e
