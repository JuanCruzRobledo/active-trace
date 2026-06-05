"""013 — Add config JSONB column to tenant

Revision ID: 013
Revises: 012
Create Date: 2026-06-04

C-12 comunicaciones-cola-worker: agrega columna ``config`` al modelo Tenant
para almacenar flags configurables por institución (aprobacion de
comunicaciones, roles aprobadores, etc.).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add config JSONB column to tenant table."""
    op.add_column(
        "tenant",
        sa.Column(
            "config",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    """Drop config column from tenant table."""
    op.drop_column("tenant", "config")
