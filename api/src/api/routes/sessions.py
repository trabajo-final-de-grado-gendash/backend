import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from api.models.schemas import SessionHistoryResponse
from api.models.error_schemas import ErrorResponse
from api.dependencies import get_session_service

router = APIRouter(prefix="/api/v1", tags=["sessions"])

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
        raise HTTPException(status_code=404, detail="Session not found")
        
    messages = await session_service.get_full_history(session_id)
    return SessionHistoryResponse(
        session_id=session_id,
        messages=messages
    )
