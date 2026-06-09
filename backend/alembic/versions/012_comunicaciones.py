"""012 — Create comunicaciones table

Revision ID: 012
Revises: 011
Create Date: 2026-06-04

C-12 comunicaciones-cola-worker: tabla de comunicaciones masivas con
destinatario cifrado, ciclo de estados (Pendiente→Enviando→Enviado/Error/Cancelado),
y soporte para aprobación configurable por tenant.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create comunicaciones table."""

    op.create_table(
        "comunicaciones",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "enviado_por_id",
            UUID(as_uuid=True),
            sa.ForeignKey("usuario.id", ondelete="SET NULL"),
            nullable=False,
        ),
        sa.Column(
            "materia_id",
            UUID(as_uuid=True),
            sa.ForeignKey("materia.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("destinatario", sa.Text(), nullable=False),
        sa.Column("asunto", sa.String(200), nullable=False),
        sa.Column("cuerpo", sa.Text(), nullable=False),
        sa.Column(
            "estado",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'Pendiente'"),
        ),
        sa.Column("lote_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "necesita_aprobacion",
            UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "aprobado_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "aprobado_por_id",
            UUID(as_uuid=True),
            sa.ForeignKey("usuario.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "enviado_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_comunicaciones_tenant_id", "comunicaciones", ["tenant_id"]
    )
    op.create_index(
        "ix_comunicaciones_lote_id", "comunicaciones", ["lote_id"]
    )
    op.create_index(
        "ix_comunicaciones_estado", "comunicaciones", ["estado"]
    )
    op.create_index(
        "ix_comunicaciones_enviado_por_id",
        "comunicaciones",
        ["enviado_por_id"],
    )


def downgrade() -> None:
    """Drop comunicaciones table."""
    op.drop_index(
        "ix_comunicaciones_enviado_por_id",
        table_name="comunicaciones",
    )
    op.drop_index(
        "ix_comunicaciones_estado",
        table_name="comunicaciones",
    )
    op.drop_index(
        "ix_comunicaciones_lote_id",
        table_name="comunicaciones",
    )
    op.drop_index(
        "ix_comunicaciones_tenant_id",
        table_name="comunicaciones",
    )
    op.drop_table("comunicaciones")
