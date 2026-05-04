import time

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from api.models.schemas import HealthResponse, ComponentHealth
from api.dependencies import get_db_session

log = structlog.get_logger("api.routes.health")

router = APIRouter(prefix="/api/v1", tags=["health"])

@router.get("/health", response_model=HealthResponse)
async def health_check(session: AsyncSession = Depends(get_db_session)):
    """
    Check system health and components.
    """
    components = {}
    
    # Check Database
    start_time = time.time()
    db_status = "down"
    try:
        await session.execute(text("SELECT 1"))
        db_status = "up"
    except Exception as exc:
        log.warning("health_check_db_failed", error=str(exc))
    db_latency = (time.time() - start_time) * 1000
    components["database"] = ComponentHealth(status=db_status, latency_ms=db_latency)
    
    # Note: decision_agent, vanna_agent, viz_agent, chinook_db
    # To be properly hooked up in US4/US5.
    for comp in ["decision_agent", "vanna_agent", "viz_agent", "chinook_db"]:
        components[comp] = ComponentHealth(status="up", latency_ms=1.0)
    
    overall_status = "healthy"
    if any(c.status == "down" for c in components.values()):
        overall_status = "degraded"
        if components["database"].status == "down":
            overall_status = "unhealthy"

    return HealthResponse(status=overall_status, components=components)
