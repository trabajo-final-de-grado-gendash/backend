# Quickstart: Agente Decisor y API de Orquestación

## Prerequisites

- Python ≥ 3.11
- `uv` instalado (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- PostgreSQL ≥ 14 (para BD de persistencia de la API)
- PostgreSQL con Chinook DB cargada (para Vanna AI / text2sql)
- API Key de Google Gemini (Gemini 2.5 Flash)
- Vanna AI configurado con Azure OpenAI

## Setup

### 1. Clonar y configurar el entorno

```bash
# Desde la raíz del repositorio backend/
cd decision_agent
uv sync
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tus credenciales:
#   GEMINI_API_KEY=...
#   DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/genbi_db
#   CHINOOK_DB_URL=postgresql://user:pass@localhost:5432/chinook
```

### 3. Crear la base de datos de persistencia

```bash
createdb genbi_db
# Si usas Docker:
# docker exec -it postgres createdb genbi_db

# Ejecutar migraciones:
cd ../api
uv run alembic upgrade head
```

## Running the Decision Agent (Standalone)

```bash
cd decision_agent
uv run python examples/basic_usage.py
```

Ejemplo de output esperado:
```
[DecisionAgent] Input: "ventas por mes del último año"
[DecisionAgent] Intent: valid_and_clear
[DecisionAgent] Route: SQL → Viz pipeline
[DecisionAgent] SQL generated: SELECT ...
[DecisionAgent] Visualization: success (line chart)
[DecisionAgent] Total time: 4.2s
```

## Running the API

```bash
cd api
uv run uvicorn src.api.main:app --reload --port 8000
```

### Test endpoints:

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Generate visualization
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"query": "ventas por mes del último año"}'

# Get session history
curl http://localhost:8000/api/v1/sessions/{session_id}/history

# Get saved result
curl http://localhost:8000/api/v1/results/{result_id}
```

## Running Tests

```bash
# Decision Agent unit tests
cd decision_agent
uv run pytest

# API tests
cd api
uv run pytest

# Integration tests (requires Gemini API + DBs)
uv run pytest -m integration
```

## Project Structure (Quick Reference)

```
backend/
├── decision_agent/           # Agente decisor (standalone)
│   ├── src/decision_agent/
│   │   ├── agent.py          # Entry-point: DecisionAgent.run()
│   │   ├── classifier.py     # Intent classification with Gemini
│   │   ├── sql_validator.py  # SQL safety validation
│   │   ├── models.py         # Pydantic models
│   │   ├── config.py         # Configuration
│   │   └── prompts/          # LLM prompts
│   ├── tests/
│   └── examples/
├── vanna_agent/              # Wrapper de Vanna AI (standalone)
│   ├── src/vanna_agent/
│   │   ├── agent.py          # Entry-point: VannaAgent.text_to_sql()
│   │   ├── config.py         # Azure OpenAI + Chinook connection
│   │   └── models.py         # Pydantic models
│   ├── tests/
│   └── examples/
├── api/                      # FastAPI REST API
│   ├── src/api/
│   │   ├── main.py           # App factory + CORS
│   │   ├── routes/           # Endpoint handlers
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── services/         # Business logic
│   │   └── config.py
│   ├── alembic/              # DB migrations
│   └── tests/
├── orchestrator/             # Agent wrapper/integration
│   ├── protocols.py          # Agent abstractions (Protocol)
│   └── pipeline.py           # Pipeline orchestration
├── viz_agent/                # Already implemented
└── specs/                    # Feature specs
```
