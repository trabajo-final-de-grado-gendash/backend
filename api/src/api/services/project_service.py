import uuid
import structlog
from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.models.database import Project, GenerationResult
from api.models.schemas import ProjectCreate, ProjectResponse, ResultResponse

log = structlog.get_logger("api.project_service")


class ProjectService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_project(self, data: ProjectCreate) -> ProjectResponse:
        # Validate that a project with the same name doesn't exist
        stmt = select(Project).where(Project.name == data.name)
        existing = await self.db.execute(stmt)
        if existing.scalars().first():
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="A project with this name already exists")
            
        project = Project(name=data.name)
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        
        return ProjectResponse(
            id=project.id,
            name=project.name,
            created_at=project.created_at,
            updated_at=project.updated_at
        )

    async def get_all_projects(self) -> list[ProjectResponse]:
        stmt = select(Project).order_by(Project.created_at.desc())
        result = await self.db.execute(stmt)
        projects = result.scalars().all()
        
        return [
            ProjectResponse(
                id=p.id,
                name=p.name,
                created_at=p.created_at,
                updated_at=p.updated_at
            ) for p in projects
        ]

    async def get_project(self, project_id: uuid.UUID) -> Project | None:
        stmt = select(Project).where(Project.id == project_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def delete_project(self, project_id: uuid.UUID) -> bool:
        project = await self.get_project(project_id)
        if not project:
            return False
            
        await self.db.delete(project)
        await self.db.commit()
        return True

    async def add_result_to_project(self, project_id: uuid.UUID, result_id: uuid.UUID) -> bool:
        # Check if project exists
        project = await self.get_project(project_id)
        if not project:
            return False
            
        # Get result
        stmt = select(GenerationResult).where(GenerationResult.id == result_id)
        res = await self.db.execute(stmt)
        generation_result = res.scalars().first()
        
        if not generation_result:
            return False
            
        generation_result.project_id = project_id
        await self.db.commit()
        return True

    async def remove_result_from_project(self, project_id: uuid.UUID, result_id: uuid.UUID) -> bool:
        stmt = select(GenerationResult).where(
            GenerationResult.id == result_id,
            GenerationResult.project_id == project_id
        )
        res = await self.db.execute(stmt)
        generation_result = res.scalars().first()
        
        if not generation_result:
            return False
            
        generation_result.project_id = None
        await self.db.commit()
        return True

    async def get_project_results(self, project_id: uuid.UUID) -> list[ResultResponse]:
        project = await self.get_project(project_id)
        if not project:
            return []
            
        stmt = select(GenerationResult).where(GenerationResult.project_id == project_id).order_by(GenerationResult.created_at.desc())
        res = await self.db.execute(stmt)
        results = res.scalars().all()
        
        return [
            ResultResponse(
                result_id=r.id,
                query=r.query,
                sql=r.sql,
                plotly_json=r.viz_json,
                plotly_code=r.plotly_code,
                chart_type=r.chart_type,
                project_id=r.project_id,
                created_at=r.created_at
            ) for r in results
        ]
