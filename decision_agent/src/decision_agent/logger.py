"""
logger.py — Configuración de logging estructurado con structlog.

Emite JSON con los campos: agent, stage, session_id, elapsed_ms.
En caso de error añade: error_type, context.

Referencia: FR-008, NFR-003
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog


def configure_logging(log_level: str = "INFO") -> None:
    """
    Configura structlog para emitir JSON estructurado en stdout.

    Debe llamarse una única vez al iniciar el agente o la API.
    Si ya fue llamada, es idempotente (structlog aplica la config globalmente).
    """
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        # Final renderer: JSON en producción
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(log_level)


def get_logger(
    agent: str,
    *,
    session_id: str | None = None,
    stage: str | None = None,
) -> structlog.stdlib.BoundLogger:
    """
    Retorna un logger bound con los campos base: agent, stage, session_id.

    Uso:
        log = get_logger("decision_agent", session_id=str(session_id), stage="classify")
        log.info("intent_classified", category="valid_and_clear", elapsed_ms=120)
    """
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(agent)
    if session_id:
        logger = logger.bind(session_id=session_id)
    if stage:
        logger = logger.bind(stage=stage)
    return logger.bind(agent=agent)
