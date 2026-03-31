"""
basic_usage.py — Smoke test de consola para vanna_agent.

Ejecutar: uv run python examples/basic_usage.py
"""

import time
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def main() -> None:
    print("=" * 60)
    print("Gen BI — Vanna Agent Smoke Test")
    print("=" * 60)

    from vanna_agent.config import Settings
    from vanna_agent.agent import VannaAgent

    settings = Settings()  # type: ignore[call-arg]
    print(f"[config] GEMINI_MODEL  : {settings.GEMINI_MODEL}")
    print(f"[config] SOURCE_DB_URL: {settings.SOURCE_DB_URL[:30]}...")
    print()

    agent = VannaAgent(settings=settings)
    query = "total de ventas (sumar la columna Total de la tabla Invoice)"
    print(f"[query] {query!r}")

    t0 = time.perf_counter()
    sql_result = agent.text_to_sql(query)
    elapsed_sql = time.perf_counter() - t0

    print(f"[text_to_sql] success : {sql_result.success}")
    print(f"[text_to_sql] sql     : {sql_result.sql}")
    if sql_result.error:
        print(f"[text_to_sql] error   : {sql_result.error}")
    print(f"[text_to_sql] elapsed : {elapsed_sql:.2f}s")
    print()

    if sql_result.success and sql_result.sql:
        t1 = time.perf_counter()
        df = agent.execute_sql(sql_result.sql)
        elapsed_exec = time.perf_counter() - t1
        print(f"[execute_sql] rows    : {len(df)}")
        print(f"[execute_sql] columns : {list(df.columns)}")
        print(f"[execute_sql] elapsed : {elapsed_exec:.2f}s")
        print()
        print(df.head())

    print()
    print("✅ Smoke test completado")
    print("=" * 60)


if __name__ == "__main__":
    main()
