"""006 — Create audit_log table + append-only trigger

Revision ID: 006
Revises: 005
Create Date: 2026-06-03

Crea la tabla ``audit_log`` (append-only, sin updated_at ni deleted_at)
y un trigger PL/pgSQL que rechaza cualquier UPDATE o DELETE sobre la tabla.

Los códigos de acción seed se documentan como comentario en el módulo
``app.models.audit_log`` — no se crea una tabla separada de catálogo
por decisión de diseño (D4 en design.md).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create audit_log table and append-only trigger."""
    # Agregar columna impersonated_by a refresh_token (para preservar
    # impersonación durante refresh rotation).
    op.add_column(
        "refresh_token",
        sa.Column(
            "impersonated_by",
            UUID(as_uuid=True),
            nullable=True,
        ),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id", UUID(as_uuid=True), nullable=False, index=True
        ),
        sa.Column(
            "fecha_hora",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "actor_id", UUID(as_uuid=True), nullable=False
        ),
        sa.Column(
            "impersonado_id", UUID(as_uuid=True), nullable=True
        ),
        sa.Column(
            "materia_id", UUID(as_uuid=True), nullable=True
        ),
        sa.Column("accion", sa.String(100), nullable=False),
        sa.Column("detalle", JSONB, nullable=True),
        sa.Column("filas_afectadas", sa.Integer, nullable=True),
        sa.Column("ip", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
    )

    # Ejecutar trigger PL/pgSQL (dos statements separados porque asyncpg
    # no soporta múltiples statements en un solo execute()).
    # El script completo está en alembic/scripts/001_audit_log_trigger.sql.
    op.execute("""
CREATE OR REPLACE FUNCTION fn_audit_log_prevent_modifications()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'audit_log is append-only: UPDATE and DELETE are not allowed'
        USING HINT = 'Audit records cannot be modified or deleted';
END;
$$;
""")
    op.execute("""
CREATE TRIGGER trg_audit_log_append_only
    BEFORE UPDATE OR DELETE
    ON audit_log
    FOR EACH ROW
    EXECUTE FUNCTION fn_audit_log_prevent_modifications();
""")


def downgrade() -> None:
    """Drop trigger, audit_log table, and revert refresh_token changes."""
    op.execute("DROP TRIGGER IF EXISTS trg_audit_log_append_only ON audit_log")
    op.execute("DROP FUNCTION IF EXISTS fn_audit_log_prevent_modifications()")
    op.drop_table("audit_log")
    op.drop_column("refresh_token", "impersonated_by")
