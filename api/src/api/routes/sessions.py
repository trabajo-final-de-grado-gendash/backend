import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException

from api.models.schemas import SessionHistoryResponse, SessionListResponse
from api.models.error_schemas import ErrorResponse
from api.dependencies import get_session_service

log = structlog.get_logger("api.routes.sessions")

router = APIRouter(prefix="/api/v1", tags=["sessions"])

@router.get(
    "/sessions",
    response_model=SessionListResponse,
)
async def get_all_sessions(
    session_service: Any = Depends(get_session_service)
):
    """
    Retrieve a list of all sessions with their first message as title.
    """
    sessions = await session_service.get_all_sessions()
    return SessionListResponse(sessions=sessions)


@router.get(
    "/sessions/{session_id}/history", 
    response_model=SessionHistoryResponse,
    responses={404: {"model": ErrorResponse, "description": "Sesión no encontrada"}}
)
async def get_session_history(
    session_id: uuid.UUID,
    session_service: Any = Depends(get_session_service)
):
    """
    Retrieve message history for a session.
    """
    session = await session_service.get_session(session_id)
    if not session:
        log.warning("session_not_found", session_id=str(session_id))
        raise HTTPException(status_code=404, detail="Session not found")
        
    messages = await session_service.get_full_history(session_id)
    return SessionHistoryResponse(
        session_id=session_id,
        messages=messages
    )


@router.delete(
    "/sessions/{session_id}",
    responses={
        200: {"description": "Sesión eliminada correctamente"},
        404: {"model": ErrorResponse, "description": "Sesión no encontrada"}
    }
)
async def delete_session(
    session_id: uuid.UUID,
    session_service: Any = Depends(get_session_service)
):
    """
    Delete a session and all its associated data.
    """
    deleted = await session_service.delete_session(session_id)
    if not deleted:
        log.warning("session_not_found_for_deletion", session_id=str(session_id))
        raise HTTPException(status_code=404, detail="Session not found")
        
    return {"message": "Session deleted successfully"}
