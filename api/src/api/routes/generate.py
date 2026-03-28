import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from api.models.schemas import (
    GenerateRequest,
    GenerateResponse,
    ResponseType,
)
from api.dependencies import get_pipeline_service

router = APIRouter(prefix="/api/v1", tags=["generate"])

@router.post("/generate", response_model=GenerateResponse)
async def generate_visualization(
    request: GenerateRequest,
    pipeline_service: Any = Depends(get_pipeline_service),
):
    """
    Orchestrate the pipeline and return visualization.
    """
    session_id = request.session_id or uuid.uuid4()
    # Llamar al pipeline orquestador
    output = pipeline_service.run(
        query=request.query,
        session_id=session_id,
        conversation_history=None # Se llenará en la US6
    )
    
    # Parse output and convert to API model GenerateResponse
    plotly_json = None
    plotly_code = None
    
    if output.response_type == ResponseType.VISUALIZATION and output.viz_result:
        if hasattr(output.viz_result, "plotly_json"):
            plotly_json = output.viz_result.plotly_json
        elif isinstance(output.viz_result, dict):
            plotly_json = output.viz_result.get("plotly_json")
            
        if hasattr(output.viz_result, "plotly_code"):
            plotly_code = output.viz_result.plotly_code
        elif isinstance(output.viz_result, dict):
            plotly_code = output.viz_result.get("plotly_code")
    
    return GenerateResponse(
        response_type=output.response_type.value,
        session_id=session_id,
        message=output.message,
        plotly_json=plotly_json,
        sql=output.sql,
        plotly_code=plotly_code,
        result_id=None # Se llenará en la US5
    )
