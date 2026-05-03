"""
models/database.py — Modelos ORM de SQLAlchemy para persistencia.

Entidades: Session, ConversationMessage, GenerationResult.
Referencia: data-model.md §Entities
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Session(Base):
    """
    Agrupador de interacciones dentro de un hilo conversacional.

    data-model.md §Entity: Session
    """

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
        server_default=func.now(),
    )

    # Relationships
    messages: Mapped[list[ConversationMessage]] = relationship(
        "ConversationMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ConversationMessage.created_at",
    )
    results: Mapped[list[GenerationResult]] = relationship(
        "GenerationResult",
        back_populates="session",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Session id={self.id} created_at={self.created_at}>"


class Project(Base):
    """
    Agrupador de gráficos generados.
    """

    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
        server_default=func.now(),
    )

    # Relationships
    results: Mapped[list[GenerationResult]] = relationship(
        "GenerationResult",
        back_populates="project",
    )

    def __repr__(self) -> str:
        return f"<Project id={self.id} name={self.name}>"


class ConversationMessage(Base):
    """
    Unidad atómica del historial de sesión.

    data-model.md §Entity: ConversationMessage
    """

    __tablename__ = "conversation_messages"

    __table_args__ = (
        Index("ix_conversation_messages_session_id", "session_id"),
        Index("ix_conversation_messages_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        Enum("user", "system", name="message_role_enum", schema="bigenia"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    response_type: Mapped[Optional[str]] = mapped_column(
        Enum("visualization", "clarification", "message", name="response_type_enum", schema="bigenia"),
        nullable=True,
    )
    result_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("generation_results.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        server_default=func.now(),
    )

    # Relationships
    session: Mapped[Session] = relationship("Session", back_populates="messages")

    def __repr__(self) -> str:
        return (
            f"<ConversationMessage id={self.id} role={self.role} "
            f"session_id={self.session_id}>"
        )


class GenerationResult(Base):
    """
    Registro persistido de un pipeline exitoso completo.

    data-model.md §Entity: GenerationResult
    """

    __tablename__ = "generation_results"

    __table_args__ = (
        Index("ix_generation_results_session_id", "session_id"),
        Index("ix_generation_results_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    sql: Mapped[str] = mapped_column(Text, nullable=False)
    viz_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    plotly_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    chart_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
        server_default=func.now(),
    )

    # Relationships
    session: Mapped[Session] = relationship("Session", back_populates="results")
    project: Mapped[Optional[Project]] = relationship("Project", back_populates="results")

    def __repr__(self) -> str:
        return (
            f"<GenerationResult id={self.id} session_id={self.session_id} "
            f"chart_type={self.chart_type}>"
        )
