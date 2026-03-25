"""001_initial_schema

Migración inicial: crea las tablas sessions, conversation_messages y generation_results
con todos sus índices.

Revision ID: 001
Revises: (none)
Create Date: 2026-03-24
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    # --- Enums ---
    message_role_enum = postgresql.ENUM("user", "system", name="message_role_enum")
    response_type_enum = postgresql.ENUM(
        "visualization", "clarification", "message", name="response_type_enum"
    )
    message_role_enum.create(op.get_bind())
    response_type_enum.create(op.get_bind())

    # --- sessions ---
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # --- conversation_messages ---
    op.create_table(
        "conversation_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "role",
            sa.Enum("user", "system", name="message_role_enum", create_type=False),
            nullable=False,
        ),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column(
            "response_type",
            sa.Enum(
                "visualization",
                "clarification",
                "message",
                name="response_type_enum",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["sessions.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_conversation_messages_session_id",
        "conversation_messages",
        ["session_id"],
    )
    op.create_index(
        "ix_conversation_messages_created_at",
        "conversation_messages",
        ["created_at"],
    )

    # --- generation_results ---
    op.create_table(
        "generation_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("query", sa.Text, nullable=False),
        sa.Column("sql", sa.Text, nullable=False),
        sa.Column("viz_json", postgresql.JSONB, nullable=False),
        sa.Column("plotly_code", sa.Text, nullable=True),
        sa.Column("chart_type", sa.String(50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["sessions.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_generation_results_session_id",
        "generation_results",
        ["session_id"],
    )
    op.create_index(
        "ix_generation_results_created_at",
        "generation_results",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_generation_results_created_at", "generation_results")
    op.drop_index("ix_generation_results_session_id", "generation_results")
    op.drop_table("generation_results")

    op.drop_index("ix_conversation_messages_created_at", "conversation_messages")
    op.drop_index("ix_conversation_messages_session_id", "conversation_messages")
    op.drop_table("conversation_messages")

    op.drop_table("sessions")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS message_role_enum")
    op.execute("DROP TYPE IF EXISTS response_type_enum")
