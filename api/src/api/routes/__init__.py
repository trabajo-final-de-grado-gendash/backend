"""
routes/__init__.py — Registro centralizado de endpoints bajo prefix /api/v1.
"""
from fastapi import APIRouter

from .health import router as health_router
from .generate import router as generate_router
from .sessions import router as sessions_router
from .results import router as results_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(generate_router)
api_router.include_router(sessions_router)
api_router.include_router(results_router)
