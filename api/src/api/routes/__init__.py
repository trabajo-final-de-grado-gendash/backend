"""
routes/__init__.py — Registro centralizado de endpoints bajo prefix /api/v1.
"""
from fastapi import APIRouter

from .health import router as health_router
from .generate import router as generate_router
from .sessions import router as sessions_router
from .charts import router as charts_router
from .projects import router as projects_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(generate_router)
api_router.include_router(sessions_router)
api_router.include_router(charts_router)
api_router.include_router(projects_router)
