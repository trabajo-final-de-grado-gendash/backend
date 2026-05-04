import uuid
import structlog
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified
from api.models.database import Chart
from api.services.session_service import SessionService

log = structlog.get_logger("api.chart_service")

class ChartService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.session_service = SessionService(db)

    async def save_chart(
        self,
        session_id: uuid.UUID,
        query: str,
        sql: str,
        viz_json: dict[str, Any],
        plotly_code: str | None = None,
        chart_type: str | None = None,
    ) -> Chart:
        # Aseguramos que la sesión existe para la foreign key
        await self.session_service.get_or_create_session(session_id)
        
        chart = Chart(
            session_id=session_id,
            query=query,
            sql=sql,
            viz_json=viz_json,
            plotly_code=plotly_code,
            chart_type=chart_type,
        )
        self.db.add(chart)
        await self.db.commit()
        await self.db.refresh(chart)
        
        log.info("chart_saved", chart_id=str(chart.id), session_id=str(session_id))
        return chart

    async def get_chart_by_id(self, chart_id: uuid.UUID) -> Chart | None:
        stmt = select(Chart).where(Chart.id == chart_id)
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def get_all_charts(self) -> list[Chart]:
        stmt = select(Chart).order_by(Chart.created_at.desc())
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def update_metadata(
        self,
        chart_id: uuid.UUID,
        title: str | None = None,
        xaxis_title: str | None = None,
        yaxis_title: str | None = None,
        extra_layout: dict[str, Any] | None = None,
    ) -> tuple[Chart, list[str]]:
        """Merge parcial de layout (título, ejes) sobre viz_json.

        Retorna el chart actualizado y la lista de campos modificados.
        """
        chart = await self.get_chart_by_id(chart_id)
        if not chart:
            raise ValueError(f"Chart {chart_id} not found")

        viz_json = dict(chart.viz_json)
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

        chart.viz_json = viz_json
        flag_modified(chart, "viz_json")

        await self.db.commit()
        await self.db.refresh(chart)

        log.info(
            "metadata_updated",
            chart_id=str(chart_id),
            updated_fields=updated_fields,
        )
        return chart, updated_fields

    async def update_viz_json(
        self,
        chart_id: uuid.UUID,
        viz_json: dict[str, Any],
        plotly_code: str | None = None,
        chart_type: str | None = None,
    ) -> Chart:
        """Reemplaza completamente el viz_json tras regeneración."""
        chart = await self.get_chart_by_id(chart_id)
        if not chart:
            raise ValueError(f"Chart {chart_id} not found")

        chart.viz_json = viz_json
        if plotly_code is not None:
            chart.plotly_code = plotly_code
        if chart_type is not None:
            chart.chart_type = chart_type

        flag_modified(chart, "viz_json")

        await self.db.commit()
        await self.db.refresh(chart)

        log.info("viz_json_updated", chart_id=str(chart_id))
        return chart
