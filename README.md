# BIGENIA - Backend

El backend de BIGENIA consta de un orquestador principal (API FastAPI) y múltiples subagentes especializados, que juntos forman el sistema Generativo de Business Intelligence.

## Arquitectura de Agentes

1. **DecisionAgent**: Interpreta la intención del usuario y clasifica la consulta.
2. **VannaAgent**: Toma consultas en lenguaje natural y genera sentencias SQL precisas usando técnicas de Text-to-SQL.
3. **VizAgent**: Recibe los datos y genera código en Python (Plotly) para renderizar visualizaciones ricas y dinámicas.
4. **API Orchestrator**: Unifica el flujo (Pipeline), controla el estado (caché vectorial) e interactúa con el cliente web.

## Trazabilidad y Observabilidad con LangSmith

El proyecto está integrado completamente con **LangSmith**, lo que permite rastrear, depurar y monitorear el comportamiento de las llamadas a Google Gemini y las interacciones de los agentes.

### ¿Cómo funciona la trazabilidad aquí?

Utilizamos dos métodos de integración complementarios de la librería `langsmith`:

1. **Decorador `@traceable` (Trazabilidad a Nivel Lógico)**:
   - Los métodos de entrada de los agentes (`DecisionAgent.classify`, `VannaAgent.text_to_sql`, `VizAgent.decide_and_generate_code`, etc.) y el router principal de la API (`API.chat_endpoint`) están decorados con `@traceable(run_type="chain")`.
   - Esto permite que LangSmith agrupe todas las subllamadas bajo un solo "Trace" (Traza) padre de la request del usuario. Permite ver inputs reales (strings, JSONs) y los outputs validados (modelos Pydantic).
   - También se usa en operaciones clave que no son LLM (como `execute_sql` con `run_type="tool"`) para monitorear latencias y tiempos de respuesta de la base de datos.

2. **Wrapper `wrappers.wrap_gemini` (Trazabilidad a Nivel LLM)**:
   - Al instanciar los clientes de Google GenAI (`genai.Client`) en el DecisionAgent y el VizAgent, usamos la función envoltorio.
   - Esto inyecta automáticamente en LangSmith cada petición HTTP hacia Gemini. Muestra de manera granular la cantidad exacta de **Tokens** consumidos (input y output), la temperatura, el System Prompt y el Payload crudo intercambiado.

> **Sinergia:** Gracias a ambos métodos, en el dashboard de LangSmith verás el flujo completo ordenado jerárquicamente. Por ejemplo, dentro de `API.chat_endpoint` -> verás `DecisionAgent.classify` -> y dentro, la llamada de red `gemini-2.5-flash` con sus tokens.

### Configuración (Variables de Entorno)

Para activar LangSmith, el sistema lee automáticamente las variables de entorno desde el `.env` (siempre que la API Key esté configurada). Asegúrate de tener estas líneas en el archivo `.env` del backend:

```env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT="https://api.smith.langchain.com"
LANGCHAIN_API_KEY="ls__tu_api_key_aqui"
LANGCHAIN_PROJECT="bigenia-agents"
```

> **Nota:** Todos los agentes (`decision_agent`, `viz_agent`, `vanna_agent`) y la `api` ya incluyen la dependencia de `langsmith`.