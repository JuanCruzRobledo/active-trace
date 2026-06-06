"""016 — Create avisos and acknowledgment tables

Revision ID: 016
Revises: 015
Create Date: 2026-06-05

C-15 avisos-y-acknowledgment: tablas para el modulo de avisos institucionales
(aviso, acknowledgment_aviso), con enums alcance_aviso y severidad_aviso.
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create aviso and acknowledgment_aviso tables."""

    # ── Enum types ──────────────────────────────────────────────────────
    op.execute("""
        DO $$
        BEGIN
            CREATE TYPE alcance_aviso AS ENUM ('Global', 'PorMateria', 'PorCohorte', 'PorRol');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute("""
        DO $$
        BEGIN
            CREATE TYPE severidad_aviso AS ENUM ('Info', 'Advertencia', 'Crítico');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
    """)

    # ── Table: aviso ───────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE aviso (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMPTZ,
            alcance alcance_aviso NOT NULL,
            materia_id UUID REFERENCES materia(id) ON DELETE SET NULL,
            cohorte_id UUID REFERENCES cohorte(id) ON DELETE SET NULL,
            rol_destino VARCHAR(50),
            severidad severidad_aviso NOT NULL,
            titulo VARCHAR(200) NOT NULL,
            cuerpo TEXT NOT NULL,
            inicio_en TIMESTAMPTZ NOT NULL,
            fin_en TIMESTAMPTZ NOT NULL,
            orden INTEGER NOT NULL DEFAULT 0,
            activo BOOLEAN NOT NULL DEFAULT TRUE,
            requiere_ack BOOLEAN NOT NULL DEFAULT FALSE
        )
    """)
    op.execute("CREATE INDEX ix_aviso_tenant_id ON aviso(tenant_id)")
    op.execute("CREATE INDEX ix_aviso_inicio_fin ON aviso(inicio_en, fin_en)")
    op.execute("CREATE INDEX ix_aviso_tenant_activo ON aviso(tenant_id, activo) WHERE activo = TRUE AND deleted_at IS NULL")
    op.execute("CREATE INDEX ix_aviso_materia_id ON aviso(materia_id)")
    op.execute("CREATE INDEX ix_aviso_cohorte_id ON aviso(cohorte_id)")

    # ── Table: acknowledgment_aviso ─────────────────────────────────────
    op.execute("""
        CREATE TABLE acknowledgment_aviso (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMPTZ,
            aviso_id UUID NOT NULL REFERENCES aviso(id) ON DELETE CASCADE,
            usuario_id UUID NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
            confirmado_at TIMESTAMPTZ NOT NULL
        )
    """)
    op.execute("CREATE INDEX ix_acknowledgment_aviso_tenant_id ON acknowledgment_aviso(tenant_id)")
    op.execute("CREATE INDEX ix_acknowledgment_aviso_aviso_id ON acknowledgment_aviso(aviso_id)")
    op.execute("CREATE UNIQUE INDEX uq_acknowledgment_aviso_usuario ON acknowledgment_aviso(aviso_id, usuario_id)")


def downgrade() -> None:
    """Drop aviso and acknowledgment_aviso tables."""
    op.execute("DROP TABLE IF EXISTS acknowledgment_aviso CASCADE")
    op.execute("DROP TABLE IF EXISTS aviso CASCADE")
    op.execute("DROP TYPE IF EXISTS severidad_aviso")
    op.execute("DROP TYPE IF EXISTS alcance_aviso")
