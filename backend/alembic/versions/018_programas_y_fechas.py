"""018 — Create programa_materia and fecha_academica tables

Revision ID: 018
Revises: 017
Create Date: 2026-06-06

C-17 programas-y-fechas-academicas: tablas para gestion de programas de
materia (documentos oficiales) y fechas academicas (instancias evaluativas).
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "018"
down_revision: Union[str, None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create programa_materia and fecha_academica tables."""

    # ── Enum type for fecha_academica ────────────────────────────────────
    op.execute("""
        DO $$
        BEGIN
            CREATE TYPE tipo_fecha_academica AS ENUM ('Parcial', 'TP', 'Coloquio', 'Recuperatorio');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
    """)

    # ── Table: programa_materia ───────────────────────────────────────────
    op.execute("""
        CREATE TABLE programa_materia (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMPTZ,
            materia_id UUID NOT NULL REFERENCES materia(id) ON DELETE CASCADE,
            carrera_id UUID NOT NULL REFERENCES carrera(id) ON DELETE CASCADE,
            cohorte_id UUID NOT NULL REFERENCES cohorte(id) ON DELETE CASCADE,
            titulo VARCHAR(300) NOT NULL,
            referencia_archivo UUID NOT NULL,
            cargado_at TIMESTAMPTZ NOT NULL
        )
    """)
    op.execute("CREATE INDEX ix_programa_materia_tenant_id ON programa_materia(tenant_id)")
    op.execute("CREATE INDEX ix_programa_materia_materia_id ON programa_materia(materia_id)")
    op.execute("CREATE INDEX ix_programa_materia_carrera_id ON programa_materia(carrera_id)")
    op.execute("CREATE INDEX ix_programa_materia_cohorte_id ON programa_materia(cohorte_id)")
    op.execute("""
        CREATE UNIQUE INDEX uq_programa_materia_tenant_materia_carrera_cohorte
        ON programa_materia(tenant_id, materia_id, carrera_id, cohorte_id)
    """)

    # ── Table: fecha_academica ────────────────────────────────────────────
    op.execute("""
        CREATE TABLE fecha_academica (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMPTZ,
            materia_id UUID NOT NULL REFERENCES materia(id) ON DELETE CASCADE,
            cohorte_id UUID NOT NULL REFERENCES cohorte(id) ON DELETE CASCADE,
            tipo tipo_fecha_academica NOT NULL,
            numero INTEGER NOT NULL,
            periodo VARCHAR(20) NOT NULL,
            fecha DATE NOT NULL,
            titulo VARCHAR(300) NOT NULL
        )
    """)
    op.execute("CREATE INDEX ix_fecha_academica_tenant_id ON fecha_academica(tenant_id)")
    op.execute("CREATE INDEX ix_fecha_academica_materia_id ON fecha_academica(materia_id)")
    op.execute("CREATE INDEX ix_fecha_academica_cohorte_id ON fecha_academica(cohorte_id)")
    op.execute("""
        CREATE UNIQUE INDEX uq_fecha_academica_tenant_materia_cohorte_tipo_numero
        ON fecha_academica(tenant_id, materia_id, cohorte_id, tipo, numero)
        WHERE deleted_at IS NULL
    """)


def downgrade() -> None:
    """Drop fecha_academica and programa_materia tables."""
    op.execute("DROP TABLE IF EXISTS fecha_academica CASCADE")
    op.execute("DROP TABLE IF EXISTS programa_materia CASCADE")
    op.execute("DROP TYPE IF EXISTS tipo_fecha_academica")
