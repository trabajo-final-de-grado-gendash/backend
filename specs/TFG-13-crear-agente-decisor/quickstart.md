# Quickstart: Gen BI Backend

Guía rápida para levantar el entorno de desarrollo del Agente Decisor y la API de orquestación.

## Requisitos Previos

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (Recomendado para gestión de paquetes)
- PostgreSQL (Instancia corriendo para persistencia)

## Configuración del Entorno

1. **Clonar el repositorio** y posicionarse en la raíz del backend.
2. **Crear archivos .env**:
   Copia los ejemplos proporcionados en cada módulo y completa las llaves de API (Gemini):
   ```bash
   cp api/.env.example api/.env
   cp decision_agent/.env.example decision_agent/.env
   cp vanna_agent/.env.example vanna_agent/.env
   ```
3. **Variables Críticas**:
   - `GEMINI_API_KEY`: Requerida en todos los agentes.
   - `DATABASE_URL`: URL de PostgreSQL (ej: `postgresql+asyncpg://user:pass@localhost:5432/gendash_db`).
   - `CHINOOK_DB_URL`: Para `vanna_agent`, apunta a la base analítica.

## Ejecución de la API

Desde la raíz del proyecto:

```bash
# Instalar dependencias y correr en modo dev
export PYTHONPATH=$PWD/api/src:$PWD/decision_agent/src:$PWD/vanna_agent/src:$PWD/viz_agent/src
uv run --project api/ uvicorn api.main:app --reload
```

La API estará disponible en `http://localhost:8000`. Puedes ver la documentación interactiva en `/docs`.

## Ejecución de Tests

### Tests de la API (Smoke Tests)
```bash
uv run --project api/ --extra dev pytest api/tests/smoke_test.py
```

### Tests del Decision Agent
```bash
uv run --project api/ --extra dev pytest decision_agent/tests/test_agent.py
```

## Estructura de Endpoints Principales

- `POST /api/v1/generate`: Punto de entrada principal para consultas en lenguaje natural.
- `GET /api/v1/sessions/{id}/history`: Recupera el historial de chat.
- `GET /api/v1/results/{id}`: Recupera una visualización guardada específicamente.
- `GET /api/v1/health`: Estado de salud del sistema y sus componentes.
