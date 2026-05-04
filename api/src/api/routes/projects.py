import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status

from api.models.schemas import (
    ProjectCreate,
    ProjectResponse,
    ProjectListResponse,
    ResultResponse,
)
from api.models.error_schemas import ErrorResponse
from api.dependencies import get_project_service

log = structlog.get_logger("api.routes.projects")

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse, "description": "Ya existe un proyecto con ese nombre"}},
)
async def create_project(
    data: ProjectCreate,
    project_service: Any = Depends(get_project_service),
):
    """Crea un nuevo proyecto (carpeta)."""
    return await project_service.create_project(data)


@router.get(
    "",
    response_model=ProjectListResponse,
)
async def get_projects(
    project_service: Any = Depends(get_project_service),
):
    """Lista todos los proyectos."""
    projects = await project_service.get_all_projects()
    return ProjectListResponse(projects=projects)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorResponse, "description": "Proyecto no encontrado"}},
)
async def delete_project(
    project_id: uuid.UUID,
    project_service: Any = Depends(get_project_service),
):
    """Elimina un proyecto."""
    success = await project_service.delete_project(project_id)
    if not success:
        log.warning("project_not_found", project_id=str(project_id))
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")


@router.get(
    "/{project_id}/charts",
    response_model=list[ResultResponse],
    responses={404: {"model": ErrorResponse, "description": "Proyecto no encontrado"}},
)
async def get_project_charts(
    project_id: uuid.UUID,
    project_service: Any = Depends(get_project_service),
):
    """Obtiene todos los gráficos asociados a un proyecto."""
    # Verificamos si existe
    project = await project_service.get_project(project_id)
    if not project:
        log.warning("project_not_found", project_id=str(project_id))
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
        
    return await project_service.get_project_results(project_id)


@router.post(
    "/{project_id}/charts/{result_id}",
    status_code=status.HTTP_200_OK,
    responses={404: {"model": ErrorResponse, "description": "Proyecto o resultado no encontrado"}},
)
async def add_chart_to_project(
    project_id: uuid.UUID,
    result_id: uuid.UUID,
    project_service: Any = Depends(get_project_service),
):
    """Asocia un gráfico a un proyecto."""
    success = await project_service.add_result_to_project(project_id, result_id)
    if not success:
        log.warning("add_chart_to_project_failed", project_id=str(project_id), result_id=str(result_id))
        raise HTTPException(status_code=404, detail="Proyecto o resultado no encontrado")
    return {"status": "success"}


@router.delete(
    "/{project_id}/charts/{result_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorResponse, "description": "Gráfico no encontrado en el proyecto"}},
)
async def remove_chart_from_project(
    project_id: uuid.UUID,
    result_id: uuid.UUID,
    project_service: Any = Depends(get_project_service),
):
    """Desasocia un gráfico de un proyecto."""
    success = await project_service.remove_result_from_project(project_id, result_id)
    if not success:
        log.warning("remove_chart_from_project_failed", project_id=str(project_id), result_id=str(result_id))
        raise HTTPException(status_code=404, detail="Gráfico no encontrado en el proyecto")
