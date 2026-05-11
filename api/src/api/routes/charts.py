"""
routes/charts.py — Endpoints para consulta y edición de gráficos.

Endpoints:
- GET  /api/v1/charts/{chart_id}            — Obtener un gráfico existente
- PATCH /api/v1/charts/{chart_id}/metadata   — TFG-56: Actualizar metadata del gráfico
- POST  /api/v1/charts/{chart_id}/regenerate — TFG-57: Regenerar gráfico con prompt
"""

import asyncio
import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException
from langsmith import traceable
from api.models.schemas import (
    RegenerateChartRequest,
    RegenerateChartResponse,
    ChartResponse,
    UpdateMetadataRequest,
    UpdateMetadataResponse,
)
from api.models.error_schemas import ErrorResponse
from api.dependencies import get_pipeline_service, get_chart_service, get_session_service, get_settings
from decision_agent.models import MessageRole, ResponseType

log = structlog.get_logger("api.routes.charts")

router = APIRouter(prefix="/api/v1", tags=["charts"])

@router.get(
    "/charts",
    response_model=list[ChartResponse],
)
async def get_all_charts(
    chart_service: Any = Depends(get_chart_service),
):
    """
    Retrieve all saved visualization charts across all projects.
    """
    charts = await chart_service.get_all_charts()
    return [
        ChartResponse(
            chart_id=r.id,
            query=r.query,
            sql=r.sql,
            plotly_json=r.viz_json,
            plotly_code=r.plotly_code,
            chart_type=r.chart_type,
            project_id=r.project_id,
            created_at=r.created_at
        ) for r in charts
    ]


@router.get(
    "/charts/{chart_id}", 
    response_model=ChartResponse,
    responses={404: {"model": ErrorResponse, "description": "Gráfico no encontrado"}}
)
async def get_chart(
    chart_id: uuid.UUID,
    chart_service: Any = Depends(get_chart_service),
):
    """
    Retrieve a saved visualization chart.
    """
    chart = await chart_service.get_chart_by_id(chart_id)
    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")
        
    return ChartResponse(
        chart_id=chart.id,
        query=chart.query,
        sql=chart.sql,
        plotly_json=chart.viz_json,
        plotly_code=chart.plotly_code,
        chart_type=chart.chart_type,
        project_id=chart.project_id,
        created_at=chart.created_at
    )


@router.patch(
    "/charts/{chart_id}/metadata", 
    response_model=UpdateMetadataResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Gráfico no encontrado"},
        422: {"description": "Error de validación de campos"}
    }
)
async def update_chart_metadata(
    chart_id: uuid.UUID,
    request: UpdateMetadataRequest,
    chart_service: Any = Depends(get_chart_service),
):
    """
    Actualizar metadata del gráfico (título, ejes).

    Hace un merge parcial sobre viz_json.layout con los campos proporcionados.
    Solo se actualizan los campos que se envían en el body.
    """
    # Validar que al menos un campo fue proporcionado
    if not any([request.title, request.xaxis_title, request.yaxis_title, request.extra_layout]):
        raise HTTPException(
            status_code=422,
            detail="Debe proporcionar al menos un campo para actualizar (title, xaxis_title, yaxis_title, extra_layout).",
        )

    try:
        chart, updated_fields = await chart_service.update_metadata(
            chart_id=chart_id,
            title=request.title,
            xaxis_title=request.xaxis_title,
            yaxis_title=request.yaxis_title,
            extra_layout=request.extra_layout,
        )
    except ValueError:
        log.warning("chart_not_found", chart_id=str(chart_id))
        raise HTTPException(status_code=404, detail="Chart not found")

    return UpdateMetadataResponse(
        chart_id=chart.id,
        updated_fields=updated_fields,
        plotly_json=chart.viz_json,
    )


@router.post(
    "/charts/{chart_id}/regenerate", 
    response_model=RegenerateChartResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Gráfico no encontrado"},
        422: {"description": "Este gráfico no tiene código Python o entrada inválida"},
        500: {"model": ErrorResponse, "description": "Error al re-ejecutar SQL o en VizAgent"},
    }
)
@traceable(name="API.regenerate_chart", run_type="chain")
async def regenerate_chart(
    chart_id: uuid.UUID,
    request: RegenerateChartRequest,
    chart_service: Any = Depends(get_chart_service),
    pipeline_service: Any = Depends(get_pipeline_service),
    session_service: Any = Depends(get_session_service),
):
    """
    Regenerar gráfico con un prompt del usuario.

    Toma el viz_json actual del gráfico, lo envía a Gemini junto con el prompt
    del usuario, y actualiza el resultado con el JSON modificado.
    """
    session_id = request.session_id
    log.info(
        "chart_regeneration_started",
        chart_id=str(chart_id),
        session_id=str(session_id) if session_id else None,
        prompt_len=len(request.prompt),
    )
    # 1. Obtener el gráfico existente
    chart = await chart_service.get_chart_by_id(chart_id)
    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")

    # 2. Verificar que el gráfico tiene plotly_code
    if not chart.plotly_code:
        raise HTTPException(
            status_code=422,
            detail="Este gráfico no tiene código Python asociado y no puede ser regenerado.",
        )

    # 3. Recuperar historial de conversación (context window) si hay sesión
    conversation_history = []
    settings = get_settings()
    if session_id:
        try:
            conversation_history = await session_service.get_context_window(session_id, limit=settings.CONTEXT_WINDOW_SIZE)
        except Exception as exc:
            log.warning("failed_to_fetch_conversation_history", error=str(exc), session_id=str(session_id))

    # 4. Re-ejecutar el SQL guardado para obtener el DataFrame real
    #    execute_sql es síncrona/bloqueante — se corre en thread pool para no
    #    bloquear el event loop de uvloop.
    vanna_agent = pipeline_service.decision_agent.text2sql_agent
    try:
        dataframe = await asyncio.to_thread(vanna_agent.execute_sql, chart.sql)
    except Exception as exc:
        log.error(
            "chart_regeneration_sql_failed",
            chart_id=str(chart_id),
            sql=chart.sql,
            error=str(exc),
        )
        raise HTTPException(
            status_code=500,
            detail="Error al re-ejecutar la consulta SQL del gráfico.",
        )

    # 5. Guardar el mensaje del USUARIO antes de invocar la IA
    if session_id:
        try:
            await session_service.save_message(
                session_id=session_id,
                role=MessageRole.USER,
                content=request.prompt,
                chart_id=chart_id  # Guardar la referencia al gráfico citado
            )
        except Exception as exc:
            log.error("failed_to_save_user_message_regenerate", error=str(exc), session_id=str(session_id))

    # 6. Invocar VizAgent.modify_chart (también síncrono/bloqueante)
    log.info("viz_agent_modify_started", chart_id=str(chart_id))
    viz_agent = pipeline_service.decision_agent.viz_agent
    modification_output = await asyncio.to_thread(
        viz_agent.modify_chart,
        chart.plotly_code,
        dataframe,
        request.prompt,
        conversation_history,
    )

    if not modification_output.success:
        error_msg = modification_output.error_message
        is_503 = "503 unavailable" in error_msg.lower()
        status_code = 503 if is_503 else 500

        log.error(
            "chart_regeneration_failed",
            chart_id=str(chart_id),
            error=error_msg,
        )
        raise HTTPException(
            status_code=status_code,
            detail=error_msg if is_503 else f"Error al regenerar gráfico: {error_msg}",
        )

    # 7. Actualizar el gráfico en la BD (plotly_json y plotly_code sincronizados)
    try:
        updated_chart = await chart_service.update_viz_json(
            chart_id=chart_id,
            viz_json=modification_output.plotly_json,
            plotly_code=modification_output.plotly_code,
            chart_type=modification_output.chart_type,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Chart not found")

    # 8. Guardar el mensaje del SISTEMA con la descripción generada por Gemini
    if session_id:
        try:
            changes_description = (
                modification_output.metadata.get("changes_description")
                if modification_output.metadata
                else None
            )
            await session_service.save_message(
                session_id=session_id,
                role=MessageRole.SYSTEM,
                content=changes_description or "(Gráfico modificado sin descripción)",
                response_type=ResponseType.MESSAGE,
                # No se pasa chart_id: el chart se actualiza in-place en el frontend
                # vía directUpdate. Este mensaje es solo la descripción textual del cambio.
            )
        except Exception as exc:
            log.error("failed_to_save_system_message_regenerate", error=str(exc), session_id=str(session_id))

    log.info(
        "chart_regeneration_completed",
        chart_id=str(updated_chart.id),
        session_id=str(session_id) if session_id else None,
    )
    return RegenerateChartResponse(
        chart_id=updated_chart.id,
        plotly_json=updated_chart.viz_json,
        plotly_code=updated_chart.plotly_code,
        chart_type=updated_chart.chart_type,
    )

