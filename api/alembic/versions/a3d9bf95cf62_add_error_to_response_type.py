"""add error to response type

Revision ID: a3d9bf95cf62
Revises: a3d9bf95cf61
Create Date: 2026-05-10 00:20:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a3d9bf95cf62'
down_revision: Union[str, None] = 'a3d9bf95cf61'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Commit the current transaction because ALTER TYPE ADD VALUE cannot run inside a transaction block
    op.execute("COMMIT")
    # Intentamos ejecutarlo directamente dentro de la transacción de Alembic
    op.execute("ALTER TYPE bigenia.response_type_enum ADD VALUE IF NOT EXISTS 'error'")


def downgrade() -> None:
    # Postgres doesn't easily support dropping an enum value.
    pass
