"""
agent.py — Agente decisor orquestador del pipeline de Gen BI.

Referencia: FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008
"""

from __future__ import annotations

import time
from typing import Any

from decision_agent.classifier import IntentClassifier
from decision_agent.config import Settings
from decision_agent.exceptions import PipelineError, SQLValidationError
from decision_agent.logger import get_logger
from decision_agent.models import (
    DecisionAgentInput,
    DecisionAgentOutput,
    IntentCategory,
    ResponseType,
)
from decision_agent.prompts.refinement_prompt import format_refinement_prompt
from decision_agent.sql_validator import SQLValidator
from decision_agent.protocols import Text2SQLAgent, VizAgentProtocol


class DecisionAgent:
    """
    Agente director del ecosistema Gen BI.

    Toma la entrada del usuario, clasifica, y si aplica orquesta:
    text2sql (Vanna) -> validation -> query DB -> viz (VizAgent)
    """

    def __init__(
        self,
        settings: Settings | None = None,
        text2sql_agent: Text2SQLAgent | None = None,
        viz_agent: VizAgentProtocol | None = None,
    ) -> None:
        """
        Inyectando dependencias externas. En entorno standalone creará
        instancias dummy o reales importándolas localmente si es necesario, 
        pero está preparado para recibir abstracciones (Protocol) desde la API.
        """
        self.settings = settings or Settings()  # type: ignore[call-arg]
        self.log = get_logger("decision_agent", stage="init")
        
        # 1. Intent Classifier
        self.classifier = IntentClassifier(
            api_key=self.settings.GEMINI_API_KEY,
            model_name=self.settings.GEMINI_MODEL,
        )
        # 2. SQL Validator
        self.sql_validator = SQLValidator()
        
        # 3. Agents inyectados o importados lazily (para evitar deps circulares si corre standalone)
        self.text2sql_agent = text2sql_agent
        self.viz_agent = viz_agent
        
        if self.text2sql_agent is None:
            self._try_load_vanna()
            
        if self.viz_agent is None:
            self._try_load_viz()

    def _try_load_vanna(self):
        try:
            from vanna_agent.agent import VannaAgent
            from vanna_agent.config import Settings as VannaSettings
            
            vanna_settings = VannaSettings(
                GEMINI_API_KEY=self.settings.GEMINI_API_KEY,
                SOURCE_DB_URL=self.settings.SOURCE_DB_URL,
            )
            self.text2sql_agent = VannaAgent(settings=vanna_settings)
        except ImportError:
            self.log.warning("vanna_agent_not_found_standalone")

    def _try_load_viz(self):
        try:
            from viz_agent.agent import VizAgent
            from viz_agent.config import Settings as VizSettings
            
            viz_config = VizSettings(
                GEMINI_API_KEY=self.settings.GEMINI_API_KEY,
            )
            self.viz_agent = VizAgent(config=viz_config)
        except ImportError:
            self.log.warning("viz_agent_not_found_standalone")

    def run(self, input_data: DecisionAgentInput) -> DecisionAgentOutput:
        """Entry point orquestador principal con timeout de 30s."""

        import concurrent.futures

        t_start = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self._run_internal, input_data)
            try:
                return future.result(timeout=30)

            except concurrent.futures.TimeoutError as exc:
                elapsed = int((time.perf_counter() - t_start) * 1000)
                self.log.error("decision_agent_timeout", error="timeout_exceeded", elapsed_ms=elapsed)
                raise PipelineError(
                    message="El pipeline excedió el límite de tiempo de 30 segundos (timeout).",

                    stage="timeout"
                ) from exc


    def _run_internal(self, input_data: DecisionAgentInput) -> DecisionAgentOutput:
        """Lógica original de orquestación."""
        t0 = time.perf_counter()
        session_id_str = str(input_data.session_id) if input_data.session_id else "No-Session"
        self.log = self.log.bind(session_id=session_id_str)
        
        query = input_data.query
        history = input_data.conversation_history
        self.log.info("decision_agent_run_started", query=query)

        metadata = {"attempts": 1}
        
        try:
            # 1. Clasificación
            intent = self.classifier.classify(query=query, conversation_history=history)
            
            # Enrutamiento según US2 (Fase 4 -> aunque preparamos la esctructura aquí para luego)
            if intent.category == IntentCategory.VALID_BUT_AMBIGUOUS:
                # T025: Guardia de máximo-una-clarificación consecutiva
                skip_clarification = False
                if history:
                    last_msg = history[-1]
                    from decision_agent.models import MessageRole
                    if last_msg.role == MessageRole.SYSTEM and getattr(last_msg, "response_type", None) == ResponseType.CLARIFICATION:
                        skip_clarification = True
                        self.log.info(
                            "max_clarification_reached_assuming_intent", 
                            suggested=intent.suggested_interpretations
                        )
                
                if not skip_clarification:
                    return DecisionAgentOutput(
                        response_type=ResponseType.CLARIFICATION,
                        message=intent.clarification_question or "¿Puedes ser más específico sobre la consulta?",
                        metadata=metadata,
                    )
                else:
                    # En caso de skipear clarificación, enriquecemos la metadata y procedemos como VALID_AND_CLEAR
                    metadata["clarification_skipped"] = True
                    intent.category = IntentCategory.VALID_AND_CLEAR

            if intent.category == IntentCategory.OUT_OF_SCOPE:
                return DecisionAgentOutput(
                    response_type=ResponseType.MESSAGE,
                    message="Lo siento, tu consulta se sale del alcance. Solo puedo realizar análisis de datos sobre la información proveída.",
                    metadata=metadata,
                )
            if intent.category == IntentCategory.CONVERSATIONAL:
                return DecisionAgentOutput(
                    response_type=ResponseType.MESSAGE,
                    message="¡Hola! Estoy listo para analizar tus datos.",
                    metadata=metadata,
                )

            # --- RUTA PRINCIPAL (VALID_AND_CLEAR) ---
            if not self.text2sql_agent or not self.viz_agent:
                raise PipelineError("Faltan agentes inyectados en runtime para ejecución del pipeline.")

            # Si Gemini resolvió una query auto-contenida desde el contexto, usarla.
            # De lo contrario, usar la query original del usuario.
            effective_query = intent.resolved_query or query
            if intent.resolved_query:
                self.log.info(
                    "query_resolved_from_context",
                    original=query,
                    resolved=intent.resolved_query,
                )

            return self._execute_data_pipeline(effective_query, metadata)


        except Exception as e:
            elapsed = time.perf_counter() - t0
            self.log.error("decision_agent_failed", error=str(e), elapsed_ms=int(elapsed * 1000))
            if isinstance(e, SQLValidationError):
                raise
            raise PipelineError(f"DecisionAgent falló con error: {e}") from e

    def _execute_data_pipeline(self, query: str, metadata: dict[str, Any]) -> DecisionAgentOutput:
        """Sub-workflow para queries analíticas válidas: Vanna -> Validator -> DB -> Viz"""
        
        # 1. Text2SQL (Intento inicial)
        t_sql = time.perf_counter()
        t2s_output = self.text2sql_agent.text_to_sql(query)
        sql = t2s_output.sql
        
        if not t2s_output.success or not sql:
            # Fallo inicial en generacion
            self.log.warning("initial_text2sql_failed", error=t2s_output.error)
            # Podríamos reintentar inmediatamnte con la query sola, pero Vanna no arrojó SQL.
            raise PipelineError(f"Vanna falló en generación inicial: {t2s_output.error}")

        # Retrying block (FR-003: 1 reintento con reformulación)
        df_result = None
        current_sql = sql
        execution_error = None
        
        for attempt in range(1, 3):  # Max 2 intentos (1 original + 1 retry)
            metadata["attempts"] = attempt
            
            try:
                # 2. SQL Validator
                self.log.debug("validating_sql", attempt=attempt, sql=current_sql)
                self.sql_validator.validate(current_sql)
                
                # 3. DB Execution
                self.log.info("executing_sql", attempt=attempt)
                df_result = self.text2sql_agent.execute_sql(current_sql)
                execution_error = None
                break  # Éxito! Salir del loop de reintentos
                
            except Exception as e:
                execution_error = str(e)
                self.log.warning("pipeline_execution_failed", attempt=attempt, error=execution_error)
                
                # Si estamos en el último intento o es un SQLValidationError irreparable
                if isinstance(e, SQLValidationError):
                    raise
                if attempt == 2:
                    raise PipelineError(f"Fallo final luego de {attempt} intentos: {e}", stage="execute_sql") from e
                
                # 4. Reformular query usando refinement prompt
                self.log.info("triggering_sql_refinement", failed_sql=current_sql)
                refined_query = format_refinement_prompt(query=query, sql=current_sql, error=execution_error)
                
                # Re-invocar Vanna con sugerencia de contexto
                retry_output = self.text2sql_agent.text_to_sql(refined_query)
                if not retry_output.success or not retry_output.sql:
                    raise PipelineError("Vanna falló en retry con query reformulada.", stage="text_to_sql")
                
                current_sql = retry_output.sql

        if df_result is None or df_result.empty:
            # T022: DataFrame vacío -> no llamar a viz_agent, retornar mje directo
            self.log.info("empty_dataframe_returned")
            return DecisionAgentOutput(
                response_type=ResponseType.MESSAGE,
                message="La consulta se ejecutó de forma correcta, pero no arrojó datos para el registro especificado.",
                sql=current_sql,
                metadata=metadata,
            )

        # 5. Viz Agent
        self.log.info("invoking_viz_agent", records_len=len(df_result))
        
        try:
            from viz_agent.models import VizAgentInput
            viz_input = VizAgentInput(dataframe=df_result, user_request=query)
            
            # En duck_typing o protocol, asume generate_visualization
            if hasattr(self.viz_agent, "generate_visualization"):
                viz_output = self.viz_agent.generate_visualization(viz_input)
            else:
                viz_output = self.viz_agent.run(viz_input)
            
            if not viz_output.success:
                raise PipelineError(f"VizAgent dictaminó fallo en la visualización: {viz_output.error_message}", stage="viz_agent")
                
            self.log.info("visualization_generated_successfully")
            return DecisionAgentOutput(
                response_type=ResponseType.VISUALIZATION,
                message=None,
                sql=current_sql,
                viz_result=viz_output,
                metadata=metadata,
            )
        except Exception as e:
            self.log.error("viz_agent_invocation_failed", error=str(e))
            raise PipelineError(f"Fallo al invocar Viz Agent: {e}", stage="viz_agent") from e
