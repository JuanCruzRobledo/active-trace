"""009 — Create usuario, asignacion tables

Revision ID: 009
Revises: 008
Create Date: 2026-06-03

C-07 usuarios-y-asignaciones: modelo Usuario con PII cifrada (AES-256 en reposo)
y modelo Asignacion (Usuario ↔ Rol ↔ contexto académico) con vigencia temporal.

Partial unique indexes para soft-delete: ``(tenant_id, email)`` en usuario permite
re-uso del email tras baja lógica.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create usuario and asignacion tables."""

    # ── usuario (tenant-scoped, PII cifrada con AES-256) ─────────────────
    op.create_table(
        "usuario",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "auth_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("apellidos", sa.String(200), nullable=False),
        # PII fields — stored encrypted via EncryptedColumn (Text at DB level)
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("dni", sa.Text(), nullable=True),
        sa.Column("cuil", sa.Text(), nullable=True),
        sa.Column("cbu", sa.Text(), nullable=True),
        sa.Column("alias_cbu", sa.Text(), nullable=True),
        # Business fields
        sa.Column("banco", sa.String(100), nullable=True),
        sa.Column("regional", sa.String(100), nullable=True),
        sa.Column("legajo", sa.String(50), nullable=True),
        sa.Column("legajo_profesional", sa.String(50), nullable=True),
        sa.Column("facturador", sa.String(200), nullable=True),
        sa.Column(
            "estado",
            sa.String(20),
            nullable=False,
            server_default="Activo",
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
    op.create_index("ix_usuario_tenant_id", "usuario", ["tenant_id"])
    # Partial unique index for soft-delete: only active records enforce uniqueness
    op.create_index(
        "uq_usuario_tenant_email_active",
        "usuario",
        ["tenant_id", "email"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # ── asignacion (tenant-scoped, Usuario ↔ Rol ↔ contexto) ────────────
    op.create_table(
        "asignacion",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "usuario_id",
            UUID(as_uuid=True),
            sa.ForeignKey("usuario.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rol", sa.String(50), nullable=False),
        sa.Column(
            "materia_id",
            UUID(as_uuid=True),
            sa.ForeignKey("materia.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "carrera_id",
            UUID(as_uuid=True),
            sa.ForeignKey("carrera.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "cohorte_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cohorte.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("comisiones", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column(
            "responsable_id",
            UUID(as_uuid=True),
            sa.ForeignKey("usuario.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("desde", sa.DateTime(timezone=True), nullable=False),
        sa.Column("hasta", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index("ix_asignacion_tenant_id", "asignacion", ["tenant_id"])
    op.create_index("ix_asignacion_usuario_id", "asignacion", ["usuario_id"])
    op.create_index("ix_asignacion_materia_id", "asignacion", ["materia_id"])
    op.create_index("ix_asignacion_carrera_id", "asignacion", ["carrera_id"])
    op.create_index("ix_asignacion_cohorte_id", "asignacion", ["cohorte_id"])


def downgrade() -> None:
    """Drop tables in reverse order."""
    op.drop_index("ix_asignacion_cohorte_id", table_name="asignacion")
    op.drop_index("ix_asignacion_carrera_id", table_name="asignacion")
    op.drop_index("ix_asignacion_materia_id", table_name="asignacion")
    op.drop_index("ix_asignacion_usuario_id", table_name="asignacion")
    op.drop_index("ix_asignacion_tenant_id", table_name="asignacion")
    op.drop_table("asignacion")
    op.drop_index("uq_usuario_tenant_email_active", table_name="usuario")
    op.drop_index("ix_usuario_tenant_id", table_name="usuario")
    op.drop_table("usuario")
