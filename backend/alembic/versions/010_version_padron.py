"""010 — Create version_padron, entrada_padron tables

Revision ID: 010
Revises: 009
Create Date: 2026-06-04

C-09 padron-ingesta-moodle: modelo versionado de padron de alumnos por materia x
cohorte con soporte de importacion manual (xlsx/csv) e integracion Moodle WS.

EntradaPadron.email se almacena cifrado (AES-256 en reposo via EncryptedColumn).
usuario_id es nullable porque el alumno puede no tener cuenta aun en el sistema.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create version_padron and entrada_padron tables."""

    # ── version_padron (tenant-scoped, versionado) ──────────────────────
    op.create_table(
        "version_padron",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "materia_id",
            UUID(as_uuid=True),
            sa.ForeignKey("materia.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "cohorte_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cohorte.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "cargado_por",
            UUID(as_uuid=True),
            sa.ForeignKey("usuario.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "cargado_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("activa", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
        "ix_version_padron_tenant_id", "version_padron", ["tenant_id"]
    )
    op.create_index(
        "ix_version_padron_materia_cohorte",
        "version_padron",
        ["materia_id", "cohorte_id"],
    )

    # ── entrada_padron (tenant-scoped, entries per version) ─────────────
    op.create_table(
        "entrada_padron",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "version_id",
            UUID(as_uuid=True),
            sa.ForeignKey("version_padron.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "usuario_id",
            UUID(as_uuid=True),
            sa.ForeignKey("usuario.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Datos desnormalizados (para historico)
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("apellidos", sa.String(200), nullable=False),
        sa.Column(
            "email", sa.Text(), nullable=False
        ),  # EncryptedColumn → Text at DB level
        sa.Column("comision", sa.String(50), nullable=True),
        sa.Column("regional", sa.String(100), nullable=True),
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
        "ix_entrada_padron_tenant_id", "entrada_padron", ["tenant_id"]
    )
    op.create_index(
        "ix_entrada_padron_version_id", "entrada_padron", ["version_id"]
    )

    # ── Seed: permiso padron:importar + asignacion a roles ──────────────
    _seed_padron_permissions()


def _seed_padron_permissions() -> None:
    """Inserta el permiso padron:importar y lo asigna a PROFESOR, COORDINADOR, NEXO y ADMIN."""
    conn = op.get_bind()

    # Insertar permiso (catalogo global, sin tenant_id)
    result = conn.execute(
        sa.text(
            "INSERT INTO permiso (id, codigo, descripcion, created_at) "
            "VALUES (gen_random_uuid(), :codigo, :descripcion, now()) "
            "RETURNING id"
        ),
        {"codigo": "padron:importar", "descripcion": "Importar padron de alumnos"},
    )
    permiso_id = result.scalar_one()

    # Asignar a roles existentes en cada tenant
    # PROFESOR, COORDINADOR, NEXO, ADMIN tienen permiso padron:importar
    roles_con_permiso = ["PROFESOR", "COORDINADOR", "NEXO", "ADMIN"]

    # Obtener todos los tenants y sus roles
    tenants = conn.execute(sa.text("SELECT id FROM tenant")).fetchall()
    for (tenant_id,) in tenants:
        roles = conn.execute(
            sa.text("SELECT id, codigo FROM rol WHERE tenant_id = :t AND codigo = ANY(:roles)"),
            {"t": tenant_id, "roles": roles_con_permiso},
        ).fetchall()
        for rol_id, _ in roles:
            # Verificar si ya existe la relacion (idempotencia)
            existing = conn.execute(
                sa.text(
                    "SELECT 1 FROM rol_permiso WHERE tenant_id = :t AND rol_id = :r AND permiso_id = :p"
                ),
                {"t": tenant_id, "r": rol_id, "p": permiso_id},
            ).fetchone()
            if not existing:
                conn.execute(
                    sa.text(
                        "INSERT INTO rol_permiso (id, tenant_id, rol_id, permiso_id, created_at) "
                        "VALUES (gen_random_uuid(), :t, :r, :p, now())"
                    ),
                    {"t": tenant_id, "r": rol_id, "p": permiso_id},
                )


def downgrade() -> None:
    """Drop tables in reverse order."""
    op.drop_index("ix_entrada_padron_version_id", table_name="entrada_padron")
    op.drop_index("ix_entrada_padron_tenant_id", table_name="entrada_padron")
    op.drop_table("entrada_padron")
    op.drop_index(
        "ix_version_padron_materia_cohorte", table_name="version_padron"
    )
    op.drop_index("ix_version_padron_tenant_id", table_name="version_padron")
    op.drop_table("version_padron")
