"""
decision_agent — Agente decisor para Gen BI.

Clasifica intenciones del usuario con Gemini y orquesta el pipeline:
    NL query → VannaAgent (text2sql) → SQLValidator → execute_sql → VizAgent → Plotly JSON.
"""

__version__ = "0.1.0"
