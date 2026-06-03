"""Seed script para desarrollo — unifica la creación de datos de prueba.

Crea (si no existen):
  • Tenant de desarrollo (id: 00000000-0000-0000-0000-000000000001)
  • Roles: ADMIN, PROFESOR, TUTOR, COORDINADOR
  • admin@trace.dev / Admin123456!  (roles: ADMIN, PROFESOR)
  • target@test.com  / Target123456! (rol: PROFESOR)
  • admin2@test.com  / Admin123456!  (rol: ADMIN)

Idempotente: se puede ejecutar N veces sin duplicar datos.

Uso:
    cd backend
    python scripts/seed.py

Requiere:
    - Variables de entorno en .env (DATABASE_URL, ENCRYPTION_KEY, etc.)
    - Base de datos migrada (alembic upgrade head)
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from uuid import UUID, uuid4

_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from sqlalchemy import select, text

from app.core.config import Settings
from app.core.database import close_engine, get_session_maker, init_engine
from app.core.security import hash_password
from app.repositories.user_repository import UserRepository

# ── Constantes ──────────────────────────────────────────────────────────

DEV_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")

ROLES = [
    ("ADMIN", "Administrador del sistema"),
    ("PROFESOR", "Profesor/docente"),
    ("TUTOR", "Tutor"),
    ("COORDINADOR", "Coordinador académico"),
]

USERS = [
    {
        "email": "admin@trace.dev",
        "password": "Admin123456!",
        "roles": ["ADMIN", "PROFESOR"],
        "desc": "Admin principal — tiene impersonacion:usar",
    },
    {
        "email": "target@test.com",
        "password": "Target123456!",
        "roles": ["PROFESOR"],
        "desc": "Target para impersonar — SIN impersonacion:usar",
    },
    {
        "email": "admin2@test.com",
        "password": "Admin123456!",
        "roles": ["ADMIN"],
        "desc": "Segundo admin — CON impersonacion:usar",
    },
]


# ── Helpers ─────────────────────────────────────────────────────────────


async def ensure_tenant_exists(session) -> None:
    """Crea el tenant de desarrollo si no existe."""
    result = await session.execute(
        text("SELECT id FROM tenant WHERE id = :tid"),
        {"tid": DEV_TENANT_ID},
    )
    if result.fetchone() is not None:
        print("  [~] Tenant de desarrollo ya existe")
        return

    await session.execute(
        text(
            "INSERT INTO tenant (id, tenant_id, nombre, created_at, updated_at) "
            "VALUES (:tid, :tid, 'Tenant Dev', now(), now())"
        ),
        {"tid": DEV_TENANT_ID},
    )
    print("  [+] Tenant de desarrollo creado")


async def ensure_roles(session) -> dict[str, UUID]:
    """Crea los roles si no existen. Devuelve {codigo: id}."""
    role_ids: dict[str, UUID] = {}

    for codigo, descripcion in ROLES:
        result = await session.execute(
            text("SELECT id FROM rol WHERE codigo = :cod AND tenant_id = :tid"),
            {"cod": codigo, "tid": DEV_TENANT_ID},
        )
        row = result.fetchone()
        if row is not None:
            role_ids[codigo] = row[0]
            print(f"  [~] Rol {codigo} ya existe")
        else:
            rid = uuid4()
            await session.execute(
                text(
                    "INSERT INTO rol (id, codigo, descripcion, tenant_id, created_at, updated_at) "
                    "VALUES (:id, :cod, :desc, :tid, now(), now())"
                ),
                {"id": rid, "cod": codigo, "desc": descripcion, "tid": DEV_TENANT_ID},
            )
            role_ids[codigo] = rid
            print(f"  [+] Rol {codigo} creado")

    return role_ids


async def ensure_user(
    session, email: str, password: str, role_ids: dict[str, UUID], roles: list[str]
) -> UUID:
    """Crea un usuario y le asigna roles si no existe. Devuelve su UUID."""
    repo = UserRepository(session=session, tenant_id=DEV_TENANT_ID)

    # Buscar por email
    result = await session.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": email},
    )
    row = result.fetchone()
    if row is not None:
        uid = row[0]
        print(f"  [~] Usuario {email} ya existe (UUID: {uid})")
        return uid

    # Crear usuario
    user = await repo.create(
        email=email,
        password_hash=hash_password(password),
    )
    uid = user.id
    print(f"  [+] Usuario {email} creado (UUID: {uid})")

    # Asignar roles
    for rol in roles:
        rid = role_ids.get(rol)
        if rid is None:
            print(f"      [!] Rol '{rol}' no encontrado, saltando")
            continue

        await session.execute(
            text(
                "INSERT INTO user_rol (id, user_id, rol_id, tenant_id, created_at) "
                "VALUES (:id, :uid, :rid, :tid, now()) "
                "ON CONFLICT (user_id, rol_id) DO NOTHING"
            ),
            {"id": uuid4(), "uid": uid, "rid": rid, "tid": DEV_TENANT_ID},
        )
        print(f"      Rol asignado: {rol}")

    return uid


# ── Main ────────────────────────────────────────────────────────────────


async def main() -> None:
    settings = Settings()
    db_display = (
        settings.DATABASE_URL.split("@")[1]
        if "@" in settings.DATABASE_URL
        else settings.DATABASE_URL
    )
    print(f"\nConectando a {db_display}...\n")

    await close_engine()
    init_engine(settings.DATABASE_URL, encryption_key=settings.ENCRYPTION_KEY)
    maker = get_session_maker()

    async with maker() as session:
        await ensure_tenant_exists(session)
        role_ids = await ensure_roles(session)

        print()
        for user_cfg in USERS:
            await ensure_user(
                session,
                email=user_cfg["email"],
                password=user_cfg["password"],
                role_ids=role_ids,
                roles=user_cfg["roles"],
            )

        await session.commit()

    await close_engine()
    print(f"\n[OK] Seed completado. {len(USERS)} usuarios listos.\n")


if __name__ == "__main__":
    asyncio.run(main())
