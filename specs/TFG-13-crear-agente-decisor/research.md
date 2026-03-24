# Research: Agente Decisor y API de Orquestación

**Date**: 2026-03-23
**Purpose**: Resolver todas las incógnitas técnicas antes de diseño (Phase 0)

---

## R-001: Arquitectura del Agente Decisor con Gemini

**Decision**: El agente decisor se implementa como un módulo Python independiente (`decision_agent/`) siguiendo el patrón establecido por `viz_agent/`. Usa Google GenAI SDK (`google-genai`) con Gemini 2.5 Flash y structured output para clasificar intenciones.

**Rationale**:
- La constitución exige Agent-First Architecture (Principio I): cada agente en su propio directorio, entry-point independiente, sin importar FastAPI.
- `viz_agent` ya valida este patrón con éxito: `src/viz_agent/agent.py` expone `VizAgent.generate_visualization()` como entry-point.
- Gemini 2.5 Flash ya está probado en `viz_agent` con structured output (JSON Schema + Pydantic), lo que asegura consistencia.

**Alternatives considered**:
- **LangChain / LangGraph**: Descartado. El flujo del decision agent es determinístico y simple: classify intent (1 llamada a Gemini) → `match` con 4 ramas → ejecutar. No hay un grafo cíclico, ni herramientas que el LLM elige dinámicamente, ni razonamiento iterativo. LangChain introduciría ~15 dependencias transitivas, capas de abstracción (`AgentExecutor`, `RunnableSequence`, `ChatModel`) que oscurecen el debugging, y obligaría a wrappear el SDK de google-genai (que ya usamos directamente en viz_agent). El routing se resuelve con ~20 líneas de un `match/case` de Python, vs ~60-80 líneas de nodos, edges y state schemas de LangGraph. Si en el futuro el sistema crece a +10 agentes con routing dinámico, se reevalúa.
- **Observabilidad (LangSmith)**: LangSmith funciona **sin LangChain**. El SDK `langsmith` es independiente y framework-agnostic. Se instrumenta con el decorador `@traceable` sobre nuestras funciones, lo que produce traces más limpios (se ven las funciones del proyecto, no nodos internos de LangChain). Setup: solo `LANGSMITH_API_KEY` + `LANGSMITH_TRACING=true` en `.env`. Se agrega como dependencia cuando se implemente el sprint de observabilidad, sin refactoring.
- OpenAI function calling: Descartado porque el proyecto ya usa Gemini (constitución fija).
- ReAct loop genérico: Descartado; el agente decisor tiene un flujo determinístico (classify → route → execute), no necesita razonamiento iterativo.

---

## R-002: Integración con Vanna AI (Text2SQL)

**Decision**: Vanna AI se encapsula en su propio directorio `vanna_agent/` siguiendo el patrón Agent-First de la constitución, con la misma estructura que `viz_agent/` y `decision_agent/`. Internamente es un wrapper liviano sobre la librería Vanna ya configurada (`test_vanna.py`), exponiendo un entry-point simple. El `decision_agent` lo recibe como abstracción inyectada vía Protocol (`Text2SQLAgent`).

**Rationale**:
- Principio I (Agent-First): cada agente en su propio directorio. Mantener Vanna como un script suelto (`test_vanna.py`) viola esta regla.
- El archivo `test_vanna.py` en la raíz ya tiene la configuración funcional (Azure OpenAI + PostgresRunner contra Chinook). El wrapper la reutiliza; no reescribimos Vanna.
- Principio VI (Dependency Inversion): el decision_agent depende de una abstracción (`Text2SQLAgent` Protocol), no de la implementación concreta.
- Principio II: Vanna resuelve Text2SQL exclusivamente; el decision_agent solo orquesta.
- **Esfuerzo estimado**: ~3-4 horas (Protocol ~15min, wrapper ~1-2h, tests ~1h, smoke test ~30min). La configuración ya existe, solo se reorganiza.

**Alternatives considered**:
- Importar Vanna directamente en el decision_agent: Viola Principio VI (Dependency Inversion) y acopla la implementación.
- Dejar Vanna como script suelto sin estructura de agente: Viola Principio I y queda desorganizado respecto a los otros agentes.

---

## R-003: Validación de SQL (Seguridad)

**Decision**: Implementar un validador de SQL basado en parsing de la consulta con `sqlparse` (librería pura Python) que intercepte TODA operación no-SELECT antes de ejecutar contra Chinook.

**Rationale**:
- FR-004 y FR-024 exigen validación programada obligatoria e inalterable.
- NFR-007 hace de esto un requisito de seguridad crítico.
- `sqlparse` es una librería madura, sin dependencias nativas, que puede tokenizar SQL y detectar statement types.

**Alternatives considered**:
- Regex sobre el SQL: Frágil, fácil de evadir con CTEs, subconsultas o comentarios SQL.
- Confiar en el prompt del LLM: Explícitamente prohibido por la constitución (la validación no puede depender exclusivamente del modelo).
- Usar permisos de usuario en PostgreSQL (READ-ONLY role): Complementario pero no suficiente como única capa; la spec exige validación programada.

---

## R-004: Clasificación de Intenciones con Gemini

**Decision**: El agente utiliza Gemini para clasificar cada consulta en una de cuatro categorías (`visualization`, `clarification`, `message`, `out_of_scope`) usando structured output. El prompt incluye el esquema de la base de datos Chinook como contexto.

**Rationale**:
- FR-014 requiere clasificación en 4 categorías: válida/clara, ambigua, fuera de alcance, conversacional.
- El structured output de Gemini (ya probado en viz_agent) garantiza respuestas parseables.
- Incluir el schema de Chinook en el prompt permite al LLM determinar si la consulta es viable sin ejecutar nada.

**Alternatives considered**:
- Classifier ML dedicado: Overhead de training innecesario; Gemini con few-shot es suficiente y más flexible.
- Rule-based (keywords): No escala a lenguaje natural ambiguo; no detectaría saludos vs. consultas mal formuladas.

---

## R-005: FastAPI como Framework de API

**Decision**: FastAPI con estructura `api/` en la raíz del repositorio. Endpoints bajo prefijo `/api/v1/`. Pydantic v2 para request/response schemas. CORS habilitado para localhost.

**Rationale**:
- La constitución fija FastAPI como framework de API.
- La spec requiere versionamiento explícito (`/api/v1/`).
- Pydantic v2 ya está en uso extensivo en el proyecto (viz_agent models).

**Alternatives considered**:
- Flask: Descartado, la constitución fija FastAPI.
- Django REST: Descartado, mismo motivo.

---

## R-006: PostgreSQL para Persistencia (Sessions, Messages, Results)

**Decision**: PostgreSQL como BD de persistencia de la API (separada de Chinook). Se usa `asyncpg` + `SQLAlchemy 2.0` (async) para el ORM. Tres tablas principales: `sessions`, `conversation_messages`, `generation_results`. Migraciones con Alembic.

**Rationale**:
- El usuario especificó PostgreSQL explícitamente.
- La spec (Assumption 8) confirma que la BD de persistencia es separada de Chinook.
- SQLAlchemy 2.0 async + asyncpg es el stack estándar para FastAPI + PostgreSQL.
- Las entidades clave de la spec (Session, ConversationMessage, GenerationResult) mapean directamente a 3 tablas.

**Alternatives considered**:
- **SQLModel** (de Tiangolo/FastAPI): Fusiona Pydantic + SQLAlchemy en 1 clase, lo cual reduce boilerplate en CRUDs simples. Sin embargo: (1) no soporta `AsyncSession` nativamente — hay que mezclar con `sqlalchemy.ext.asyncio` y se vuelve incómodo; (2) todavía está en versión `0.x`, no es 1.0 estable; (3) internamente usa Pydantic v1 o un shim, lo cual puede chocar con nuestro proyecto que usa Pydantic v2 en todos lados. Con solo 3 tablas, el ahorro de boilerplate es ~20 líneas, y los riesgos de incompatibilidad async + Pydantic v2 no lo justifican.
- SQLite: Más simple pero no soporta bien concurrencia (NFR-002 requiere 5 requests concurrentes simultáneos).
- Motor puro asyncpg sin ORM: Viable pero incrementa boilerplate; SQLAlchemy 2.0 da migraciones con Alembic + modelos declarativos.

---

## R-007: Historial de Conversación (Ventana de Contexto)

**Decision**: Se recuperan los últimos 5 mensajes (configurable) de la sesión antes de cada invocación al agente decisor. El historial se formatea como lista de `{role, content}` y se inyecta en el prompt de Gemini.

**Rationale**:
- FR-017 y spec (Assumption 9) fijan la ventana en 5 mensajes.
- SC-010 requiere que el agente resuelva >=80% de consultas de refinamiento con este contexto.
- Inyectar el historial como parte del prompt es el patrón estándar para contexto conversacional con LLMs.

**Alternatives considered**:
- Historial completo sin límite: Riesgo de exceder ventana de tokens del LLM y aumentar latencia/costo.
- Embeddings + vector search: Overengineering para 5 mensajes; innecesario en esta fase.

---

## R-008: Wrapper de Agentes (Orquestación)

**Decision**: Módulo `orchestrator/` en la raíz con Protocol classes para `VizAgent`, `Text2SQLAgent` y `DecisionAgent`. La API importa solo del orchestrator, nunca directamente de los agentes.

**Rationale**:
- Principio VI (Dependency Inversion): la API depende de abstracciones, no de implementaciones concretas.
- FR-013 exige un wrapper que permita instanciar y coordinar los 3 agentes de forma desacoplada.
- US-4 requiere que los agentes sean intercambiables sin modificar el código del pipeline.

**Alternatives considered**:
- Importar agentes directamente desde la API: Viola Principio I y VI.
- Registry pattern (diccionario de agentes): Más flexible pero innecesario para 3 agentes conocidos; se puede agregar después.

---

## R-009: Manejo de Errores y Logging

**Decision**: Custom exception hierarchy (`AgentError`, `SQLValidationError`, `LLMError`, `PipelineError`). Logging con `structlog` para logs JSON estructurados. Cada invocación del pipeline genera un log entry con input, route, attempts y outcome.

**Rationale**:
- Principio IV exige errores tipados y structured logging obligatorio.
- FR-008 requiere registrar decisiones, tiempos y errores.
- SC-007 requiere que los logs permitan reconstruir el flujo completo.
- `structlog` es una librería madura para structured logging en Python, complementaria con el `logging` estándar.

**Alternatives considered**:
- `logging` standard library: Suficiente para logging básico pero no produce JSON estructurado out of the box.
- Logger custom como en viz_agent: El `VizAgentLogger` actual es específico de viz; se generaliza el patrón pero se mejora con structlog.

---

## R-010: Concurrencia y Performance

**Decision**: FastAPI async handlers + asyncpg para queries DB no-bloqueantes. LLM calls (Gemini) se ejecutan sincrónicamente en thread pool executor ya que el SDK de google-genai es síncrono.

**Rationale**:
- NFR-001: pipeline completo < 15s (p90).
- NFR-002: 5 requests concurrentes sin degradación.
- **¿Por qué concurrencia?** Cuando varias personas usan la app web al mismo tiempo (ej: durante la demo de la tesis o testing), cada request tarda 3-5s esperando la respuesta de Gemini. Sin async, el server queda bloqueado y el segundo usuario espera a que termine el primero. Con 5 usuarios sincrónicos, el último esperaría ~25s. Con async, mientras el request 1 espera a Gemini, el server atiende los requests 2-5 en paralelo.
- FastAPI maneja concurrencia internamente con su event loop asyncio; el cuello de botella es la latencia del LLM (~3-5s por llamada).
- `asyncpg` evita bloquear el event loop en queries a PostgreSQL. Si la BD tarda 50ms por query pero es síncrona, esos 50ms bloquean a TODOS los demás requests.

**Alternatives considered**:
- Full sync (sin async FastAPI): Bloquearía el server en cada request de DB o LLM. Inaceptable para NFR-002.
- gRPC para comunicación inter-agentes: Overengineering para llamadas in-process.
