"""
routes/results.py — Endpoints para consulta y edición de resultados de visualización.

Endpoints:
- GET  /api/v1/results/{result_id}            — Obtener un resultado existente
- PATCH /api/v1/results/{result_id}/metadata   — TFG-56: Actualizar metadata del gráfico
- POST  /api/v1/results/{result_id}/regenerate — TFG-57: Regenerar gráfico con prompt
"""

import asyncio
import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException
from api.models.schemas import (
    RegenerateChartRequest,
    RegenerateChartResponse,
    ResultResponse,
    UpdateMetadataRequest,
    UpdateMetadataResponse,
)
from api.models.error_schemas import ErrorResponse
from api.dependencies import get_pipeline_service, get_result_service

log = structlog.get_logger("api.routes.results")

router = APIRouter(prefix="/api/v1", tags=["results"])

@router.get(
    "/results/{result_id}", 
    response_model=ResultResponse,
    responses={404: {"model": ErrorResponse, "description": "Resultado no encontrado"}}
)
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


@router.patch("/results/{result_id}/metadata", response_model=UpdateMetadataResponse)
async def update_chart_metadata(
    result_id: uuid.UUID,
    request: UpdateMetadataRequest,
    result_service: Any = Depends(get_result_service),
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
        result, updated_fields = await result_service.update_metadata(
            result_id=result_id,
            title=request.title,
            xaxis_title=request.xaxis_title,
            yaxis_title=request.yaxis_title,
            extra_layout=request.extra_layout,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Result not found")

    return UpdateMetadataResponse(
        result_id=result.id,
        updated_fields=updated_fields,
        plotly_json=result.viz_json,
    )


@router.post("/results/{result_id}/regenerate", response_model=RegenerateChartResponse)
async def regenerate_chart(
    result_id: uuid.UUID,
    request: RegenerateChartRequest,
    result_service: Any = Depends(get_result_service),
    pipeline_service: Any = Depends(get_pipeline_service),
):
    """
    Regenerar gráfico con un prompt del usuario.

    Toma el viz_json actual del gráfico, lo envía a Gemini junto con el prompt
    del usuario, y actualiza el resultado con el JSON modificado.
    """
    # 1. Obtener el resultado existente
    result = await result_service.get_result_by_id(result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")

    # 2. Verificar que el resultado tiene plotly_code
    if not result.plotly_code:
        raise HTTPException(
            status_code=422,
            detail="Este resultado no tiene código Python asociado y no puede ser regenerado.",
        )

    # 3. Re-ejecutar el SQL guardado para obtener el DataFrame real
    #    execute_sql es síncrona/bloqueante — se corre en thread pool para no
    #    bloquear el event loop de uvloop.
    vanna_agent = pipeline_service.decision_agent.text2sql_agent
    try:
        dataframe = await asyncio.to_thread(vanna_agent.execute_sql, result.sql)
    except Exception as exc:
        log.error(
            "chart_regeneration_sql_failed",
            result_id=str(result_id),
            sql=result.sql,
            error=str(exc),
        )
        raise HTTPException(
            status_code=500,
            detail="Error al re-ejecutar la consulta SQL del resultado.",
        )

    # 4. Invocar VizAgent.modify_chart (también síncrono/bloqueante)
    viz_agent = pipeline_service.decision_agent.viz_agent
    modification_output = await asyncio.to_thread(
        viz_agent.modify_chart,
        result.plotly_code,
        dataframe,
        request.prompt,
    )

    if not modification_output.success:
        log.error(
            "chart_regeneration_failed",
            result_id=str(result_id),
            error=modification_output.error_message,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Error al regenerar gráfico: {modification_output.error_message}",
        )

    # 5. Actualizar el resultado en la BD (plotly_json y plotly_code sincronizados)
    try:
        updated_result = await result_service.update_viz_json(
            result_id=result_id,
            viz_json=modification_output.plotly_json,
            plotly_code=modification_output.plotly_code,
            chart_type=modification_output.chart_type,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Result not found")

    return RegenerateChartResponse(
        result_id=updated_result.id,
        plotly_json=updated_result.viz_json,
        plotly_code=updated_result.plotly_code,
        chart_type=updated_result.chart_type,
    )

