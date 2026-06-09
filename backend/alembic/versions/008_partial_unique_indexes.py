"""008 — Replace unique constraints with partial unique indexes

Revision ID: 008
Revises: 007
Create Date: 2026-06-03

Replaces plain ``UniqueConstraint`` on carrera, materia and cohorte with
partial unique indexes that only enforce uniqueness on active rows
(``deleted_at IS NULL``). This allows re-using codes/names of soft-deleted
records without violating the constraint — solving the risk identified in
the C-06 design review.

Affected tables and their new indexes:

  - ``carrera``:   ``uq_carrera_tenant_codigo_active``
                   ON (tenant_id, codigo) WHERE deleted_at IS NULL
  - ``materia``:   ``uq_materia_tenant_codigo_active``
                   ON (tenant_id, codigo) WHERE deleted_at IS NULL
  - ``cohorte``:   ``uq_cohorte_tenant_carrera_nombre_active``
                   ON (tenant_id, carrera_id, nombre) WHERE deleted_at IS NULL
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ── Helpers ──────────────────────────────────────────────────────────────

# Constraint names (defined in migration 007)
_OLD_CONSTRAINTS = {
    "carrera": "uq_carrera_tenant_codigo",
    "materia": "uq_materia_tenant_codigo",
    "cohorte": "uq_cohorte_tenant_carrera_nombre",
}

# New partial unique index names
_NEW_INDEXES = {
    "carrera": {
        "name": "uq_carrera_tenant_codigo_active",
        "columns": ["tenant_id", "codigo"],
    },
    "materia": {
        "name": "uq_materia_tenant_codigo_active",
        "columns": ["tenant_id", "codigo"],
    },
    "cohorte": {
        "name": "uq_cohorte_tenant_carrera_nombre_active",
        "columns": ["tenant_id", "carrera_id", "nombre"],
    },
}


def upgrade() -> None:
    """Drop old unique constraints, create partial unique indexes."""

    for table in ("carrera", "materia", "cohorte"):
        # 1. Drop the old unique constraint
        op.drop_constraint(
            _OLD_CONSTRAINTS[table],
            table,
            type_="unique",
        )
        # 2. Create partial unique index (only active records)
        idx = _NEW_INDEXES[table]
        op.create_index(
            idx["name"],
            table,
            idx["columns"],
            unique=True,
            postgresql_where=sa.text("deleted_at IS NULL"),
        )


def downgrade() -> None:
    """Drop partial unique indexes, re-create old unique constraints.

    NOTE: If there are soft-deleted records whose code/nombre has been
    re-used by an active record, this downgrade will fail with a
    duplicate-key violation. In practice this is a development-only
    downgrade path.
    """

    for table in ("cohorte", "materia", "carrera"):
        # 1. Drop the partial unique index
        idx = _NEW_INDEXES[table]
        op.drop_index(idx["name"], table_name=table)

    # 2. Re-create old unique constraints
    op.create_unique_constraint(
        _OLD_CONSTRAINTS["carrera"],
        "carrera",
        ["tenant_id", "codigo"],
    )
    op.create_unique_constraint(
        _OLD_CONSTRAINTS["materia"],
        "materia",
        ["tenant_id", "codigo"],
    )
    op.create_unique_constraint(
        _OLD_CONSTRAINTS["cohorte"],
        "cohorte",
        ["tenant_id", "carrera_id", "nombre"],
    )
