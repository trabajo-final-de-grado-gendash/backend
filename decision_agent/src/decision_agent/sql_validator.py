"""
sql_validator.py — Validación de sentencias SQL generadas por LLMs.

Aplica política de exclusión de palabras clave DDL/DML y lanza
SQLValidationError para cualquier cosa que no sea un SELECT puro.

Referencia: FR-004, FR-024, NFR-007
"""

from __future__ import annotations

import sqlparse
import structlog

from decision_agent.exceptions import SQLValidationError
from decision_agent.logger import get_logger


class SQLValidator:
    """Validador de SQL que solo permite operaciones de lectura segura (SELECT)."""

    # Diccionario explícito de keywords destructivas por seguridad profunda
    # Más allá del parseo de sentencia base, si la query contiene estas palabras clave,
    # se bloqueará su ejecución.
    BLOCKED_KEYWORDS: set[str] = {
        "DELETE",
        "DROP",
        "UPDATE",
        "INSERT",
        "ALTER",
        "TRUNCATE",
        "CREATE",
        "REPLACE",
        "GRANT",
        "REVOKE",
        "UPSERT",
        "MERGE",
        "EXEC",
        "EXECUTE",
    }

    def __init__(self, logger: structlog.stdlib.BoundLogger | None = None) -> None:
        self.log = logger or get_logger("decision_agent", stage="validate_sql")

    def validate(self, sql: str) -> None:
        """
        Analiza la sentencia SQL provista y comprueba sus características.
        
        Args:
            sql: Cadena de código SQL generada por Text2SQL.
            
        Raises:
            SQLValidationError si contiene sentencias prohibidas.
        """
        if not sql or not sql.strip():
            self.log.warning("empty_sql_validation")
            raise SQLValidationError("La consulta SQL recibida está vacía.", sql=sql)

        # 1. Validación rígida con la librería sqlparse (Statement level)
        parsed_statements = sqlparse.parse(sql)
        if not parsed_statements:
            self.log.warning("failed_sql_parsing", sql=sql)
            raise SQLValidationError("No fue posible interpretar o desempaquetar el SQL.", sql=sql)

        for stmt in parsed_statements:
            stmt_type = stmt.get_type()
            # Permitimos bloqueos extraños/vacíos parseados o sentencias puramente descriptivas,
            # pero bloqueamos cualquier acción de escritura detectada ("INSERT/UPDATE/DELETE").
            # Para mayor estrictez (FR-024), requerimos explícitamente el SELECT form o WITH CTE.
            if stmt_type.upper() not in {"SELECT", "UNKNOWN"}:
                self.log.warning(
                    "blocked_sql_operation",
                    sql=sql,
                    statement_type=stmt_type,
                )
                raise SQLValidationError(
                    f"Operación no permitida: {stmt_type}. Se requiere una sentencia SELECT pura.",
                    sql=sql,
                )

        # 2. Validación lexicográfica (Keyword level)
        # Parseamos tokens planos para prevenir inyecciones disfuncionales dentro del SELECT.
        # token.value es la cadena pura de texto parseada.
        tokens_upper = {
            t.value.upper()
            for stmt in parsed_statements
            for t in stmt.flatten()
            if not t.is_whitespace
        }

        for blocked_kw in self.BLOCKED_KEYWORDS:
            if blocked_kw in tokens_upper:
                self.log.warning("blocked_sql_keyword", sql=sql, keyword=blocked_kw)
                raise SQLValidationError(
                    f"Palabra clave de modificación destructiva prohibida hallada en la consulta: {blocked_kw}. Transacción truncada por seguridad.",
                    sql=sql,
                )

        self.log.debug("sql_validated_successfully")
