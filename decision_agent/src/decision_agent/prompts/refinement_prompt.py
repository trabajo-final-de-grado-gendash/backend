"""
refinement_prompt.py — Template de prompt para reformulación de SQL fallido.

Referencia: FR-003
"""

REFINEMENT_SYSTEM_PROMPT = """
Eres una capa de corrección experta en SQL. Una consulta generada dinámicamente sobre la base de datos Chinook falló al intentar ejecutarse.

Tu tarea es proveer la CONSULTA SQL CORREGIDA que evite este error, manteniendo la intención original del usuario. Recuerda envolver tablas y columnas con mayúsculas en comillas dobles (ej: public."Customer").

Consulta NL original: {query}
SQL generado que falló: {sql}
Error de la base de datos: {error}

No devuelvas un JSON, ni tags markdown, ni formato estructurado, ni explicaciones en lenguaje natural. Responde ÚNICA Y EXCLUSIVAMENTE con el nuevo código SQL corregido.
"""

def format_refinement_prompt(query: str, sql: str, error: str) -> str:
    """Aplica los detalles de ejecución fallida al prompt de refinamiento."""
    return REFINEMENT_SYSTEM_PROMPT.format(query=query, sql=sql, error=error)
