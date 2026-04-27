"""002_add_updated_at_to_generation_results

Agrega columna updated_at a generation_results para trackear
cuándo fue modificado un gráfico

Revision ID: 002
Revises: 001
Create Date: 2026-04-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: str = "001"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    op.add_column(
        "generation_results",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="bigenia",
    )


def downgrade() -> None:
    op.drop_column("generation_results", "updated_at", schema="bigenia")
