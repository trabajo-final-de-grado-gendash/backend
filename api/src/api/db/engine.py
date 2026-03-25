"""
db/engine.py — Async engine de SQLAlchemy y session factory.

Referencia: data-model.md §Configuración de Base de Datos, plan.md §API
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from api.config import Settings

# Módulo-level singletons (inicializados bajo demanda o en lifespan)
_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine(settings: Settings | None = None) -> AsyncEngine:
    """
    Retorna (o crea) el motor async global.

    El primer llamado inicializa el engine. Los subsiguientes retornan
    el mismo objeto (singleton a nivel de proceso).
    """
    global _engine
    if _engine is None:
        if settings is None:
            settings = Settings()  # type: ignore[call-arg]
        _engine = create_async_engine(
            settings.DATABASE_URL,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            echo=False,
        )
    return _engine


def get_session_factory(settings: Settings | None = None) -> async_sessionmaker[AsyncSession]:
    """Retorna (o crea) la factory de sessions."""
    global _async_session_factory
    if _async_session_factory is None:
        engine = get_engine(settings)
        _async_session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_factory


async def dispose_engine() -> None:
    """Cierra el pool de conexiones. Llamar en el shutdown del lifespan."""
    global _engine, _async_session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _async_session_factory = None


async def get_async_session(
    settings: Settings | None = None,
) -> AsyncGenerator[AsyncSession, None]:
    """
    Generador async para uso directo (no como dependencia FastAPI).

    Uso:
        async for session in get_async_session():
            result = await session.execute(...)
    """
    factory = get_session_factory(settings)
    async with factory() as session:
        yield session
