"""020 — Seed default ClavePlus keys for DEV tenant

Revision ID: 020
Revises: 019
Create Date: 2026-06-06

C-18 liquidaciones-y-honorarios: inserta 8 claves de plus salarial por
defecto para el tenant de desarrollo (0000...001):

    PROG — Programación
    BD   — Base de Datos
    MAT  — Matemática
    ING  — Inglés
    RED  — Redes
    WEB  — Web
    GES  — Gestión
    IDI  — Idiomas

Cada tenant puede agregar las suyas via CRUD. Solo las que tengan materias
asignadas generan plus salarial.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "020"
down_revision: Union[str, None] = "019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DEV_TENANT_ID = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    conn = op.get_bind()

    claves = [
        ("PROG", "Programación"),
        ("BD", "Base de Datos"),
        ("MAT", "Matemática"),
        ("ING", "Inglés"),
        ("RED", "Redes"),
        ("WEB", "Web"),
        ("GES", "Gestión"),
        ("IDI", "Idiomas"),
    ]
    for codigo, nombre in claves:
        conn.execute(
            sa.text(
                "INSERT INTO clave_plus (id, tenant_id, codigo, nombre, activa, created_at, updated_at) "
                "VALUES (gen_random_uuid(), :tenant_id, :codigo, :nombre, true, now(), now()) "
                "ON CONFLICT (tenant_id, codigo) WHERE deleted_at IS NULL DO NOTHING"
            ),
            {"tenant_id": _DEV_TENANT_ID, "codigo": codigo, "nombre": nombre},
        )


def downgrade() -> None:
    conn = op.get_bind()
    codigos = ["PROG", "BD", "MAT", "ING", "RED", "WEB", "GES", "IDI"]
    for codigo in codigos:
        conn.execute(
            sa.text(
                "DELETE FROM clave_plus WHERE tenant_id = :tenant_id AND codigo = :codigo"
            ),
            {"tenant_id": _DEV_TENANT_ID, "codigo": codigo},
        )
