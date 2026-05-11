"""
classifier.py — Clasificador de intenciones con google-genai structured output.

Clasifica las consultas del usuario en cuatro categorías manejando historial de chat,
devolviendo un modelo IntentClassification tipado y seguro.

Referencia: FR-002, FR-014
"""

from __future__ import annotations

import structlog
from google import genai
from google.genai import types
from langsmith import traceable, wrappers

from decision_agent.exceptions import LLMError
from decision_agent.logger import get_logger
from decision_agent.models import ConversationContext, IntentClassification
from decision_agent.prompts.classification_prompt import CLASSIFICATION_SYSTEM_PROMPT
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception

def is_503_error(e: BaseException) -> bool:
    return "503 unavailable" in str(e).lower() or "503 unavailable" in repr(e).lower()


class IntentClassifier:
    """Clasificador de intención del usuario usando Gemini Structured Outputs."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-2.5-flash",
        logger: structlog.stdlib.BoundLogger | None = None,
    ) -> None:
        self.model_name = model_name
        self._client = wrappers.wrap_gemini(genai.Client(api_key=api_key))
        self.log = logger or get_logger("decision_agent", stage="classify")

    @traceable(name="DecisionAgent.classify", run_type="chain")
    @retry(stop=stop_after_attempt(4), wait=wait_fixed(3), retry=retry_if_exception(is_503_error), reraise=True)
    def classify(
        self,
        query: str,
        conversation_history: list[ConversationContext] | None = None,
    ) -> IntentClassification:
        """
        Analiza el query contra el historial y retorna una de las 4 intenciones.

        Args:
            query: La consulta en lenguaje natural (ej. "dame ventas por género").
            conversation_history: Últimos 5 mensajes del contexto de sesión.

        Returns:
            IntentClassification validado con Pydantic.

        Raises:
            LLMError si el modelo falla o retorna un JSON malformado.
        """
        history = conversation_history or []
        self.log.info("classifying_intent", query=query, history_len=len(history))

        # Reconstruir el historial en texto para inyectarlo en el system prompt
        history_lines = [f"{msg.role.value.capitalize()}: {msg.content}" for msg in history]
        history_str = "\n".join(history_lines) if history_lines else "(Sin historial previo)"
        
        system_instruction = CLASSIFICATION_SYSTEM_PROMPT.format(
            conversation_history=history_str
        )
        prompt = f"Consulta del usuario para clasificar: {query}"

        try:
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=IntentClassification,
                    temperature=0.0,
                ),
            )

            result = response.parsed
            if not result or not isinstance(result, IntentClassification):
                raise LLMError("Gemini no retornó un struct output válido para IntentClassification.")

            self.log.info(
                "intent_classified",
                category=result.category.value,
                reasoning=result.reasoning,
            )
            return result

        except LLMError:
            raise
        except Exception as e:
            self.log.error("llm_classification_failed", error=str(e), type=type(e).__name__)
            raise LLMError(f"Fallo al invocar API de Gemini: {e}", context={"query": query}) from e
