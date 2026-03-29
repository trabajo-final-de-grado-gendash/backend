import uuid
import structlog
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from api.models.database import GenerationResult
from api.services.session_service import SessionService

log = structlog.get_logger("api.result_service")

class ResultService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.session_service = SessionService(db)

    async def save_result(
        self,
        session_id: uuid.UUID,
        query: str,
        sql: str,
        viz_json: dict[str, Any],
        plotly_code: str | None = None,
        chart_type: str | None = None,
    ) -> GenerationResult:
        # Aseguramos que la sesión existe para la foreign key
        await self.session_service.get_or_create_session(session_id)
        
        result = GenerationResult(
            session_id=session_id,
            query=query,
            sql=sql,
            viz_json=viz_json,
            plotly_code=plotly_code,
            chart_type=chart_type,
        )
        self.db.add(result)
        await self.db.commit()
        await self.db.refresh(result)
        
        log.info("result_saved", result_id=str(result.id), session_id=str(session_id))
        return result

    async def get_result_by_id(self, result_id: uuid.UUID) -> GenerationResult | None:
        stmt = select(GenerationResult).where(GenerationResult.id == result_id)
        res = await self.db.execute(stmt)
        return res.scalars().first()
