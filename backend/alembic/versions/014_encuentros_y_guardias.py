"""014 — Create encuentros and guardias tables

Revision ID: 014
Revises: 013
Create Date: 2026-06-05

C-13 encuentros-y-guardias: tablas para el módulo de encuentros sincrónicos
(slot_encuentro, instancia_encuentro) y guardias de atención a alumnos
(guardia), con enums estado_encuentro, estado_guardia y dia_semana.

USO SQL DIRECTO porque op.create_table() con sa.Enum() activa el evento
_on_table_create de SQLAlchemy que intenta recrear los tipos existentes
a pesar de create_type=False (bug conocido en esta versión de SQLAlchemy).
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create slot_encuentro, instancia_encuentro and guardia tables."""

    # ── Enum types ──────────────────────────────────────────────────────
    # Idempotente: se salta si el tipo ya existe.
    op.execute("""
        DO $$
        BEGIN
            CREATE TYPE estado_encuentro AS ENUM ('Programado', 'Realizado', 'Cancelado');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute("""
        DO $$
        BEGIN
            CREATE TYPE estado_guardia AS ENUM ('Pendiente', 'Realizada', 'Cancelada');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute("""
        DO $$
        BEGIN
            CREATE TYPE dia_semana AS ENUM ('Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
    """)

    # ── slot_encuentro ─────────────────────────────────────────────────
    # SQL directo para evitar que sa.Enum() dispare _on_table_create.
    op.execute("""
        CREATE TABLE slot_encuentro (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL,
            asignacion_id UUID REFERENCES asignacion(id) ON DELETE SET NULL,
            materia_id UUID REFERENCES materia(id) ON DELETE SET NULL,
            titulo VARCHAR(200) NOT NULL,
            hora TIME NOT NULL,
            dia_semana dia_semana NOT NULL,
            fecha_inicio DATE NOT NULL,
            cant_semanas INTEGER NOT NULL DEFAULT 0,
            fecha_unica DATE,
            meet_url VARCHAR(500),
            vig_desde DATE,
            vig_hasta DATE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMPTZ
        )
    """)
    op.create_index("ix_slot_encuentro_tenant_id", "slot_encuentro", ["tenant_id"])
    op.create_index("ix_slot_encuentro_materia_id", "slot_encuentro", ["materia_id"])

    # ── instancia_encuentro ────────────────────────────────────────────
    op.execute("""
        CREATE TABLE instancia_encuentro (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL,
            slot_id UUID REFERENCES slot_encuentro(id) ON DELETE SET NULL,
            materia_id UUID REFERENCES materia(id) ON DELETE SET NULL,
            fecha DATE NOT NULL,
            hora TIME NOT NULL,
            titulo VARCHAR(200) NOT NULL,
            estado estado_encuentro NOT NULL DEFAULT 'Programado',
            meet_url VARCHAR(500),
            video_url VARCHAR(500),
            comentario TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMPTZ
        )
    """)
    op.create_index("ix_instancia_encuentro_tenant_id", "instancia_encuentro", ["tenant_id"])
    op.create_index("ix_instancia_encuentro_materia_id", "instancia_encuentro", ["materia_id"])
    op.create_index("ix_instancia_encuentro_slot_id", "instancia_encuentro", ["slot_id"])
    op.create_index("ix_instancia_encuentro_fecha", "instancia_encuentro", ["fecha"])

    # ── guardia ────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE guardia (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL,
            asignacion_id UUID REFERENCES asignacion(id) ON DELETE SET NULL,
            materia_id UUID REFERENCES materia(id) ON DELETE SET NULL,
            carrera_id UUID REFERENCES carrera(id) ON DELETE SET NULL,
            cohorte_id UUID REFERENCES cohorte(id) ON DELETE SET NULL,
            dia dia_semana NOT NULL,
            horario VARCHAR(50) NOT NULL,
            estado estado_guardia NOT NULL DEFAULT 'Pendiente',
            comentarios TEXT,
            creada_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMPTZ
        )
    """)
    op.create_index("ix_guardia_tenant_id", "guardia", ["tenant_id"])
    op.create_index("ix_guardia_materia_id", "guardia", ["materia_id"])
    op.create_index("ix_guardia_asignacion_id", "guardia", ["asignacion_id"])


def downgrade() -> None:
    """Drop slot_encuentro, instancia_encuentro and guardia tables."""
    op.drop_index("ix_guardia_asignacion_id", table_name="guardia")
    op.drop_index("ix_guardia_materia_id", table_name="guardia")
    op.drop_index("ix_guardia_tenant_id", table_name="guardia")
    op.drop_table("guardia")
    op.drop_index("ix_instancia_encuentro_fecha", table_name="instancia_encuentro")
    op.drop_index("ix_instancia_encuentro_slot_id", table_name="instancia_encuentro")
    op.drop_index("ix_instancia_encuentro_materia_id", table_name="instancia_encuentro")
    op.drop_index("ix_instancia_encuentro_tenant_id", table_name="instancia_encuentro")
    op.drop_table("instancia_encuentro")
    op.drop_index("ix_slot_encuentro_materia_id", table_name="slot_encuentro")
    op.drop_index("ix_slot_encuentro_tenant_id", table_name="slot_encuentro")
    op.drop_table("slot_encuentro")
    op.execute("DROP TYPE IF EXISTS estado_encuentro")
    op.execute("DROP TYPE IF EXISTS estado_guardia")
    op.execute("DROP TYPE IF EXISTS dia_semana")
