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
    
    from fastapi import Request
    from fastapi.responses import JSONResponse
    from decision_agent.exceptions import SQLValidationError, PipelineError
    from sqlalchemy.exc import DBAPIError

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

    # Exception Handlers
    @app.exception_handler(SQLValidationError)
    async def sql_validation_exception_handler(request: Request, exc: SQLValidationError):
        return JSONResponse(
            status_code=400,
            content={"error_type": exc.error_type, "message": exc.message, "context": exc.context}
        )

    @app.exception_handler(PipelineError)
    async def pipeline_exception_handler(request: Request, exc: PipelineError):
        return JSONResponse(
            status_code=500,
            content={"error_type": exc.error_type, "message": exc.message, "context": exc.context}
        )

    @app.exception_handler(DBAPIError)
    async def db_exception_handler(request: Request, exc: DBAPIError):
        return JSONResponse(
            status_code=503,
            content={
                "error_type": "database_error",
                "message": "Fallo de conexión o consulta de base de datos.",
                "context": {"detail": str(exc.orig) if hasattr(exc, "orig") else str(exc)}
            }
        )

    # Incluir routers
    from api.routes import api_router
    app.include_router(api_router)

    return app

app = create_app()
