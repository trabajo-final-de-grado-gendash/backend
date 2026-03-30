# API Contracts: GenBI REST API v1

**Base URL**: `http://localhost:8000/api/v1`
**Format**: JSON
**Auth**: None (NFR-006, entorno local Sprint 2)

---

## POST /generate

Endpoint principal: recibe consulta en lenguaje natural, orquesta el pipeline y retorna resultado.

### Request

```json
{
  "query": "ventas por mes del último año",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"  // optional
}
```

| Field | Type | Required | Constraints | Notes |
|---|---|---|---|---|
| `query` | string | ✅ | min_length=1, max_length=2000 | Consulta en lenguaje natural |
| `session_id` | UUID | ❌ | UUID v4 válido | Si omitido, se genera automáticamente |

### Response: Visualization (200)

```json
{
  "response_type": "visualization",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "result_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "message": null,
  "plotly_json": { "data": [...], "layout": {...} },
  "sql": "SELECT genre, SUM(total) FROM invoices GROUP BY genre",
  "plotly_code": "import plotly.express as px\n...",
  "chart_type": "bar"
}
```

### Response: Clarification (200)

```json
{
  "response_type": "clarification",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "result_id": null,
  "message": "Detecté múltiples intenciones en tu consulta. ¿Deseas ver las ventas por mes y el top 10 de artistas como gráficos separados o combinados?",
  "plotly_json": null,
  "sql": null,
  "plotly_code": null
}
```

### Response: Message (200)

```json
{
  "response_type": "message",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "result_id": null,
  "message": "¡Hola! Soy un asistente especializado en visualizar datos de la base Chinook. ¿Qué te gustaría analizar?",
  "plotly_json": null,
  "sql": null,
  "plotly_code": null
}
```

### Error Responses

**400 Bad Request** — Payload inválido:
```json
{
  "detail": [
    {
      "loc": ["body", "query"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**422 Unprocessable Entity** — Validación de Pydantic:
```json
{
  "detail": [
    {
      "loc": ["body", "query"],
      "msg": "String should have at least 1 character",
      "type": "string_too_short"
    }
  ]
}
```

**500 Internal Server Error** — Error no previsto:
```json
{
  "error_type": "PipelineError",
  "message": "Unexpected error during pipeline execution",
  "context": {
    "stage": "sql_generation",
    "details": "..."
  }
}
```

**503 Service Unavailable** — Base de datos no disponible:
```json
{
  "error_type": "ServiceUnavailable",
  "message": "Data service is currently unavailable",
  "context": {
    "component": "chinook_db"
  }
}
```

---

## GET /health

Estado de salud de cada componente del sistema.

### Response (200)

```json
{
  "status": "healthy",
  "components": {
    "decision_agent": { "status": "up", "latency_ms": 12.5 },
    "vanna_ai": { "status": "up", "latency_ms": 45.0 },
    "viz_agent": { "status": "up", "latency_ms": 8.2 },
    "database": { "status": "up", "latency_ms": 3.1 },
    "chinook_db": { "status": "up", "latency_ms": 5.0 }
  }
}
```

| status value | Meaning |
|---|---|
| `"healthy"` | Todos los componentes `up` |
| `"degraded"` | Al menos un componente `down` pero el servicio puede funcionar parcialmente |
| `"unhealthy"` | Componentes críticos `down` |

---

## GET /sessions/{session_id}/history

Historial de mensajes de una sesión.

### Path Parameters

| Parameter | Type | Required | Notes |
|---|---|---|---|
| `session_id` | UUID | ✅ | ID de la sesión |

### Response (200)

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "messages": [
    {
      "role": "user",
      "content": "ventas por mes",
      "response_type": null,
      "timestamp": "2026-03-23T20:00:00Z"
    },
    {
      "role": "system",
      "content": null,
      "response_type": "visualization",
      "timestamp": "2026-03-23T20:00:05Z"
    },
    {
      "role": "user",
      "content": "ahora el mismo pero por año",
      "response_type": null,
      "timestamp": "2026-03-23T20:01:00Z"
    }
  ]
}
```

### Error: Session not found (404)

```json
{
  "error_type": "NotFound",
  "message": "Session 550e8400-... not found"
}
```

---

## GET /results/{result_id}

Recuperar un resultado de visualización guardado.

### Path Parameters

| Parameter | Type | Required | Notes |
|---|---|---|---|
| `result_id` | UUID | ✅ | ID del resultado |

### Response (200)

```json
{
  "result_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "query": "ventas por mes del último año",
  "sql": "SELECT strftime('%m', InvoiceDate) as month, SUM(Total) ...",
  "plotly_json": { "data": [...], "layout": {...} },
  "plotly_code": "import plotly.express as px\n...",
  "chart_type": "line",
  "created_at": "2026-03-23T20:00:05Z"
}
```

### Error: Result not found (404)

```json
{
  "error_type": "NotFound",
  "message": "Result 7c9e6679-... not found"
}
```

---

## Common Headers

### Request Headers

| Header | Value | Notes |
|---|---|---|
| `Content-Type` | `application/json` | Requerido para POST |

### Response Headers

| Header | Value | Notes |
|---|---|---|
| `Content-Type` | `application/json` | Siempre JSON |
| `Access-Control-Allow-Origin` | `*` (dev) | CORS habilitado (FR-012) |

---

## Response Type Summary (FR-023)

| `response_type` | Trigger | Contains |
|---|---|---|
| `"visualization"` | Pipeline exitoso | `plotly_json`, `sql`, `result_id`, `plotly_code`, `chart_type` |
| `"clarification"` | Consulta ambigua / múltiples intenciones | `message` con pregunta de seguimiento |
| `"message"` | Fuera de alcance / saludo / error descriptivo | `message` con texto plano |
