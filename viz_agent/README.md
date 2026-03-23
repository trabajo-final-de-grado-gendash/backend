# Viz Agent - Agente de Visualización con Gemini AI

Agente de visualización inteligente que genera gráficos Plotly automáticamente usando Gemini AI.

## Características

- 🤖 Generación automática de visualizaciones con Gemini 2.5 Flash
- 📊 Soporte para múltiples tipos de gráficos (bar, line, pie, scatter, histogram, heatmap, box)
- 🔄 Auto-corrección de código con hasta 5 intentos
- ✅ Validación automática de código generado
- 📝 Logging detallado de decisiones y errores
- 🎨 Personalización de estilos y colores

## Instalación

### Requisitos

- Python >= 3.10
- uv package manager

### Setup

```bash
# Clonar el repositorio
git clone <repo-url>
cd viz-agent

# Instalar uv (si no lo tienes)
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env

# Crear entorno virtual e instalar dependencias
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tu GEMINI_API_KEY
```

## Uso Básico

```python
import pandas as pd
from viz_agent.agent import VizAgent
from viz_agent.models import VizAgentInput
from viz_agent.config import Config

# Configurar agente
config = Config.from_env()
agent = VizAgent(config)

# Preparar datos
df = pd.DataFrame({
    'categoria': ['A', 'B', 'C', 'D'],
    'valor': [10, 25, 15, 30]
})

# Generar visualización
input_data = VizAgentInput(
    dataframe=df,
    user_request="gráfico de barras de ventas por categoría"
)

result = agent.generate_visualization(input_data)

if result.success:
    print(f"✅ Gráfico generado: {result.chart_type}")
    print(result.plotly_code)
else:
    print(f"❌ Error: {result.error_message}")
```

## Testing

```bash
# Ejecutar todos los tests
pytest tests/ -v

# Con coverage
pytest tests/ -v --cov=viz_agent --cov-report=html

# Solo tests de un módulo
pytest tests/test_analyzer.py -v
```

## Estructura del Proyecto

```
viz_agent/
├── __init__.py
├── agent.py           # Agente principal
├── models.py          # Modelos Pydantic
├── analyzer.py        # Análisis de DataFrames
├── gemini_client.py   # Cliente Gemini AI
├── validator.py       # Validación de código
├── logger.py          # Sistema de logging
├── config.py          # Configuración
├── prompts/           # Templates de prompts
└── utils/             # Utilidades

tests/                 # Tests completos
examples/              # Ejemplos de uso
```

## Licencia

MIT
