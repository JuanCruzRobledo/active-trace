"""019 — Create liquidaciones y honorarios tables

Revision ID: 019
Revises: 018
Create Date: 2026-06-06

C-18 liquidaciones-y-honorarios: clave_plus, salario_base, salario_plus,
liquidacion, factura tables + clave_plus_id on materia.
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "019"
down_revision: Union[str, None] = "018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create liquidaciones y honorarios tables."""

    # ── Table: clave_plus ─────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE clave_plus (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMPTZ,
            codigo VARCHAR(20) NOT NULL,
            nombre VARCHAR(200) NOT NULL,
            activa BOOLEAN NOT NULL DEFAULT TRUE
        )
    """)
    op.execute("CREATE INDEX ix_clave_plus_tenant_id ON clave_plus(tenant_id)")
    op.execute("""
        CREATE UNIQUE INDEX uq_clave_plus_tenant_codigo_active
        ON clave_plus(tenant_id, codigo)
        WHERE deleted_at IS NULL
    """)

    # ── Table: salario_base ────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE salario_base (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMPTZ,
            rol VARCHAR(50) NOT NULL,
            monto NUMERIC(12, 2) NOT NULL,
            desde DATE NOT NULL,
            hasta DATE
        )
    """)
    op.execute("CREATE INDEX ix_salario_base_tenant_id ON salario_base(tenant_id)")
    op.execute("""
        CREATE INDEX ix_salario_base_rol_vigencia
        ON salario_base(tenant_id, rol, desde)
    """)

    # ── Table: salario_plus ────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE salario_plus (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMPTZ,
            grupo VARCHAR(20) NOT NULL,
            rol VARCHAR(50) NOT NULL,
            descripcion VARCHAR(200),
            monto NUMERIC(12, 2) NOT NULL,
            desde DATE NOT NULL,
            hasta DATE
        )
    """)
    op.execute("CREATE INDEX ix_salario_plus_tenant_id ON salario_plus(tenant_id)")
    op.execute("""
        CREATE INDEX ix_salario_plus_grupo_rol_vigencia
        ON salario_plus(tenant_id, grupo, rol, desde)
    """)

    # ── Table: liquidacion ─────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE liquidacion (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMPTZ,
            cohorte_id UUID NOT NULL REFERENCES cohorte(id) ON DELETE CASCADE,
            periodo VARCHAR(7) NOT NULL,
            usuario_id UUID NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
            rol VARCHAR(50) NOT NULL,
            comisiones JSONB,
            monto_base NUMERIC(12, 2) NOT NULL,
            monto_plus NUMERIC(12, 2) NOT NULL DEFAULT 0,
            total NUMERIC(12, 2) NOT NULL,
            es_nexo BOOLEAN NOT NULL DEFAULT FALSE,
            excluido_por_factura BOOLEAN NOT NULL DEFAULT FALSE,
            estado VARCHAR(20) NOT NULL DEFAULT 'Abierta',
            cerrada_at UUID REFERENCES audit_log(id) ON DELETE SET NULL
        )
    """)
    op.execute("CREATE INDEX ix_liquidacion_tenant_id ON liquidacion(tenant_id)")
    op.execute("CREATE INDEX ix_liquidacion_periodo ON liquidacion(periodo)")
    op.execute("CREATE INDEX ix_liquidacion_usuario_id ON liquidacion(usuario_id)")
    op.execute("CREATE INDEX ix_liquidacion_cohorte_id ON liquidacion(cohorte_id)")
    op.execute("""
        CREATE UNIQUE INDEX uq_liquidacion_periodo_usuario_rol_active
        ON liquidacion(tenant_id, periodo, usuario_id, rol)
        WHERE deleted_at IS NULL
    """)

    # ── Table: factura ─────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE factura (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMPTZ,
            usuario_id UUID NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
            periodo VARCHAR(7) NOT NULL,
            detalle VARCHAR(1000),
            referencia_archivo VARCHAR(500),
            tamano_kb INTEGER,
            estado VARCHAR(20) NOT NULL DEFAULT 'Pendiente',
            cargada_at TIMESTAMPTZ NOT NULL,
            abonada_at TIMESTAMPTZ
        )
    """)
    op.execute("CREATE INDEX ix_factura_tenant_id ON factura(tenant_id)")
    op.execute("CREATE INDEX ix_factura_usuario_id ON factura(usuario_id)")
    op.execute("CREATE INDEX ix_factura_periodo ON factura(periodo)")

    # ── Alter materia — add clave_plus_id column ───────────────────────────
    op.execute("""
        ALTER TABLE materia
        ADD COLUMN clave_plus_id UUID REFERENCES clave_plus(id) ON DELETE SET NULL
    """)


def downgrade() -> None:
    """Drop liquidaciones y honorarios tables."""
    op.execute("ALTER TABLE materia DROP COLUMN IF EXISTS clave_plus_id")
    op.execute("DROP TABLE IF EXISTS factura CASCADE")
    op.execute("DROP TABLE IF EXISTS liquidacion CASCADE")
    op.execute("DROP TABLE IF EXISTS salario_plus CASCADE")
    op.execute("DROP TABLE IF EXISTS salario_base CASCADE")
    op.execute("DROP TABLE IF EXISTS clave_plus CASCADE")
