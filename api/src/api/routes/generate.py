import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException
from langsmith import traceable

from api.models.schemas import (
    GenerateRequest,
    GenerateResponse,
    ResponseType,
)
from api.models.error_schemas import ErrorResponse
from api.dependencies import get_pipeline_service, get_chart_service, get_session_service, get_settings, get_vector_service, get_db_session
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
@traceable(name="API.chat_endpoint", run_type="chain")
async def generate_visualization(
    request: GenerateRequest,
    pipeline_service: Any = Depends(get_pipeline_service),
    chart_service: Any = Depends(get_chart_service),
    session_service: Any = Depends(get_session_service),
    vector_service: Any = Depends(get_vector_service),
    db: Any = Depends(get_db_session),
):
    """
    Orchestrate the pipeline and return visualization.
    """
    session_id = request.session_id or uuid.uuid4()
    log.info("generate_request_started", session_id=str(session_id), query_len=len(request.query))

    # Obtener ventana de contexto
    settings = get_settings()
    history = await session_service.get_context_window(session_id, limit=settings.CONTEXT_WINDOW_SIZE)
    
    # 1. Intentar recuperación semántica (Cache con pgvector)
    cached_query = await vector_service.find_similar_query(db, request.query)
    
    if cached_query and cached_query.cached_response:
        log.info("full_cache_hit", session_id=str(session_id), cached_id=str(cached_query.id))
        
        # Save the USER conversation message
        await session_service.save_message(session_id=session_id, role=MessageRole.USER, content=request.query)
        
        # Prepare response from cache
        cached_data = cached_query.cached_response
        plotly_json = cached_data.get("plotly_json")
        plotly_code = cached_data.get("plotly_code")
        chart_type = cached_data.get("chart_type")
        
        # Create chart instance in this session
        chart_id = None
        if plotly_json:
            try:
                persisted_chart = await chart_service.save_chart(
                    session_id=session_id,
                    query=request.query,
                    sql=cached_query.sql or "",
                    viz_json=plotly_json,
                    plotly_code=plotly_code,
                    chart_type=chart_type
                )
                chart_id = persisted_chart.id
            except Exception as e:
                log.error("failed_to_save_cached_chart", error=str(e), session_id=str(session_id))
        
        # Save SYSTEM message to history
        await session_service.save_message(
            session_id=session_id, 
            role=MessageRole.SYSTEM, 
            content=cached_data.get("explanation") or f"Resultado recuperado de caché: {request.query}",
            response_type=cached_query.response_type or ResponseType.VISUALIZATION,
            chart_id=chart_id
        )
        
        return GenerateResponse(
            session_id=session_id,
            response_type=cached_query.response_type or ResponseType.VISUALIZATION,
            plotly_json=plotly_json,
            plotly_code=plotly_code,
            sql=cached_query.sql,
            message=cached_data.get("explanation"),
            chart_type=chart_type,
            chart_id=chart_id
        )

    cached_sql = cached_query.sql if cached_query else None
    
    if cached_sql:
        log.info("cache_hit_found", session_id=str(session_id), cached_id=str(cached_query.id))

    # Save the USER conversation message FIRST to ensure session is created
    try:
        await session_service.save_message(
            session_id=session_id, 
            role=MessageRole.USER, 
            content=request.query
        )
    except Exception as e:
        log.error("failed_to_save_user_message", error=str(e), session_id=str(session_id))

    # Llamar al pipeline orquestador
    try:
        output = pipeline_service.run(
            query=request.query,
            session_id=session_id,
            conversation_history=history,
            cached_sql=cached_sql
        )
    except Exception as e:
        log.error("pipeline_service_failed", error=str(e), session_id=str(session_id))
        
        # Generar mensaje de error explícito
        error_msg = "Hubo un problema al procesar tu consulta. Es posible que el sistema esté sobrecargado o la conexión haya fallado. Por favor, reintenta."
        
        e_str = str(e).lower()
        e_repr = repr(e).lower()
        if "503 unavailable" in e_str or "503 unavailable" in e_repr:
            error_msg = str(e)
        elif "timeout" in e_str or "timeout" in e_repr:
            error_msg = "La consulta tardó demasiado tiempo en procesarse. Por favor, intenta hacer una pregunta más específica o reintenta."
        elif "quota" in e_str or "429" in e_str or "exhausted" in e_str:
            error_msg = "El servicio de Inteligencia Artificial (Gemini) se ha quedado sin cuota. Por favor, intenta de nuevo más tarde."
        
        # Persistir el mensaje de error del SYSTEM
        try:
            await session_service.save_message(
                session_id=session_id,
                role=MessageRole.SYSTEM,
                content=error_msg,
                response_type=ResponseType.ERROR,
                chart_id=None
            )
        except Exception as db_err:
            log.error("failed_to_save_system_error_message", error=str(db_err), session_id=str(session_id))
            
        return GenerateResponse(
            response_type=ResponseType.ERROR.value,
            session_id=session_id,
            message=error_msg
        )
    
    # 2. Guardar en cache semántica si fue exitoso y no vino de cache
    if not cached_query and output.response_type == ResponseType.VISUALIZATION and output.sql:
        try:
            # Extraer los datos de visualización para cachear
            viz_data = {
                "plotly_json": getattr(output.viz_result, "plotly_json", None) if output.viz_result else None,
                "plotly_code": getattr(output.viz_result, "plotly_code", None) if output.viz_result else None,
                "explanation": output.message,
                "chart_type": getattr(output.viz_result, "chart_type", None) if output.viz_result else None
            }
            if isinstance(output.viz_result, dict):
                viz_data["plotly_json"] = output.viz_result.get("plotly_json")
                viz_data["plotly_code"] = output.viz_result.get("plotly_code")
                viz_data["chart_type"] = output.viz_result.get("chart_type")

            await vector_service.save_query_vector(
                db, 
                request.query, 
                output.sql, 
                cached_response=viz_data,
                response_type=output.response_type
            )
            log.info("query_cached", session_id=str(session_id))
        except Exception as e:
            log.error("failed_to_cache_query", error=str(e))
    
    # USER message was saved before the pipeline run
    
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

    # Save SYSTEM message (assistant response), now with chart_id if available
    try:
        content_to_save = output.message or "Aquí tienes la visualización generada."
        log.info("saving_assistant_message", session_id=str(session_id), content_preview=content_to_save[:50])
        await session_service.save_message(
            session_id=session_id,
            role=MessageRole.SYSTEM,
            content=content_to_save,
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
