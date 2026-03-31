# GenBI Backend Development Guidelines

Auto-generated from feature plans. Last updated: 2026-03-23

## Active Technologies

- **Language**: Python ≥ 3.11
- **API**: FastAPI + uvicorn
- **LLM**: Google GenAI SDK (`google-genai`) — Gemini 2.5 Flash
- **ORM**: SQLAlchemy 2.0 (async) + asyncpg
- **Migrations**: Alembic
- **Validation**: Pydantic v2
- **SQL Safety**: sqlparse
- **Logging**: structlog
- **Dependency Management**: uv + pyproject.toml
- **Testing**: pytest + pytest-cov + pytest-mock
- **Linting**: ruff (lint + format) + mypy

## Project Structure

```text
backend/
├── decision_agent/       # Agente decisor (Gemini intent classification + pipeline)
│   ├── src/decision_agent/
│   ├── tests/
│   └── examples/
├── vanna_agent/          # Wrapper de Vanna AI (text2sql)
│   ├── src/vanna_agent/
│   ├── tests/
│   └── examples/
├── viz_agent/            # Agente de visualización (ya implementado)
│   ├── src/viz_agent/
│   ├── tests/
│   └── examples/
├── orchestrator/         # Protocol classes + pipeline orchestration
├── api/                  # FastAPI REST API + PostgreSQL persistence
│   ├── src/api/
│   ├── alembic/
│   └── tests/
└── specs/                # Feature specifications
```

## Key Conventions

- **Agent-First**: Cada agente en su propio directorio, entry-point independiente, sin importar FastAPI
- **Config**: Pydantic `BaseSettings`, no `os.getenv()` sueltos. Secrets via `.env` + `python-dotenv`
- **Naming**: snake_case (vars/functions), CamelCase (classes), UPPER_SNAKE_CASE (constants)
- **Errors**: Custom exception classes con `error_type`, `message`, `context`
- **Tests**: pytest, mock LLM calls en unit tests, `@pytest.mark.integration` para tests reales
- **Imports**: Agentes se usan via Protocol classes del orchestrator, nunca importación directa

## Commands

```bash
# Run agent standalone (example: decision_agent)
cd decision_agent && uv run python examples/basic_usage.py

# Run API
cd api && uv run uvicorn src.api.main:app --reload --port 8000

# Run tests
cd <agent_dir> && uv run pytest

# Lint + format
uv run ruff check . && uv run ruff format .

# Type checking
uv run mypy src/

# DB migrations
cd api && uv run alembic upgrade head
```

## Recent Changes

- TFG-13-crear-agente-decisor: Decision agent + Vanna agent wrapper + FastAPI API + PostgreSQL persistence

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
