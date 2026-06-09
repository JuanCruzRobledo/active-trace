"""011 — Create calificacion, umbral_materia tables

Revision ID: 011
Revises: 010
Create Date: 2026-06-04

C-10 calificaciones-y-umbral: modelo de calificaciones por alumno/materia/actividad
y umbral de aprobacion configurable por asignacion y materia.

Calificacion almacena nota numerica y/o textual con FK a entrada_padron y materia.
UmbralMateria define el porcentaje de aprobacion y valores textuales aprobatorios
para una combinacion (asignacion_id, materia_id) activa.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create calificacion and umbral_materia tables."""

    # ── calificacion (tenant-scoped, per student/activity) ───────────────
    op.create_table(
        "calificacion",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "entrada_padron_id",
            UUID(as_uuid=True),
            sa.ForeignKey("entrada_padron.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "materia_id",
            UUID(as_uuid=True),
            sa.ForeignKey("materia.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("actividad", sa.String(200), nullable=False),
        sa.Column("nota_numerica", sa.Numeric(5, 2), nullable=True),
        sa.Column("nota_textual", sa.String(100), nullable=True),
        sa.Column("aprobado", sa.Boolean(), nullable=True),
        sa.Column(
            "origen",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'Importado'"),
        ),
        sa.Column(
            "importado_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
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
        "ix_calificacion_tenant_id", "calificacion", ["tenant_id"]
    )
    op.create_index(
        "ix_calificacion_entrada_materia_actividad",
        "calificacion",
        ["entrada_padron_id", "materia_id", "actividad"],
    )
    op.create_index(
        "ix_calificacion_materia_id",
        "calificacion",
        ["materia_id"],
    )

    # ── umbral_materia (tenant-scoped, threshold config per assignment) ──
    op.create_table(
        "umbral_materia",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "asignacion_id",
            UUID(as_uuid=True),
            sa.ForeignKey("asignacion.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "materia_id",
            UUID(as_uuid=True),
            sa.ForeignKey("materia.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "umbral_pct",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("60"),
        ),
        sa.Column(
            "valores_aprobatorios",
            sa.dialects.postgresql.JSONB(),
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
        "ix_umbral_materia_tenant_id", "umbral_materia", ["tenant_id"]
    )
    op.create_index(
        "ix_umbral_materia_asignacion_materia",
        "umbral_materia",
        ["asignacion_id", "materia_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    """Drop tables in reverse order."""
    op.drop_index(
        "ix_umbral_materia_asignacion_materia",
        table_name="umbral_materia",
    )
    op.drop_index(
        "ix_umbral_materia_tenant_id",
        table_name="umbral_materia",
    )
    op.drop_table("umbral_materia")
    op.drop_index(
        "ix_calificacion_materia_id",
        table_name="calificacion",
    )
    op.drop_index(
        "ix_calificacion_entrada_materia_actividad",
        table_name="calificacion",
    )
    op.drop_index(
        "ix_calificacion_tenant_id",
        table_name="calificacion",
    )
    op.drop_table("calificacion")
