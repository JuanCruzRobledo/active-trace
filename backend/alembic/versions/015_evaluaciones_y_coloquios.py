"""015 — Create evaluaciones and coloquios tables

Revision ID: 015
Revises: 014
Create Date: 2026-06-05

C-14 evaluaciones-y-coloquios: tablas para el modulo de evaluaciones orales
(evaluacion, reserva_evaluacion, resultado_evaluacion), con enums
tipo_evaluacion, estado_evaluacion y estado_reserva.

USO SQL DIRECTO porque op.create_table() con sa.Enum() activa el evento
_on_table_create de SQLAlchemy que intenta recrear los tipos existentes
a pesar de create_type=False (bug conocido en esta version de SQLAlchemy).
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create evaluacion, reserva_evaluacion and resultado_evaluacion tables."""

    # ── Enum types ──────────────────────────────────────────────────────
    op.execute("""
        DO $$
        BEGIN
            CREATE TYPE tipo_evaluacion AS ENUM ('Parcial', 'TP', 'Coloquio', 'Recuperatorio');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute("""
        DO $$
        BEGIN
            CREATE TYPE estado_evaluacion AS ENUM ('Activa', 'Inactiva');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute("""
        DO $$
        BEGIN
            CREATE TYPE estado_reserva AS ENUM ('Activa', 'Cancelada');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
    """)

    # ── evaluacion ─────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE evaluacion (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenant(id),
            materia_id UUID NOT NULL REFERENCES materia(id) ON DELETE CASCADE,
            cohorte_id UUID NOT NULL REFERENCES cohorte(id) ON DELETE CASCADE,
            tipo tipo_evaluacion NOT NULL,
            instancia VARCHAR(200) NOT NULL,
            dias_disponibles INTEGER NOT NULL DEFAULT 1,
            cupos_por_dia INTEGER NOT NULL DEFAULT 1,
            fecha_inicio DATE NOT NULL,
            fecha_fin DATE NOT NULL,
            estado estado_evaluacion NOT NULL DEFAULT 'Activa',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMPTZ
        )
    """)
    op.create_index("ix_evaluacion_tenant_id", "evaluacion", ["tenant_id"])
    op.create_index("ix_evaluacion_materia_id", "evaluacion", ["materia_id"])
    op.create_index("ix_evaluacion_cohorte_id", "evaluacion", ["cohorte_id"])

    # ── reserva_evaluacion ──────────────────────────────────────────────
    op.execute("""
        CREATE TABLE reserva_evaluacion (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenant(id),
            evaluacion_id UUID NOT NULL REFERENCES evaluacion(id) ON DELETE CASCADE,
            alumno_id UUID NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
            fecha_hora TIMESTAMPTZ NOT NULL,
            estado estado_reserva NOT NULL DEFAULT 'Activa',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMPTZ
        )
    """)
    op.create_index("ix_reserva_evaluacion_tenant_id", "reserva_evaluacion", ["tenant_id"])
    op.create_index("ix_reserva_evaluacion_evaluacion_id", "reserva_evaluacion", ["evaluacion_id"])
    op.create_index("ix_reserva_evaluacion_alumno_id", "reserva_evaluacion", ["alumno_id"])

    # ── resultado_evaluacion ────────────────────────────────────────────
    op.execute("""
        CREATE TABLE resultado_evaluacion (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenant(id),
            evaluacion_id UUID NOT NULL REFERENCES evaluacion(id) ON DELETE CASCADE,
            alumno_id UUID NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
            nota_final VARCHAR(100) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMPTZ
        )
    """)
    op.create_index("ix_resultado_evaluacion_tenant_id", "resultado_evaluacion", ["tenant_id"])
    op.create_index("ix_resultado_evaluacion_evaluacion_id", "resultado_evaluacion", ["evaluacion_id"])
    op.create_index("ix_resultado_evaluacion_alumno_id", "resultado_evaluacion", ["alumno_id"])
    op.create_unique_constraint(
        "uq_resultado_evaluacion_alumno",
        "resultado_evaluacion",
        ["evaluacion_id", "alumno_id", "tenant_id"],
    )


def downgrade() -> None:
    """Drop evaluacion, reserva_evaluacion and resultado_evaluacion tables."""
    op.drop_index("ix_resultado_evaluacion_alumno_id", table_name="resultado_evaluacion")
    op.drop_index("ix_resultado_evaluacion_evaluacion_id", table_name="resultado_evaluacion")
    op.drop_index("ix_resultado_evaluacion_tenant_id", table_name="resultado_evaluacion")
    op.drop_table("resultado_evaluacion")
    op.drop_index("ix_reserva_evaluacion_alumno_id", table_name="reserva_evaluacion")
    op.drop_index("ix_reserva_evaluacion_evaluacion_id", table_name="reserva_evaluacion")
    op.drop_index("ix_reserva_evaluacion_tenant_id", table_name="reserva_evaluacion")
    op.drop_table("reserva_evaluacion")
    op.drop_index("ix_evaluacion_cohorte_id", table_name="evaluacion")
    op.drop_index("ix_evaluacion_materia_id", table_name="evaluacion")
    op.drop_index("ix_evaluacion_tenant_id", table_name="evaluacion")
    op.drop_table("evaluacion")
    op.execute("DROP TYPE IF EXISTS tipo_evaluacion")
    op.execute("DROP TYPE IF EXISTS estado_evaluacion")
    op.execute("DROP TYPE IF EXISTS estado_reserva")
