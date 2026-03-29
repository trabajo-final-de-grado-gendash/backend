import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from api.models.schemas import ResultResponse
from api.dependencies import get_result_service

router = APIRouter(prefix="/api/v1", tags=["results"])

@router.get("/results/{result_id}", response_model=ResultResponse)
async def get_result(
    result_id: uuid.UUID,
    result_service: Any = Depends(get_result_service),
):
    """
    Retrieve a saved visualization result.
    """
    result = await result_service.get_result_by_id(result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
        
    return ResultResponse(
        result_id=result.id,
        query=result.query,
        sql=result.sql,
        plotly_json=result.viz_json,
        plotly_code=result.plotly_code,
        chart_type=result.chart_type,
        created_at=result.created_at
    )
