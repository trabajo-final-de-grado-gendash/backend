# Quickstart: GenBI Backend

Guía rápida para levantar el entorno de desarrollo del sistema GenBI con configuración centralizada.

## Requisitos Previos

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (Recomendado)
- PostgreSQL corriendo localmente.

## Configuración del Entorno

1. **Clonar el repositorio** y posicionarse en la raíz del backend (`/backend`).
2. **Crear archivo .env centralizado**:
   Copia el ejemplo de la raíz:
   ```bash
   cp .env.example .env
   ```
3. **Variables Críticas**:
   Edita el nuevo archivo `.env` en la raíz con tus credenciales:
   ```bash
   # API & Persistencia
   APP_DB_URL=postgresql+asyncpg://user:pass@localhost:5432/genbi_db

   # Agentes & Fuente de Datos
   SOURCE_DB_URL=postgresql://user:pass@localhost:5432/chinook
   GEMINI_API_KEY=your_api_key_here
   ```
   - `GEMINI_API_KEY`: Tu API Key de Google AI Studio.
   - `APP_DB_URL`: URL de conexión a la base de datos de la aplicación.
   - `SOURCE_DB_URL`: URL de conexión a la base de datos de datos (ej: Chinook).
   - `GEMINI_MODEL`: Modelo a usar (ej: `gemini-1.5-flash`).

*Nota: No es necesario crear archivos .env dentro de cada carpeta de agente, ya que todos leerán el archivo de la raíz automáticamente.*

## Ejecución de la API

Desde la raíz del proyecto:

```bash
# Configurar PYTHONPATH e iniciar servidor
export PYTHONPATH=$PWD/api/src:$PWD/decision_agent/src:$PWD/vanna_agent/src:$PWD/viz_agent/src
uv run --project api/ uvicorn api.main:app --reload
```

La API estará disponible en `http://localhost:8000/api/v1`. Documentación en `/docs`.

## Ejecución de Tests

```bash
# Smoke test completo
uv run --project api/ pytest api/tests/smoke_test.py

# Tests unitarios del Decision Agent
uv run --project api/ pytest decision_agent/tests/test_agent.py
```

## Estructura de Endpoints

- `POST /api/v1/generate`: Generar SQL + Visualización desde lenguaje natural.
- `GET /api/v1/sessions/{id}/history`: Historial de conversación.
- `GET /api/v1/results/{id}`: Detalle de un resultado guardado.
- `GET /api/v1/health`: Estado del sistema.
