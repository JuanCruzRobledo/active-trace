"""007 — Create carrera, materia, cohorte tables

Revision ID: 007
Revises: 006
Create Date: 2026-06-03

C-06 estructura-academica: catalogo academico del tenant (Carrera, Materia,
Cohorte) con constraints de unicidad compuesta y aislamiento multi-tenant.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create carrera, materia, cohorte tables."""

    # ── carrera (tenant-scoped catalog) ─────────────────────────────────
    op.create_table(
        "carrera",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("codigo", sa.String(50), nullable=False),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column(
            "estado",
            sa.String(20),
            nullable=False,
            server_default="Activa",
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
        sa.UniqueConstraint(
            "tenant_id", "codigo", name="uq_carrera_tenant_codigo"
        ),
    )
    op.create_index("ix_carrera_tenant_id", "carrera", ["tenant_id"])

    # ── materia (tenant-scoped catalog) ─────────────────────────────────
    op.create_table(
        "materia",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("codigo", sa.String(50), nullable=False),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column(
            "estado",
            sa.String(20),
            nullable=False,
            server_default="Activa",
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
        sa.UniqueConstraint(
            "tenant_id", "codigo", name="uq_materia_tenant_codigo"
        ),
    )
    op.create_index("ix_materia_tenant_id", "materia", ["tenant_id"])

    # ── cohorte (tenant-scoped, linked to carrera) ──────────────────────
    op.create_table(
        "cohorte",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "carrera_id",
            UUID(as_uuid=True),
            sa.ForeignKey("carrera.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("anio", sa.Integer(), nullable=False),
        sa.Column("vig_desde", sa.Date(), nullable=False),
        sa.Column("vig_hasta", sa.Date(), nullable=True),
        sa.Column(
            "estado",
            sa.String(20),
            nullable=False,
            server_default="Activa",
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
        sa.UniqueConstraint(
            "tenant_id", "carrera_id", "nombre",
            name="uq_cohorte_tenant_carrera_nombre",
        ),
    )
    op.create_index("ix_cohorte_tenant_id", "cohorte", ["tenant_id"])
    op.create_index("ix_cohorte_carrera_id", "cohorte", ["carrera_id"])


def downgrade() -> None:
    """Drop tables in reverse order."""
    op.drop_index("ix_cohorte_carrera_id", table_name="cohorte")
    op.drop_index("ix_cohorte_tenant_id", table_name="cohorte")
    op.drop_table("cohorte")
    op.drop_index("ix_materia_tenant_id", table_name="materia")
    op.drop_table("materia")
    op.drop_index("ix_carrera_tenant_id", table_name="carrera")
    op.drop_table("carrera")
