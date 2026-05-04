import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException

from api.models.schemas import (
    GenerateRequest,
    GenerateResponse,
    ResponseType,
)
from api.models.error_schemas import ErrorResponse
from api.dependencies import get_pipeline_service, get_chart_service, get_session_service, get_settings
from decision_agent.models import MessageRole

log = structlog.get_logger("api.routes.generate")

router = APIRouter(prefix="/api/v1", tags=["generate"])

@router.post(
    "/generate", 
    response_model=GenerateResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Error de validación (SQL prohibido)"},
        500: {"model": ErrorResponse, "description": "Error interno del pipeline (Timeout/LLM)"},
        503: {"model": ErrorResponse, "description": "Error de base de datos"},
    }
)
async def generate_visualization(
    request: GenerateRequest,
    pipeline_service: Any = Depends(get_pipeline_service),
    chart_service: Any = Depends(get_chart_service),
    session_service: Any = Depends(get_session_service),
):
    """
    Orchestrate the pipeline and return visualization.
    """
    session_id = request.session_id or uuid.uuid4()
    log.info("generate_request_started", session_id=str(session_id), query_len=len(request.query))

    # Obtener ventana de contexto
    settings = get_settings()
    history = await session_service.get_context_window(session_id, limit=settings.CONTEXT_WINDOW_SIZE)
    
    # Llamar al pipeline orquestador
    output = pipeline_service.run(
        query=request.query,
        session_id=session_id,
        conversation_history=history
    )
    
    # Save the USER conversation message
    try:
        await session_service.save_message(
            session_id=session_id, 
            role=MessageRole.USER, 
            content=request.query
        )
    except Exception as e:
        log.error("failed_to_save_user_message", error=str(e), session_id=str(session_id))
    
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

    chart_type = None
    if output.viz_result:
        if hasattr(output.viz_result, "chart_type"):
            chart_type = output.viz_result.chart_type
        elif isinstance(output.viz_result, dict):
            chart_type = output.viz_result.get("chart_type")

    chart_id = None
    if output.response_type == ResponseType.VISUALIZATION and plotly_json:
        try:
            persisted_chart = await chart_service.save_chart(
                session_id=session_id,
                query=request.query,
                sql=output.sql or "",
                viz_json=plotly_json,
                plotly_code=plotly_code,
                chart_type=chart_type
            )
            chart_id = persisted_chart.id
        except Exception as e:
            log.error("failed_to_save_chart", error=str(e), session_id=str(session_id))

    # Save SYSTEM message, now with chart_id if available
    try:
        content_to_save = output.sql if output.response_type == ResponseType.VISUALIZATION else output.message
        await session_service.save_message(
            session_id=session_id,
            role=MessageRole.SYSTEM,
            content=content_to_save or "(No content)",
            response_type=output.response_type,
            chart_id=chart_id
        )
    except Exception as e:
        log.error("failed_to_save_system_message", error=str(e), session_id=str(session_id))

    log.info(
        "generate_request_completed",
        session_id=str(session_id),
        response_type=output.response_type.value,
        chart_id=str(chart_id) if chart_id else None,
    )
    return GenerateResponse(
        response_type=output.response_type.value,
        session_id=session_id,
        message=output.message,
        plotly_json=plotly_json,
        sql=output.sql,
        plotly_code=plotly_code,
        chart_type=chart_type,
        chart_id=chart_id
    )
