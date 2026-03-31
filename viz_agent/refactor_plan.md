# Implementation Plan: Refactor y Unificación de Viz Agent 2.0

**Branch**: `TFG-42-refactor-viz-agent` (propuesto) | **Date**: 2026-03-29 | **Related**: [spec.md](./spec.md), [plan.md](./plan.md)

## Summary

Refactorizar el módulo `viz_agent` para unificar su arquitectura técnica con la del `DecisionAgent` y la `API`. El objetivo es estandarizar los entry-points (`run`), el sistema de logging (`structlog`), la jerarquía de excepciones y cumplir con los requisitos pendientes de subplots y validación de datos nulos.

---

## 1. Alineación Arquitectónica (Unificación)

### 1.1 Entry-point Consistente (FR-013 Refactor)
- **Cambio**: Renombrar `VizAgent.generate_visualization` a `VizAgent.run`.
- **Firma**: `run(self, input_data: VizAgentInput) -> VizAgentOutput`
- **Impacto**: Permite que el `PipelineService` consuma todos los agentes bajo una interfaz común (`AgentProtocol`).

### 1.2 Jerarquía de Excepciones Unificada (Principio IV)
- **Archivo**: `viz_agent/src/viz_agent/exceptions.py`
- **Modelos**:
    - `VizAgentError(Exception)`: Clase base.
    - `VizLLMError(VizAgentError)`: Fallos en comunicación/formato de Gemini.
    - `VizExecutionError(VizAgentError)`: Agotados los 5 reintentos de corrección.
    - `InvalidDataError(VizAgentError)`: DataFrame vacío o ilegible.

### 1.3 Logging Estructurado (Principio IV)
- **Implementación**: Migrar `VizAgentLogger` de `logging.FileHandler` a **`structlog`**.
- **Contexto**: Inyectar `agent="viz_agent"` en todos los eventos.
- **Campos mandatorios**: `stage`, `elapsed_ms`, `attempt`, `chart_type`.

### 1.4 Modernización Pydantic (Principio V)
- **Cambio**: Reemplazar `class Config` por `model_config = ConfigDict(arbitrary_types_allowed=True)` en `models.py`.

---

## 2. Cumplimiento de Especificaciones (Gaps)

### 2.1 Soporte para Subplots (User Story 3 / Priority P3)
- **Prompt**: Actualizar `decision_prompt.py` para incluir instrucciones sobre `plotly.subplots.make_subplots`.
- **Validación**: Mejorar `_extract_figure` en `validator.py` para asegurar que el objeto retornado (fig o subplot) sea capturado correctamente.
- **Lógica**: Si el `user_request` implica múltiples comparaciones, incentivar el uso de subplots.

### 2.2 Validación de Datos Nulos (Edge Case / Priority P2)
- **Cambio**: En `analyzer.py`, añadir el método `check_data_viability()`.
- **Acción**: Si todas las columnas numéricas tienen 100% de nulos, lanzar `InvalidDataError` antes de invocar al LLM.

---

## 3. Estructura de Archivos (Post-Refactor)

```text
backend/viz_agent/
└── src/
    └── viz_agent/
        ├── exceptions.py       # NUEVO: Jerarquía de errores
        ├── agent.py            # REFACTOR: Método run() + Catch exceptions
        ├── logger.py           # REFACTOR: Migración a structlog
        ├── models.py           # REFACTOR: Pydantic ConfigDict
        └── analyzer.py         # REFACTOR: check_data_viability()
```

---

## 4. Tareas Técnicas (Checklist para Implementación)

### Fase 1: Estructura y Estándares
- [ ] T01 Implementar `exceptions.py` con la jerarquía acordada.
- [ ] T02 Migrar `models.py` a Pydantic 2 `ConfigDict`.
- [ ] T03 Refactorizar `logger.py` para usar `structlog` (output JSON).

### Fase 2: Lógica del Agente
- [ ] T04 Renombrar `generate_visualization` a `run()`.
- [ ] T05 Implementar el chequeo de "viabilidad de datos" en `analyzer.py` (nulos/vacíos).
- [ ] T06 Integrar el manejo de excepciones en el loop de corrección de `agent.py`.

### Fase 3: Potenciación del Prompt y Validación
- [ ] T07 Actualizar `DECISION_PROMPT_TEMPLATE` con instrucciones de subplots.
- [ ] T08 Refactorizar `CodeValidator` para mejor detección de figuras complejas.

### Fase 4: Tests y Documentación
- [ ] T09 Actualizar `examples/basic_usage.py` con la nueva firma `run()`.
- [ ] T10 Corregir los tests unitarios afectados por el renombre de métodos.
