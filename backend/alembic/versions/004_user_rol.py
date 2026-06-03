"""004 — Create user_rol table (user ↔ role association)

Revision ID: 004
Revises: 003
Create Date: 2026-06-03

C-04 rbac-permisos-finos: tabla de asignacion usuario → rol.
Cada fila asigna un usuario a un rol dentro de un tenant.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create user_rol table."""
    op.create_table(
        "user_rol",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("rol_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Foreign keys
    op.create_foreign_key(
        "fk_user_rol_user_id",
        "user_rol", "users",
        ["user_id"], ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_user_rol_rol_id",
        "user_rol", "rol",
        ["rol_id"], ["id"],
        ondelete="CASCADE",
    )

    # Indices
    op.create_index("ix_user_rol_tenant_id", "user_rol", ["tenant_id"])
    op.create_index("ix_user_rol_user_id", "user_rol", ["user_id"])
    op.create_index("ix_user_rol_rol_id", "user_rol", ["rol_id"])

    # Unique constraint
    op.create_unique_constraint(
        "uq_user_rol_user_rol",
        "user_rol",
        ["user_id", "rol_id"],
    )


def downgrade() -> None:
    """Drop user_rol table."""
    op.drop_constraint("uq_user_rol_user_rol", "user_rol")
    op.drop_index("ix_user_rol_rol_id")
    op.drop_index("ix_user_rol_user_id")
    op.drop_index("ix_user_rol_tenant_id")
    op.drop_constraint("fk_user_rol_rol_id", "user_rol", type_="foreignkey")
    op.drop_constraint("fk_user_rol_user_id", "user_rol", type_="foreignkey")
    op.drop_table("user_rol")
