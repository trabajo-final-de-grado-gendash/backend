"""
main.py — Factory de la app FastAPI.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import Settings
from api.db.engine import dispose_engine, get_engine
from api.routes import health, generate, sessions, results

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings = Settings()
    get_engine(settings)
    yield
    # Shutdown
    await dispose_engine()

def create_app() -> FastAPI:
    settings = Settings()
    
    app = FastAPI(
        title="GenBI API",
        description="Agente Decisor y API de Orquestación para Gen BI",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Configurar CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Incluir routers
    app.include_router(health.router)
    app.include_router(generate.router)
    app.include_router(sessions.router)
    app.include_router(results.router)

    return app

app = create_app()
