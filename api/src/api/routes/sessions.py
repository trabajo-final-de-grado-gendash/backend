import uuid

from fastapi import APIRouter, HTTPException

from api.models.schemas import SessionHistoryResponse, MessageItem

router = APIRouter(prefix="/api/v1", tags=["sessions"])

@router.get("/sessions/{session_id}/history", response_model=SessionHistoryResponse)
async def get_session_history(session_id: uuid.UUID):
    """
    Retrieve message history for a session.
    """
    # Stub: Delegate to session_service once US6 is complete
    # For now, return a 404 since it's not implemented yet in the MVP scope
    raise HTTPException(status_code=404, detail="Session not found")
