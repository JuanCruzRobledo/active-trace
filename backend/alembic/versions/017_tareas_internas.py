"""017 — Create tareas internas tables

Revision ID: 017
Revises: 016
Create Date: 2026-06-06

C-16 tareas-internas: tablas para el modulo de tareas internas
(tarea, comentario_tarea) con enum estado_tarea.
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "017"
down_revision: Union[str, None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create tarea and comentario_tarea tables."""

    # ── Enum type ──────────────────────────────────────────────────────
    op.execute("""
        DO $$
        BEGIN
            CREATE TYPE estado_tarea AS ENUM ('Pendiente', 'En progreso', 'Resuelta', 'Cancelada');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
    """)

    # ── Table: tarea ────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE tarea (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMPTZ,
            materia_id UUID REFERENCES materia(id) ON DELETE SET NULL,
            asignado_a UUID NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
            asignado_por UUID NOT NULL REFERENCES usuario(id) ON DELETE SET NULL,
            estado estado_tarea NOT NULL DEFAULT 'Pendiente',
            descripcion TEXT NOT NULL,
            contexto_id UUID
        )
    """)
    op.execute("CREATE INDEX ix_tarea_tenant_id ON tarea(tenant_id)")
    op.execute("CREATE INDEX ix_tarea_asignado_a ON tarea(asignado_a)")
    op.execute("CREATE INDEX ix_tarea_estado ON tarea(estado)")
    op.execute("CREATE INDEX ix_tarea_tenant_asignado ON tarea(tenant_id, asignado_a, estado) WHERE deleted_at IS NULL")
    op.execute("CREATE INDEX ix_tarea_materia_id ON tarea(materia_id)")

    # ── Table: comentario_tarea ─────────────────────────────────────────
    op.execute("""
        CREATE TABLE comentario_tarea (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL,
            tarea_id UUID NOT NULL REFERENCES tarea(id) ON DELETE CASCADE,
            autor_id UUID NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
            texto TEXT NOT NULL,
            creado_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX ix_comentario_tarea_tenant_id ON comentario_tarea(tenant_id)")
    op.execute("CREATE INDEX ix_comentario_tarea_tarea_id ON comentario_tarea(tarea_id)")


def downgrade() -> None:
    """Drop tarea and comentario_tarea tables."""
    op.execute("DROP TABLE IF EXISTS comentario_tarea CASCADE")
    op.execute("DROP TABLE IF EXISTS tarea CASCADE")
    op.execute("DROP TYPE IF EXISTS estado_tarea")
