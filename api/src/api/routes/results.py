import uuid

from fastapi import APIRouter, HTTPException

from api.models.schemas import ResultResponse

router = APIRouter(prefix="/api/v1", tags=["results"])

@router.get("/results/{result_id}", response_model=ResultResponse)
async def get_result(result_id: uuid.UUID):
    """
    Retrieve a saved visualization result.
    """
    # Stub: Delegate to result_service once US5 is complete
    # For now, return a 404 since it's not implemented yet
    raise HTTPException(status_code=404, detail="Result not found")
