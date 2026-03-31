# Data Model: Agente Decisor y API de Orquestación

**Date**: 2026-03-23
**Source**: spec.md (Key Entities, FRs 016-022)

---

## Entity: Session

Agrupador de interacciones dentro de un hilo conversacional.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK, default=uuid4 | Identificador único de sesión |
| `created_at` | datetime | NOT NULL, default=now() | Momento de creación |
| `updated_at` | datetime | NOT NULL, default=now() | Última actividad |

**Relationships**:
- Session `1` → `N` ConversationMessage
- Session `1` → `N` GenerationResult

**Validation rules**:
- `id` debe ser UUID v4 válido
- Si el cliente envía un `session_id` inexistente, se crea automáticamente (FR-016)

---

## Entity: ConversationMessage

Unidad atómica del historial de sesión.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK, default=uuid4 | Identificador único del mensaje |
| `session_id` | UUID | FK → Session.id, NOT NULL | Sesión a la que pertenece |
| `role` | Enum("user", "system") | NOT NULL | Emisor del mensaje |
| `content` | Text | NOT NULL | Texto del mensaje (query o respuesta) |
| `response_type` | Enum("visualization", "clarification", "message") | NULLABLE | Solo para role="system" (FR-023) |
| `created_at` | datetime | NOT NULL, default=now() | Timestamp del mensaje |

**Relationships**:
- ConversationMessage `N` → `1` Session

**Validation rules**:
- `content` no puede estar vacío
- `response_type` solo aplica cuando `role = "system"`
- El historial se recupera ordenado por `created_at ASC`
- La ventana de contexto usa los últimos 5 mensajes (configurable)

**State transitions**: N/A (inmutable una vez creado)

---

## Entity: GenerationResult

Registro persistido de un pipeline exitoso completo.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK, default=uuid4 | `result_id` retornado al cliente |
| `session_id` | UUID | FK → Session.id, NOT NULL | Sesión asociada |
| `query` | Text | NOT NULL | Consulta original del usuario |
| `sql` | Text | NOT NULL | SQL generado por Vanna AI |
| `viz_json` | JSONB | NOT NULL | JSON Plotly completo de la visualización |
| `plotly_code` | Text | NULLABLE | Código Python generado (opcional, útil para debug) |
| `chart_type` | VARCHAR(50) | NULLABLE | Tipo de gráfico generado |
| `created_at` | datetime | NOT NULL, default=now() | Timestamp de creación |

**Relationships**:
- GenerationResult `N` → `1` Session

**Validation rules**:
- Solo se persiste cuando el pipeline completa exitosamente (FR-019)
- En caso de fallo del pipeline, NO se crea registro (FR-019, US-5 Scenario 2)
- `viz_json` debe ser JSON Plotly válido
- `sql` debe haber pasado la validación de SQL (solo SELECT)

**State transitions**: N/A (inmutable una vez creado)

---

## Entity Relationship Diagram

```mermaid
erDiagram
    SESSION ||--o{ CONVERSATION_MESSAGE : contains
    SESSION ||--o{ GENERATION_RESULT : produces

    SESSION {
        uuid id PK
        datetime created_at
        datetime updated_at
    }

    CONVERSATION_MESSAGE {
        uuid id PK
        uuid session_id FK
        enum role
        text content
        enum response_type
        datetime created_at
    }

    GENERATION_RESULT {
        uuid id PK
        uuid session_id FK
        text query
        text sql
        jsonb viz_json
        text plotly_code
        varchar chart_type
        datetime created_at
    }
```

---

## Pydantic Models (Application Layer)

Estos modelos representan la capa de aplicación y son independientes del ORM.

### Request/Response Models

```python
# Shared enums
class ResponseType(str, Enum):
    VISUALIZATION = "visualization"
    CLARIFICATION = "clarification"
    MESSAGE = "message"

class IntentCategory(str, Enum):
    VALID_AND_CLEAR = "valid_and_clear"
    VALID_BUT_AMBIGUOUS = "valid_but_ambiguous"
    OUT_OF_SCOPE = "out_of_scope"
    CONVERSATIONAL = "conversational"

class MessageRole(str, Enum):
    USER = "user"
    SYSTEM = "system"
```

### Decision Agent Models

```python
class DecisionAgentInput(BaseModel):
    """Input para el agente decisor"""
    query: str
    session_id: UUID | None = None
    conversation_history: list[ConversationContext] = []

class ConversationContext(BaseModel):
    """Mensaje de contexto conversacional"""
    role: MessageRole
    content: str

class IntentClassification(BaseModel):
    """Resultado de clasificación de intención (structured output de Gemini)"""
    category: IntentCategory
    reasoning: str
    clarification_question: str | None = None
    suggested_interpretations: list[str] = []

class DecisionAgentOutput(BaseModel):
    """Output del agente decisor"""
    response_type: ResponseType
    message: str | None = None
    sql: str | None = None
    viz_result: VizAgentOutput | None = None
    metadata: dict[str, Any] = {}
```

### API Models

```python
class GenerateRequest(BaseModel):
    """Request al endpoint POST /api/v1/generate"""
    query: str = Field(..., min_length=1, max_length=2000)
    session_id: UUID | None = None

class GenerateResponse(BaseModel):
    """Response del endpoint POST /api/v1/generate"""
    response_type: ResponseType
    session_id: UUID
    result_id: UUID | None = None
    message: str | None = None
    plotly_json: dict | None = None
    sql: str | None = None
    plotly_code: str | None = None

class HealthResponse(BaseModel):
    """Response del endpoint GET /api/v1/health"""
    status: str  # "healthy" | "degraded" | "unhealthy"
    components: dict[str, ComponentHealth]

class ComponentHealth(BaseModel):
    """Estado de un componente del sistema"""
    status: str  # "up" | "down"
    latency_ms: float | None = None

class SessionHistoryResponse(BaseModel):
    """Response del endpoint GET /api/v1/sessions/{session_id}/history"""
    session_id: UUID
    messages: list[MessageItem]

class MessageItem(BaseModel):
    """Mensaje individual en el historial"""
    role: MessageRole
    content: str
    response_type: ResponseType | None = None
    timestamp: datetime

class ResultResponse(BaseModel):
    """Response del endpoint GET /api/v1/results/{result_id}"""
    result_id: UUID
    query: str
    sql: str
    plotly_json: dict
    plotly_code: str | None = None
    chart_type: str | None = None
    created_at: datetime
```

---

## Database Configuration

- **Engine**: PostgreSQL ≥ 14
- **Driver**: `asyncpg` (async driver for SQLAlchemy 2.0)
- **ORM**: SQLAlchemy 2.0 (declarative + async)
- **Migrations**: Alembic
- **Connection**: Via `.env` (`DATABASE_URL=postgresql+asyncpg://user:pass@host:port/genbi_db`)
- **Nota**: Esta BD es independiente de Chinook (usada solo por Vanna AI para queries SELECT)
