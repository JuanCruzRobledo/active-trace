"""005 — Seed dev user for manual testing via Swagger

Revision ID: 005
Revises: 004
Create Date: 2026-06-03

Inserts a development user with known credentials and multiple roles
(ADMIN + PROFESOR) so developers can test the auth flow and RBAC
permissions manually from http://localhost:8000/docs without needing
to run tests first.

Credentials:
    email:    admin@trace.dev
    password: Admin123456!

The password hash is generated at migration time using the app's own
``hash_password()`` (Argon2id), ensuring it's compatible with
``verify_password()`` at login time.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DEV_TENANT_ID = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    """Insert dev tenant + dev user + role assignments."""
    # Import here to avoid circular imports at module level
    from app.core.security import hash_password  # noqa: PLC0415

    conn = op.get_bind()

    # 0. Ensure dev tenant exists before inserting user (FK requirement)
    #    tenant_id = id for the root tenant record (self-reference)
    conn.execute(
        sa.text(
            "INSERT INTO tenant (id, tenant_id, nombre, created_at, updated_at) "
            "VALUES (:tid, :tid, 'Tenant Dev', now(), now()) "
            "ON CONFLICT (id) DO NOTHING"
        ),
        {"tid": _DEV_TENANT_ID},
    )

    # 1. Generate Argon2id hash for the known dev password
    pwd_hash = hash_password("Admin123456!")

    # 2. Insert user
    result = conn.execute(
        sa.text(
            "INSERT INTO users (id, tenant_id, email, password_hash, "
            "is_active, created_at, updated_at) "
            "VALUES (gen_random_uuid(), :tenant_id, :email, :pwd_hash, "
            "true, now(), now()) RETURNING id"
        ),
        {
            "tenant_id": _DEV_TENANT_ID,
            "email": "admin@trace.dev",
            "pwd_hash": pwd_hash,
        },
    )
    user_id = result.scalar_one()

    # 3. Assign two roles so we can verify multi-role union in /me
    for rol_codigo in ("ADMIN", "PROFESOR"):
        conn.execute(
            sa.text(
                "INSERT INTO user_rol (id, user_id, rol_id, tenant_id, created_at) "
                "SELECT gen_random_uuid(), :user_id, r.id, r.tenant_id, now() "
                "FROM rol r "
                "WHERE r.codigo = :rol_codigo AND r.tenant_id = :tenant_id"
            ),
            {
                "user_id": user_id,
                "rol_codigo": rol_codigo,
                "tenant_id": _DEV_TENANT_ID,
            },
        )


def downgrade() -> None:
    """Remove the dev user (cascade removes user_rol rows)."""
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "DELETE FROM users "
            "WHERE email = :email AND tenant_id = :tenant_id"
        ),
        {
            "email": "admin@trace.dev",
            "tenant_id": _DEV_TENANT_ID,
        },
    )
