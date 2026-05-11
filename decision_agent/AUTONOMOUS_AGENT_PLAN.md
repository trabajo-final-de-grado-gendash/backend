# Plan: Patrón de Agente Autónomo (Plan → Execute → Review)

**Fecha**: 2026-03-30
**Archivo objetivo principal**: `decision_agent/src/decision_agent/agent.py`

## Contexto y Motivación

El `DecisionAgent` actual funciona como un **orquestador determinístico** con el siguiente
flujo fijo:

```
Classify → (si valid) → Text2SQL → Validate SQL → Execute SQL → VizAgent → Return
```

Este flujo es correcto y funcional. El objetivo de este refactor es elevar su complejidad
académica incorporando el patrón **Plan → Execute → Review (PER)**, que es la base de
los sistemas LLM autónomos modernos (AutoGPT, ReAct, Reflexion).

Con este cambio, el flujo pasará a ser:

```
Plan (LLM genera un plan estructurado)
  ↓
Execute (cada tool/agente se ejecuta según el plan)
  ↓
Review (el LLM evalúa su propio output)
  ↓ (si falla) ↑ (vuelve a re-planear con contexto del error)
Return (si Review pasa) / Error descriptivo (si se agotaron retries)
```

---

## Qué Existe Hoy vs. Qué Cambia

| Etapa | Estado Actual | Cambio Propuesto |
|---|---|---|
| **Clasificación** | Gemini clasifica intención | Se mantiene igual — es la "pre-condición" |
| **Planificación** | NO existe | **NUEVO**: Gemini genera un `AgentPlan` estructurado |
| **Ejecución** | Lineal, sin contexto de plan | **REFACTOR**: Ejecuta basándose en el plan generado |
| **Revisión** | Solo validación de SQL (estructural) | **NUEVO**: Gemini revisa si el output cumple el plan |
| **Auto-corrección SQL** | 1 reintento con reformulación | Se mantiene igual, bajo el paraguas del nuevo executor |
| **Logging** | Ya con structlog ✅ | Añadir campos `plan_id`, `review_passed` |

---

## Archivos a Crear / Modificar

### Archivos Nuevos

```
decision_agent/src/decision_agent/
  ├── planner.py              # NUEVO: Clase AgentPlanner
  ├── reviewer.py             # NUEVO: Clase OutputReviewer
  └── prompts/
      ├── planning_prompt.py  # NUEVO: Template de prompt para planificación
      └── review_prompt.py    # NUEVO: Template de prompt para revisión
```

### Archivos Modificados

```
decision_agent/src/decision_agent/
  ├── agent.py                # REFACTOR: Nuevo método _plan_and_execute()
  └── models.py               # REFACTOR: Nuevos modelos AgentPlan, ReviewResult
```

---

## Detalle de Implementación

### PASO 1 — Nuevos Modelos Pydantic (`models.py`)

**Agregar los siguientes modelos al final de `models.py`:**

```python
class PlanStep(BaseModel):
    """Un paso individual dentro del plan del agente."""
    step_id: int
    action: str   # e.g. "generate_sql", "execute_sql", "generate_viz"
    description: str  # Razonamiento de por qué este paso
    expected_output: str  # Qué debe producir este paso

class AgentPlan(BaseModel):
    """El plan estructurado que Gemini genera antes de ejecutar."""
    query_interpretation: str  # Cómo el LLM interpretó la consulta
    steps: list[PlanStep]
    requires_temporal_filter: bool  # Hint para Vanna (tiene filtros de fecha?)
    expected_chart_type: str | None  # Sugerencia de gráfico para viz_agent
    confidence: float  # De 0.0 a 1.0 — qué tan seguro está el plan

class ReviewResult(BaseModel):
    """Resultado de la revisión hecha por el Reviewer."""
    passed: bool
    feedback: str  # Descripción de qué estuvo bien o mal
    suggested_fix: str | None  # Si failed, qué debería corregirse
    data_quality_ok: bool  # ¿El DataFrame tiene datos coherentes con la consulta?
    viz_quality_ok: bool   # ¿La visualización es apropiada para los datos?
```

---

### PASO 2 — Nuevo Prompt de Planificación (`prompts/planning_prompt.py`)

**Propósito**: Dado el input del usuario y el historial, Gemini genera un `AgentPlan`.

```python
PLANNING_PROMPT_TEMPLATE = """
You are the planning module of an autonomous BI agent.
Your job is to create a step-by-step execution plan to answer the user's query.

## User Query
{query}

## Conversation History (last 5 messages)
{history}

## Available Tools
- generate_sql: Converts natural language to SQL using Vanna AI
- execute_sql: Runs the SQL query against the Chinook PostgreSQL database
- generate_viz: Creates an interactive Plotly chart from a DataFrame

## Instructions
1. Interpret the user's query carefully
2. Plan the minimal sequence of steps needed
3. Specify what data you expect from each step
4. Suggest the most appropriate chart type if a visualization is needed
5. Assign a confidence score (0.0 to 1.0) to your plan

Generate a structured plan following the JSON schema provided.
"""
```

---

### PASO 3 — Nuevo Prompt de Revisión (`prompts/review_prompt.py`)

**Propósito**: Dado el plan original y el output ejecutado, Gemini evalúa si el resultado
es correcto.

```python
REVIEW_PROMPT_TEMPLATE = """
You are the quality-review module of an autonomous BI agent.
Your job is to verify that the pipeline output correctly answers the original query.

## Original User Query
{query}

## Execution Plan That Was Followed
{plan_summary}

## Pipeline Output
- SQL Generated: {sql}
- Rows Returned: {row_count}
- Columns in Result: {columns}
- Sample Data (first 3 rows): {sample_data}
- Chart Type Generated: {chart_type}

## Review Criteria
1. Does the SQL logically answer the user's query?
2. Is there data returned (not empty)?
3. Is the chart type appropriate for the data structure?
4. Are the column names and data types coherent with the query intent?

Answer very briefly. If something is wrong, specify exactly what needs to change.
"""
```

---

### PASO 4 — Clase `AgentPlanner` (`planner.py`)

```python
class AgentPlanner:
    """
    Responsabilidad ÚNICA: Generar un AgentPlan a partir de una query
    usando Gemini Structured Output.
    """
    def __init__(self, api_key: str, model_name: str) -> None:
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    def plan(
        self,
        query: str,
        history: list[ConversationContext]
    ) -> AgentPlan:
        """
        Llama a Gemini con el PLANNING_PROMPT_TEMPLATE y retorna
        un AgentPlan validado por Pydantic.
        """
        prompt = PLANNING_PROMPT_TEMPLATE.format(
            query=query,
            history=self._format_history(history)
        )
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=AgentPlan,
        )
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=config
        )
        return AgentPlan(**json.loads(response.text))
```

---

### PASO 5 — Clase `OutputReviewer` (`reviewer.py`)

```python
class OutputReviewer:
    """
    Responsabilidad ÚNICA: Revisar el output del pipeline
    y determinar si pasa la validación de calidad.
    """
    def __init__(self, api_key: str, model_name: str) -> None:
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    def review(
        self,
        query: str,
        plan: AgentPlan,
        sql: str,
        df_result,     # pd.DataFrame
        chart_type: str | None
    ) -> ReviewResult:
        """
        Llama a Gemini con el REVIEW_PROMPT_TEMPLATE y retorna
        un ReviewResult con passed=True/False y feedback.
        """
        prompt = REVIEW_PROMPT_TEMPLATE.format(
            query=query,
            plan_summary=plan.query_interpretation,
            sql=sql,
            row_count=len(df_result),
            columns=", ".join(df_result.columns.tolist()),
            sample_data=df_result.head(3).to_dict(orient="records"),
            chart_type=chart_type or "not_generated_yet"
        )
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ReviewResult,
        )
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=config
        )
        return ReviewResult(**json.loads(response.text))
```

---

### PASO 6 — Refactor de `agent.py`

**Cambios en `__init__`:**
```python
# Añadir en __init__, luego del classifier:
self.planner  = AgentPlanner(api_key=..., model_name=...)
self.reviewer = OutputReviewer(api_key=..., model_name=...)
```

**Nuevo flujo en `_execute_data_pipeline`:**
```
ANTES:  _execute_data_pipeline(query)
         → text2sql → validate → execute → viz → return

DESPUÉS:
  1.  plan = self.planner.plan(query, history)
  2.  sql  = text2sql(query enriquecido con hints del plan)
  3.  validate SQL
  4.  df   = execute_sql(sql)
  5.  viz  = viz_agent(df, expected_chart_type=plan.expected_chart_type)
  6.  review = self.reviewer.review(query, plan, sql, df, viz.chart_type)
  7.  if review.passed: return success
  8.  else: log feedback + raise PipelineError con review.feedback
  9.  (futuro) si no passed: re-plan con review.feedback como contexto
```

**Logging enriquecido:**
```python
self.log.info(
    "plan_generated",
    plan_confidence=plan.confidence,
    plan_steps=len(plan.steps),
    expected_chart=plan.expected_chart_type
)
self.log.info(
    "review_completed",
    passed=review.passed,
    data_quality=review.data_quality_ok,
    viz_quality=review.viz_quality_ok,
    feedback=review.feedback
)
```

---

## Tareas de Implementación (Checklist)

### Fase 1: Modelos y Prompts
- [ ] T01 Agregar `PlanStep`, `AgentPlan`, `ReviewResult` en `models.py`
- [ ] T02 Crear `prompts/planning_prompt.py` con `PLANNING_PROMPT_TEMPLATE`
- [ ] T03 Crear `prompts/review_prompt.py` con `REVIEW_PROMPT_TEMPLATE`

### Fase 2: Nuevos Componentes
- [ ] T04 Implementar `planner.py` (clase `AgentPlanner` con Gemini Structured Output)
- [ ] T05 Implementar `reviewer.py` (clase `OutputReviewer` con Gemini Structured Output)

### Fase 3: Integración en el Agente
- [ ] T06 Extender `__init__` de `DecisionAgent` para instanciar planner y reviewer
- [ ] T07 Refactorizar `_execute_data_pipeline()` para el nuevo flujo PER
- [ ] T08 Pasar `plan.expected_chart_type` como hint al VizAgent
- [ ] T09 Loggear `plan_confidence`, `review_passed`, `review_feedback` con structlog

### Fase 4: Tests y Validación
- [ ] T10 Test unitario de `AgentPlanner.plan()` con Gemini mockeado
- [ ] T11 Test unitario de `OutputReviewer.review()` con Gemini mockeado
- [ ] T12 Test de integración del ciclo completo con la BD Chinook

---

## Consideraciones de Performance

> **Costo adicional**: El patrón PER añade **2 llamadas extra a Gemini** por request
> (Planning + Review). Con `gemini-2.5-flash` esto agrega ~1-2 segundos al pipeline.
> El límite de 15s definido en NFR-001 sigue siendo alcanzable.

> **Flash vs. Pro**: Usar `gemini-2.5-flash` para Planning y Review es suficiente.
> No es necesario subir a Pro solo por añadir estos pasos.

---

## Valor Académico de Este Cambio

Este refactor introduce formalmente los siguientes conceptos de investigación:

1. **Generación Aumentada por Recuperación con Planificación** (Plan-RAG)
2. **Auto-Reflexión de Agentes** (Self-Reflection / Reflexion Pattern)
3. **Structured Outputs como contrato entre módulos del agente**
4. **Pipelines Auto-Correctivos** basados en feedback del mismo LLM

En la defensa de tesis esto permite argumentar:
> *"El sistema no es un pipeline determinístico; incorpora un ciclo de planificación y
> auto-revisión que le permite detectar y comunicar inconsistencias entre la intención del
> usuario y el output generado, sin intervención de un operador humano."*
