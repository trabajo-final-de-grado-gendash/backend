"""
dependencies.py — Dependencias de FastAPI para inyección general.
"""

from collections.abc import AsyncGenerator
from typing import Any

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import Settings
from api.db.engine import get_async_session

def get_settings() -> Settings:
    return Settings()

async def get_db_session(
    settings: Settings = Depends(get_settings),
) -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session via dependency injection."""
    async for session in get_async_session(settings):
        yield session

def get_pipeline_service() -> Any:
    """
    Provide the pipeline service via dependency injection.
    """
    from api.services.pipeline_service import PipelineService
    return PipelineService()


def get_chart_service(db: AsyncSession = Depends(get_db_session)) -> Any:
    """Provide the chart service via dependency injection."""
    from api.services.chart_service import ChartService
    return ChartService(db)

def get_session_service(db: AsyncSession = Depends(get_db_session)) -> Any:
    """Provide the session service via dependency injection."""
    from api.services.session_service import SessionService
    return SessionService(db)

def get_project_service(db: AsyncSession = Depends(get_db_session)) -> Any:
    """Provide the project service via dependency injection."""
    from api.services.project_service import ProjectService
    return ProjectService(db)
