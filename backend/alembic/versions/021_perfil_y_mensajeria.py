"""021 — Create mensaje_hilo and mensaje tables

Revision ID: 021
Revises: 020
Create Date: 2026-06-06

C-20 perfil-y-mensajeria-interna: tablas para el módulo de mensajería
interna entre usuarios registrados (mensaje_hilo, mensaje).
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "021"
down_revision: Union[str, None] = "020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create mensaje_hilo and mensaje tables."""

    # ── Table: mensaje_hilo ─────────────────────────────────────────────
    op.execute("""
        CREATE TABLE mensaje_hilo (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMPTZ,
            asunto VARCHAR(255) NOT NULL,
            usuario_a_id UUID NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
            usuario_b_id UUID NOT NULL REFERENCES usuario(id) ON DELETE CASCADE
        )
    """)
    op.execute("CREATE INDEX ix_mensaje_hilo_tenant_id ON mensaje_hilo(tenant_id)")
    op.execute("CREATE INDEX ix_mensaje_hilo_usuario_a_id ON mensaje_hilo(usuario_a_id)")
    op.execute("CREATE INDEX ix_mensaje_hilo_usuario_b_id ON mensaje_hilo(usuario_b_id)")
    # Índice de participantes para búsquedas de inbox
    op.execute(
        "CREATE INDEX ix_mensaje_hilo_participantes ON mensaje_hilo(tenant_id, usuario_a_id, usuario_b_id) "
        "WHERE deleted_at IS NULL"
    )

    # ── Table: mensaje ──────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE mensaje (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL,
            hilo_id UUID NOT NULL REFERENCES mensaje_hilo(id) ON DELETE CASCADE,
            autor_id UUID NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
            cuerpo TEXT NOT NULL,
            creado_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            leido_at TIMESTAMPTZ
        )
    """)
    op.execute("CREATE INDEX ix_mensaje_tenant_id ON mensaje(tenant_id)")
    op.execute("CREATE INDEX ix_mensaje_hilo_id ON mensaje(hilo_id)")


def downgrade() -> None:
    """Drop mensaje and mensaje_hilo tables."""
    op.execute("DROP TABLE IF EXISTS mensaje CASCADE")
    op.execute("DROP TABLE IF EXISTS mensaje_hilo CASCADE")
