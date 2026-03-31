"""
basic_usage.py — Smoke test de consola para decision_agent.

Ejecutar: uv run python examples/basic_usage.py
"""

import time
import os
import sys

# Añadir src al path para ejecución directa
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
# Añadir carpetas de los otros agentes a sys.path (para el smoke test)
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(root_dir, "vanna_agent", "src"))
sys.path.insert(0, os.path.join(root_dir, "viz_agent", "src"))


def main() -> None:
    print("=" * 60)
    print("Gen BI — Decision Agent Smoke Test")
    print("=" * 60)

    from decision_agent.config import Settings
    from decision_agent.agent import DecisionAgent
    from decision_agent.models import DecisionAgentInput

    settings = Settings()  # type: ignore[call-arg]
    print(f"[config] GEMINI_MODEL  : {settings.GEMINI_MODEL}")
    print(f"[config] SOURCE_DB_URL: {settings.SOURCE_DB_URL[:30]}...")
    print()

    from vanna_agent.agent import VannaAgent
    from vanna_agent.config import Settings as VannaSettings
    from viz_agent.agent import VizAgent
    from viz_agent.config import Config as VizConfig

    vanna_agent = VannaAgent(settings=VannaSettings())
    viz_agent = VizAgent(config=VizConfig(gemini_api_key=settings.GEMINI_API_KEY))

    agent = DecisionAgent(
        settings=settings,
        text2sql_agent=vanna_agent,
        viz_agent=viz_agent
    )

    query = "total de ventas por país del cliente"
    print(f"[query] {query!r}")
    print()

    t0 = time.perf_counter()
    result = agent.run(
        DecisionAgentInput(
            query=query,
            conversation_history=[],
        )
    )
    elapsed = time.perf_counter() - t0

    print(f"[result] response_type : {result.response_type}")
    print(f"[result] sql           : {result.sql}")
    print(f"[result] message       : {result.message}")
    if result.viz_result:
        if hasattr(result.viz_result, "plotly_code"):
            print(f"\n[result] plotly_code   :\n{result.viz_result.plotly_code[:500]}...\n")
        if hasattr(result.viz_result, "plotly_json"):
            print(f"[result] plotly_json   : Generado correctamente.")
            
            # Guardar el JSON real para que load_from_json.py pueda leerlo
            import os
            out_path = os.path.join(os.path.dirname(__file__), "..", "..", "viz_agent", "examples", "output.json")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(result.viz_result.plotly_json)
            print(f"👉 JSON de la visualización guardado en: {os.path.abspath(out_path)}")
            print(result.viz_result)
    print(f"[result] metadata      : {result.metadata}")
    print()
    print(f"✅ Pipeline completado en {elapsed:.2f}s")
    print("=" * 60)


if __name__ == "__main__":
    main()
