# Tasks: Agente Decisor y API de Orquestación para Gen BI

**Feature**: TFG-13 — Agente Decisor y API de Orquestación para Gen BI
**Branch**: `TFG-13-crear-agente-decisor`
**Generado**: 2026-03-23
**Documentos fuente**: spec.md, plan.md, data-model.md, contracts/api-v1.md, quickstart.md

---

## Estrategia de implementación

**Alcance MVP**: Fase 3 (US1 — pipeline end-to-end).  
Orden de ejecución: Fase 1 → Fase 2 → Fase 3 (US1) → Fase 4 (US2) → Fase 5 (US3 API) → Fase 6 (US4 Wrapper) → Fase 7 (US5 Persistencia) → Fase 8 (US6 Historial) → Fase 9 (Polish).  
Las historias 3, 5 y 6 comparten el módulo `api/`; US4 (orchestrator) debe completarse antes de que US3 pueda conectarse vía `pipeline_service`.

---

## Dependencias

```
Fase 1 (Setup)
  └── Fase 2 (Foundational: DB engine, modelos base, jerarquía de excepciones, logging)
        ├── Fase 3: US1 — Pipeline end-to-end (núcleo decision_agent + vanna_agent)
        │     └── Fase 4: US2 — Routing inteligente (extiende decision_agent)
        ├── Fase 5: US3 — API REST (requiere orchestrator de Fase 6)
        ├── Fase 6: US4 — Orchestrator/Wrapper (requiere agentes de Fase 3)
        ├── Fase 7: US5 — Persistencia de resultados (requiere DB y API de Fase 5)
        └── Fase 8: US6 — Historial conversacional (requiere DB, API y modelo de sesión)
Fase 9 (Polish): luego de todas las historias de usuario
```

---

## Fase 1 — Setup

> Objetivo: Inicializar todas las estructuras de paquetes para que cada fase siguiente pueda importar y testear de forma independiente.

- [ ] T001 Crear la estructura del paquete `decision_agent/` con `pyproject.toml`, `src/decision_agent/__init__.py`, `tests/__init__.py`, `tests/conftest.py`, `examples/basic_usage.py` y `.env.example` según plan.md §Estructura del Proyecto
- [ ] T002 Crear la estructura del paquete `vanna_agent/` con `pyproject.toml`, `src/vanna_agent/__init__.py`, `tests/__init__.py`, `tests/conftest.py`, `examples/basic_usage.py` y `.env.example` según plan.md §Estructura del Proyecto
- [ ] T003 Crear el módulo `orchestrator/` con `__init__.py`, `protocols.py`, `pipeline.py`, `exceptions.py` según plan.md §Estructura del Proyecto
- [ ] T004 Crear la estructura del paquete `api/` con `pyproject.toml`, `src/api/__init__.py`, `alembic/`, `alembic/env.py`, `alembic/versions/`, `tests/__init__.py`, `tests/conftest.py` y `.env.example` según plan.md §Estructura del Proyecto

---

## Fase 2 — Foundational (prerequisitos bloqueantes)

> Objetivo: Infraestructura compartida de la que dependen todas las fases de historias de usuario. Debe completarse antes de cualquier trabajo de historia.

- [ ] T005 Implementar la jerarquía de excepciones compartida en `decision_agent/src/decision_agent/exceptions.py`: `AgentError`, `LLMError`, `SQLValidationError`, `PipelineError` con campos `error_type`, `message`, `context` (plan.md §Detalle de Componentes, FR-004, FR-007)
- [ ] T006 Implementar la configuración de logging estructurado en `decision_agent/src/decision_agent/logger.py` usando `structlog`; configurar salida JSON con campos `stage`, `agent` y `elapsed_ms` (FR-008, NFR-003)
- [ ] T007 [P] Implementar `decision_agent/src/decision_agent/config.py` con `Pydantic BaseSettings`: `GEMINI_API_KEY`, `CHINOOK_DB_URL`, `DATABASE_URL`, `CONTEXT_WINDOW_SIZE=5` (plan.md §Contexto Técnico)
- [ ] T008 [P] Implementar `vanna_agent/src/vanna_agent/config.py` con `Pydantic BaseSettings`: `GEMINI_API_KEY`, `GEMINI_MODEL` (default: `gemini-2.5-pro`) y `CHINOOK_DB_URL` (connection string PostgreSQL); dependencia de instalación: `vanna[gemini,postgres]` (vanna.ai/docs/configure/gemini/postgres)
- [ ] T009 [P] Implementar `api/src/api/config.py` con `Pydantic BaseSettings`: `DATABASE_URL`, `CORS_ORIGINS`, `CONTEXT_WINDOW_SIZE=5` (plan.md §API)
- [ ] T010 Implementar el async engine de SQLAlchemy y la session factory en `api/src/api/db/engine.py` y `api/src/api/db/base.py` usando `asyncpg`; base declarativa para modelos ORM (data-model.md §Configuración de Base de Datos)
- [ ] T011 Implementar los modelos ORM de SQLAlchemy en `api/src/api/models/database.py`: `Session`, `ConversationMessage`, `GenerationResult` con todos los campos y relaciones FK según data-model.md
- [ ] T012 Crear la migración inicial de Alembic en `api/alembic/versions/001_initial_schema.py` con las tablas `sessions`, `conversation_messages`, `generation_results` incluyendo índices sobre `session_id` y `created_at` (data-model.md §Configuración de Base de Datos)
- [ ] T013 Implementar todos los schemas Pydantic de request/response en `api/src/api/models/schemas.py`: `GenerateRequest`, `GenerateResponse`, `HealthResponse`, `ComponentHealth`, `SessionHistoryResponse`, `MessageItem`, `ResultResponse`; y los enums compartidos `ResponseType`, `IntentCategory`, `MessageRole` (data-model.md §Modelos Pydantic)
- [ ] T014 Implementar los modelos Pydantic en `decision_agent/src/decision_agent/models.py`: `DecisionAgentInput`, `ConversationContext`, `IntentClassification`, `DecisionAgentOutput` (data-model.md §Modelos del Agente Decisor)
- [ ] T015 [P] Implementar los modelos Pydantic en `vanna_agent/src/vanna_agent/models.py`: `Text2SQLInput`, `Text2SQLOutput` con campos `sql`, `query`, `success`, `error` (plan.md §Vanna Agent)

---

## Fase 3 — Historia de Usuario 1: Generación de Visualización End-to-End (P1)

> Objetivo: El agente decisor orquesta el pipeline completo: consulta NL → SQL (Vanna) → validar → ejecutar → viz_agent → Plotly JSON.  
> Test independiente: Llamar a `DecisionAgent.run()` con una consulta sobre Chinook y verificar que retorna un `DecisionAgentOutput` válido con `response_type=visualization`.

- [ ] T016 [US1] Implementar `decision_agent/src/decision_agent/prompts/classification_prompt.py`: templates de prompt de sistema y usuario para clasificación de intención con las cuatro categorías (`valid_and_clear`, `valid_but_ambiguous`, `out_of_scope`, `conversational`) incluyendo inyección de `conversation_history` (FR-014)
- [ ] T017 [US1] Implementar `decision_agent/src/decision_agent/prompts/refinement_prompt.py`: template de prompt para reformulación del retry de SQL con contexto adicional (FR-003)
- [ ] T018 [US1] Implementar `decision_agent/src/decision_agent/classifier.py`: clase `IntentClassifier` usando structured output de `google-genai` retornando `IntentClassification`; incluir manejo de errores del LLM → lanzar `LLMError` (FR-002, FR-014)
- [ ] T019 [US1] Implementar `decision_agent/src/decision_agent/sql_validator.py`: clase `SQLValidator` usando `sqlparse`; allowlist solo `SELECT`; bloquear `DELETE`, `DROP`, `UPDATE`, `INSERT`, `ALTER`, `TRUNCATE`, `CREATE`, `REPLACE`; registrar intentos bloqueados en log; lanzar `SQLValidationError` (FR-004, FR-024, NFR-007)
- [ ] T020 [US1] Implementar `vanna_agent/src/vanna_agent/agent.py`: clase `VannaAgent` usando la nueva API de Vanna v2 (`from vanna.integrations.google import GeminiLlmService`; `from vanna.integrations.postgres import PostgresRunner`; `from vanna.tools import RunSqlTool`); instanciar `GeminiLlmService(model=..., api_key=...)` y `RunSqlTool(sql_runner=PostgresRunner(connection_string=...))` desde config; métodos públicos `text_to_sql(query: str) -> Text2SQLOutput` y `execute_sql(sql: str) -> pd.DataFrame` que deleguen al `RunSqlTool`; envolver en try/except → retornar `Text2SQLOutput(success=False, error=...)` en caso de fallo (FR-003, vanna.ai/docs/configure/gemini/postgres)
- [ ] T021 [US1] Implementar `decision_agent/src/decision_agent/agent.py`: `DecisionAgent.run(input: DecisionAgentInput) -> DecisionAgentOutput` orquestando: (1) clasificar intención, (2) si `valid_and_clear` → llamar a VannaAgent, (3) validar SQL, (4) ejecutar SQL, (5) llamar a viz_agent, (6) retornar output; incluir lógica de 1 reintento reformulando con `refinement_prompt` ante fallo de Vanna; logging estructurado en cada etapa (FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008)
- [ ] T022 [US1] Implementar el manejo de DataFrame vacío en `decision_agent/src/decision_agent/agent.py`: cuando `execute_sql` retorna un DataFrame vacío, retornar `DecisionAgentOutput(response_type=ResponseType.MESSAGE, message="La consulta no produjo datos...")` sin invocar viz_agent (spec.md §Edge Cases)
- [ ] T023 [US1] Implementar `decision_agent/examples/basic_usage.py`: smoke test de consola que instancia `DecisionAgent` y ejecuta la consulta de ejemplo `"total de ventas por género de cliente"` imprimiendo cada etapa y el tiempo total transcurrido (quickstart.md §Ejecutar el Agente Decisor)

---

## Fase 4 — Historia de Usuario 2: Decisión Inteligente de Flujo (P2)

> Objetivo: El agente decisor enruta correctamente las 4 categorías de intención; el flujo de clarificación funciona entre turnos.  
> Test independiente: Enviar consultas fuera de alcance, ambiguas y conversacionales a `DecisionAgent.run()` y verificar el `response_type` y `message` correctos en cada caso.

- [ ] T024 [US2] Extender `decision_agent/src/decision_agent/agent.py`: agregar ramas de routing para `valid_but_ambiguous` → retornar `DecisionAgentOutput(response_type=ResponseType.CLARIFICATION, message=<clarification_question>)`; para `out_of_scope` → retornar `DecisionAgentOutput(response_type=ResponseType.MESSAGE, message=<scope_explanation>)`; para `conversational` → retornar `DecisionAgentOutput(response_type=ResponseType.MESSAGE, message=<friendly_reply>)` (FR-014, spec.md US2 escenarios de aceptación)
- [ ] T025 [US2] Agregar guardia de máximo-una-clarificación en `decision_agent/src/decision_agent/agent.py`: inspeccionar `conversation_history` y si el mensaje anterior del sistema fue `response_type=clarification` para el mismo contexto, proceder con la interpretación más razonable en lugar de preguntar de nuevo; registrar la asunción en log (FR-014 punto 2)
- [ ] T026 [US2] Actualizar `decision_agent/src/decision_agent/prompts/classification_prompt.py` con instrucciones explícitas para detección de múltiples intenciones y descripción del límite de alcance del sistema según spec.md FR-014 y escenarios de aceptación US2

---

## Fase 5 — Historia de Usuario 3: API REST para Exposición del Pipeline (P2)

> Objetivo: Aplicación FastAPI con endpoints `/generate`, `/health`, `/sessions/{id}/history`, `/results/{id}` funcionando end-to-end.  
> Test independiente: Usar `curl` o llamadas HTTP con pytest para verificar que todos los endpoints retornan los códigos de estado y shapes de JSON correctos según contracts/api-v1.md.

- [ ] T027 [US3] Implementar `api/src/api/main.py`: factory de la app FastAPI con `lifespan` gestionando arranque/parada del async engine de BD; middleware CORS con orígenes configurables; incluir todos los routers; descripción de OpenAPI (FR-012, plan.md §API)
- [ ] T028 [US3] Implementar `api/src/api/dependencies.py`: dependencia FastAPI `get_db_session()` que yield una `AsyncSession`; dependencia para inyección de `pipeline_service` (plan.md §API)
- [ ] T029 [US3] Implementar `api/src/api/routes/health.py`: `GET /api/v1/health` que pinga decision_agent, vanna_agent, viz_agent, database, chinook_db; agrega el estado como `healthy`/`degraded`/`unhealthy`; `latency_ms` por componente; debe responder en < 1s (FR-010, SC-008, contracts/api-v1.md §GET /health)
- [ ] T030 [US3] Implementar `api/src/api/routes/generate.py`: `POST /api/v1/generate` aceptando `GenerateRequest`; generar `session_id` automáticamente si no se proporcionó; validar payload; llamar a `pipeline_service.run()`; retornar `GenerateResponse`; retornar HTTP 400/422 en errores de validación, 500 en errores no previstos, 503 si la BD no está disponible (FR-009, FR-011, FR-016, FR-023, contracts/api-v1.md §POST /generate)
- [ ] T031 [US3] Implementar `api/src/api/routes/sessions.py`: `GET /api/v1/sessions/{session_id}/history` retornando todos los mensajes ordenados por `created_at ASC`; retornar 404 si la sesión no existe (FR-020, contracts/api-v1.md §GET /sessions)
- [ ] T032 [US3] Implementar `api/src/api/routes/results.py`: `GET /api/v1/results/{result_id}` retornando `ResultResponse`; retornar 404 si no existe (FR-021, contracts/api-v1.md §GET /results)

---

## Fase 6 — Historia de Usuario 4: Integración y Wrapper de Agentes (P3)

> Objetivo: Orchestrator con abstracciones Protocol que permiten intercambiar agentes sin modificar el código del pipeline.  
> Test independiente: Instanciar cada agente a través del orchestrator, reemplazar la implementación de viz_agent y verificar que el pipeline sigue produciendo el output correcto.

- [ ] T033 [US4] Implementar `orchestrator/protocols.py`: `Text2SQLAgent`, `VizAgentProtocol`, `DecisionAgentProtocol` como clases Python `Protocol` con firmas de métodos tipadas que coincidan con los entry-points reales de cada agente (plan.md §Orchestrator, FR-013, NFR-004)
- [ ] T034 [US4] Implementar `orchestrator/pipeline.py`: clase `Pipeline` que cumple con `DecisionAgentProtocol`; el constructor recibe implementaciones de `Text2SQLAgent` y `VizAgentProtocol` por DI; `run()` delega a `DecisionAgent` con los agentes inyectados; lanza `PipelineError` ante fallos inesperados (plan.md §Orchestrator, FR-013)
- [ ] T035 [US4] Implementar `orchestrator/exceptions.py`: `PipelineError` (envuelve errores de nivel inferior con contexto de la etapa del pipeline) (plan.md §Orchestrator)
- [ ] T036 [US4] Implementar `api/src/api/services/pipeline_service.py`: puente entre las rutas de la API y `orchestrator.pipeline.Pipeline`; instancia `VannaAgent` y `DecisionAgent` vía Protocol; expone `run(query, session_id, conversation_history) -> DecisionAgentOutput`; propaga errores como excepciones compatibles con HTTP (plan.md §API §services, FR-013)

---

## Fase 7 — Historia de Usuario 5: Persistencia de Resultados de Visualización (P2)

> Objetivo: Cada pipeline exitoso genera un `GenerationResult` persistido recuperable vía `/results/{id}`; los fallos nunca persisten resultados.  
> Test independiente: Ejecutar una consulta exitosa, verificar el registro en BD y luego consultar `/results/{result_id}` para verificar el round-trip completo.

- [ ] T037 [US5] Implementar `api/src/api/services/result_service.py`: CRUD async para `GenerationResult`: `save_result(session_id, query, sql, viz_json, plotly_code, chart_type) -> GenerationResult`; `get_result_by_id(result_id) -> GenerationResult | None`; solo se invoca ante éxito del pipeline (FR-019, data-model.md §GenerationResult)
- [ ] T038 [US5] Actualizar `api/src/api/routes/generate.py`: luego de respuesta exitosa del pipeline, llamar a `result_service.save_result()`; incluir `result_id` en `GenerateResponse`; si el guardado falla, registrar el error en log y retornar igualmente la visualización al cliente (FR-019, FR-022)
- [ ] T039 [US5] Actualizar `api/src/api/routes/results.py`: conectar `result_service.get_result_by_id()` y retornar `ResultResponse` o 404 (FR-021)

---

## Fase 8 — Historia de Usuario 6: Historial de Conversación con Contexto (P2)

> Objetivo: Cada request/response se persiste; los últimos 5 mensajes se pasan como contexto al agente decisor; `/sessions/{id}/history` retorna el historial completo ordenado.  
> Test independiente: Enviar dos consultas relacionadas en la misma sesión y verificar que la segunda se resuelve correctamente usando la primera como contexto.

- [ ] T040 [US6] Implementar `api/src/api/services/session_service.py`: `get_or_create_session(session_id: UUID | None) -> Session`; `save_message(session_id, role, content, response_type) -> ConversationMessage`; `get_context_window(session_id, limit=5) -> list[ConversationContext]`; `get_full_history(session_id) -> list[MessageItem]` ordenado ASC (FR-016, FR-017, FR-018, FR-020)
- [ ] T041 [US6] Actualizar `api/src/api/routes/generate.py`: antes de llamar a `pipeline_service`, invocar `session_service.get_context_window()` y pasar como `conversation_history`; luego de la respuesta, llamar a `session_service.save_message()` para la consulta del usuario y la respuesta del sistema; usar try/except para que el fallo en el guardado no bloquee la respuesta (FR-017, FR-018, FR-022)
- [ ] T042 [US6] Actualizar `api/src/api/routes/sessions.py`: conectar `session_service.get_full_history()` como respuesta de `GET /api/v1/sessions/{session_id}/history`; retornar 404 si la sesión no existe (FR-020)

---

## Fase 9 — Polish y Aspectos Transversales

> Objetivo: Calidad de producción, smoke tests y documentación.

- [ ] T043 Implementar `vanna_agent/examples/basic_usage.py`: smoke test standalone que llama a `VannaAgent.text_to_sql("total de ventas")` y `execute_sql()`, imprimiendo los resultados (quickstart.md §Ejecutar el Agente Decisor)
- [ ] T044 [P] Crear `decision_agent/.env.example`, `vanna_agent/.env.example` y `api/.env.example` con nombres de variables de entorno documentados y valores placeholder (quickstart.md §Configuración)
- [ ] T045 [P] Agregar `api/src/api/routes/__init__.py` registrando todos los prefijos de rutas bajo `/api/v1`; verificar que el schema OpenAPI refleje todos los endpoints con ejemplos de request/response por cada contrato (NFR-005)
- [ ] T046 [P] Agregar manejadores globales de excepciones HTTP en `api/src/api/main.py` para `SQLValidationError` → 400, `PipelineError` → 500, errores de conexión a BD → 503 con cuerpo JSON estructurado en formato `error_type/message/context` (FR-011, contracts/api-v1.md §Error Responses)
- [ ] T047 Agregar manejo de timeout en `decision_agent/src/decision_agent/agent.py`: aplicar límite de < 15s de duración total del pipeline; lanzar `PipelineError(error_type="timeout")` si se supera (NFR-001)
- [ ] T048 Revisar y verificar que todas las llamadas a `structlog` en `decision_agent/`, `vanna_agent/`, `orchestrator/` y `api/` emitan los campos: `agent`, `stage`, `session_id`, `elapsed_ms`, y en caso de error: `error_type`, `context` (FR-008, NFR-003, SC-007)

---

## Grafo de dependencias

```
T001-T004 (Setup)
  → T005-T015 (Foundational)
    → T016-T023 (US1 núcleo del pipeline)        ← MVP
      → T024-T026 (US2 routing)
    → T027-T032 (US3 endpoints de la API)
      → T033-T036 (US4 orchestrator)              ← rutas US3 se conectan vía pipeline_service
      → T037-T039 (US5 persistencia de resultados) ← requiere rutas US3 + BD
      → T040-T042 (US6 conversación)              ← requiere rutas US3 + BD
    → T043-T048 (Polish)
```

---

## Ejemplos de ejecución en paralelo

### Fase 2 Foundational
```
Lote paralelo A: T005, T006, T007, T008, T009
Lote paralelo B: T010, T011, T013, T014, T015
Secuencial: T012 (luego de T010 + T011)
```

### Fase 3 US1
```
Lote paralelo A: T016, T017 (archivos de prompts, sin dependencias)
Lote paralelo B (luego de A): T018 (classifier usa prompts), T019 (sql_validator, independiente), T020 (vanna agent, independiente)
Secuencial: T021 (agent.py orquesta todo lo anterior), T022 (extiende agent.py), T023
```

### Fase 5 US3 + Fase 6 US4
```
Paralelo: T033, T034, T035 (protocols del orchestrator, sin dependencias de la API)
Paralelo: T027, T028, T029 (main.py, deps, ruta health — sin dependencia de pipeline_service)
Secuencial: T036 (pipeline_service luego de T033-T035), luego T030, T031, T032 (rutas que usan pipeline_service)
```

---

## Validación de formato

Todas las 48 tareas siguen el formato: `- [ ] T### [P?] [US?] Descripción con ruta de archivo`. ✅

## Resumen

| Fase | Historia | Tareas | Paralelizables |
|---|---|---|---|
| Fase 1 — Setup | — | 4 | 4 (T001–T004) |
| Fase 2 — Foundational | — | 11 | 7 |
| Fase 3 — US1 End-to-End | US1 (P1) | 8 | 4 |
| Fase 4 — US2 Routing | US2 (P2) | 3 | 1 |
| Fase 5 — US3 API REST | US3 (P2) | 6 | 2 |
| Fase 6 — US4 Orchestrator | US4 (P3) | 4 | 1 |
| Fase 7 — US5 Persistencia | US5 (P2) | 3 | 0 |
| Fase 8 — US6 Historial | US6 (P2) | 3 | 0 |
| Fase 9 — Polish | — | 6 | 4 |
| **Total** | **6 historias** | **48** | **23** |

**Alcance MVP**: Fases 1 + 2 + 3 (23 tareas) → pipeline del agente decisor funcionando de forma standalone, sin API ni persistencia.
