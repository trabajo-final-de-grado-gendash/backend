import uuid
import structlog
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified
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

    async def get_all_results(self) -> list[GenerationResult]:
        stmt = select(GenerationResult).order_by(GenerationResult.created_at.desc())
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def update_metadata(
        self,
        result_id: uuid.UUID,
        title: str | None = None,
        xaxis_title: str | None = None,
        yaxis_title: str | None = None,
        extra_layout: dict[str, Any] | None = None,
    ) -> tuple[GenerationResult, list[str]]:
        """Merge parcial de layout (título, ejes) sobre viz_json.

        Retorna el result actualizado y la lista de campos modificados.
        """
        result = await self.get_result_by_id(result_id)
        if not result:
            raise ValueError(f"Result {result_id} not found")

        viz_json = dict(result.viz_json)
        layout = viz_json.setdefault("layout", {})
        updated_fields: list[str] = []

        if title is not None:
            layout["title"] = {"text": title}
            updated_fields.append("title")

        if xaxis_title is not None:
            layout.setdefault("xaxis", {})["title"] = {"text": xaxis_title}
            updated_fields.append("xaxis_title")

        if yaxis_title is not None:
            layout.setdefault("yaxis", {})["title"] = {"text": yaxis_title}
            updated_fields.append("yaxis_title")

        if extra_layout is not None:
            layout.update(extra_layout)
            updated_fields.extend(extra_layout.keys())

        result.viz_json = viz_json
        flag_modified(result, "viz_json")

        await self.db.commit()
        await self.db.refresh(result)

        log.info(
            "metadata_updated",
            result_id=str(result_id),
            updated_fields=updated_fields,
        )
        return result, updated_fields

    async def update_viz_json(
        self,
        result_id: uuid.UUID,
        viz_json: dict[str, Any],
        plotly_code: str | None = None,
        chart_type: str | None = None,
    ) -> GenerationResult:
        """Reemplaza completamente el viz_json tras regeneración."""
        result = await self.get_result_by_id(result_id)
        if not result:
            raise ValueError(f"Result {result_id} not found")

        result.viz_json = viz_json
        if plotly_code is not None:
            result.plotly_code = plotly_code
        if chart_type is not None:
            result.chart_type = chart_type

        flag_modified(result, "viz_json")

        await self.db.commit()
        await self.db.refresh(result)

        log.info("viz_json_updated", result_id=str(result_id))
        return result
