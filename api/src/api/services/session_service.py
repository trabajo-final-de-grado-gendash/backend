import uuid
import structlog
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from api.models.database import Session, ConversationMessage
from decision_agent.models import MessageRole, ResponseType, ConversationContext
from api.models.schemas import MessageItem

log = structlog.get_logger("api.session_service")

class SessionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_session(self, session_id: uuid.UUID) -> Session:
        stmt = select(Session).where(Session.id == session_id)
        result = await self.db.execute(stmt)
        session = result.scalars().first()
        
        if not session:
            session = Session(id=session_id)
            self.db.add(session)
            await self.db.commit()
            await self.db.refresh(session)
            
        return session

    async def save_message(
        self,
        session_id: uuid.UUID,
        role: MessageRole,
        content: str,
        response_type: ResponseType | None = None
    ) -> ConversationMessage:
        await self.get_or_create_session(session_id)
        msg = ConversationMessage(
            session_id=session_id,
            role=role.value,
            content=content,
            response_type=response_type.value if response_type else None
        )
        self.db.add(msg)
        await self.db.commit()
        await self.db.refresh(msg)
        return msg

    async def get_context_window(self, session_id: uuid.UUID, limit: int = 5) -> list[ConversationContext]:
        stmt = (
            select(ConversationMessage)
            .where(ConversationMessage.session_id == session_id)
            .order_by(desc(ConversationMessage.created_at))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        messages = result.scalars().all()
        
        # Devuelve en orden cronológico (los más recientes primero según config context limit, y al reverso)
        context = []
        for msg in reversed(messages):
            context.append(ConversationContext(
                role=MessageRole(msg.role),
                content=msg.content,
                response_type=ResponseType(msg.response_type) if msg.response_type else None
            ))
            
        return context

    async def get_full_history(self, session_id: uuid.UUID) -> list[MessageItem]:
        stmt = (
            select(ConversationMessage)
            .where(ConversationMessage.session_id == session_id)
            .order_by(ConversationMessage.created_at.asc())
        )
        result = await self.db.execute(stmt)
        messages = result.scalars().all()
        
        history = []
        for msg in messages:
            history.append(MessageItem(
                role=MessageRole(msg.role),
                content=msg.content,
                response_type=ResponseType(msg.response_type) if msg.response_type else None,
                timestamp=msg.created_at
            ))
            
        return history

    async def get_session(self, session_id: uuid.UUID) -> Session | None:
        stmt = select(Session).where(Session.id == session_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()
