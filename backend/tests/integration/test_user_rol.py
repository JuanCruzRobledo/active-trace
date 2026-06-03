"""Integration tests for UserRol model + repository.

Requires PostgreSQL real (DATABASE_URL_TEST in env).
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.repositories.user_rol_repository import UserRolRepository
from tests.conftest import db_available

pytestmark = [
    pytest.mark.skipif(
        not db_available(),
        reason="Requiere PostgreSQL: definir DATABASE_URL_TEST en el entorno",
    ),
]

_DEV_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")


@pytest_asyncio.fixture
async def seed_rol_profesor(db_session: AsyncSession) -> UUID:
    """Crea el rol PROFESOR para el tenant dev."""
    rid = uuid4()
    await db_session.execute(
        text(
            "INSERT INTO rol (id, tenant_id, codigo, nombre, "
            "descripcion, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :codigo, :nombre, :descripcion, now(), now())"
        ),
        {
            "id": rid,
            "tenant_id": _DEV_TENANT_ID,
            "codigo": "PROFESOR",
            "nombre": "Profesor",
            "descripcion": "Docente",
        },
    )
    await db_session.commit()
    return rid


@pytest_asyncio.fixture
async def seed_user(db_session: AsyncSession) -> User:
    """Crea un usuario de prueba."""
    repo = UserRepository(session=db_session, tenant_id=_DEV_TENANT_ID)
    user = await repo.create(
        email="user_rol_test@test.com",
        password_hash="hash_dummy",
        is_active=True,
    )
    await db_session.commit()
    return user


class TestUserRolMigration:
    """Test 8.8: tabla user_rol existe con los campos correctos."""

    async def test_user_rol_table_exists(self, db_session: AsyncSession) -> None:
        result = await db_session.execute(
            text(
                "SELECT column_name, data_type, is_nullable "
                "FROM information_schema.columns "
                "WHERE table_name = 'user_rol' "
                "ORDER BY ordinal_position"
            )
        )
        columns = result.fetchall()
        assert len(columns) >= 5, "user_rol debe tener al menos 5 columnas"

        col_names = [c[0] for c in columns]
        assert "id" in col_names
        assert "user_id" in col_names
        assert "rol_id" in col_names
        assert "tenant_id" in col_names
        assert "created_at" in col_names

    async def test_user_rol_unique_constraint(
        self, db_session: AsyncSession, seed_rol_profesor: UUID,
        seed_dev_tenant: None,
    ) -> None:
        """No se puede asignar el mismo rol dos veces al mismo usuario."""
        from app.core.security import hash_password
        user_id = uuid4()
        await db_session.execute(
            text(
                "INSERT INTO users (id, tenant_id, email, password_hash, "
                "is_active, totp_enabled, created_at, updated_at) "
                "VALUES (:id, :tenant_id, :email, :pwd, true, false, now(), now())"
            ),
            {
                "id": user_id,
                "tenant_id": _DEV_TENANT_ID,
                "email": "unique_test@test.com",
                "pwd": hash_password("Test1234!"),
            },
        )
        await db_session.commit()

        # Primera inserción
        await db_session.execute(
            text(
                "INSERT INTO user_rol (id, user_id, rol_id, tenant_id, created_at) "
                "VALUES (:id, :user_id, :rol_id, :tenant_id, now())"
            ),
            {
                "id": uuid4(),
                "user_id": user_id,
                "rol_id": seed_rol_profesor,
                "tenant_id": _DEV_TENANT_ID,
            },
        )
        await db_session.commit()

        # Segunda inserción (mismo user + rol) debe fallar
        with pytest.raises(Exception):
            await db_session.execute(
                text(
                    "INSERT INTO user_rol (id, user_id, rol_id, tenant_id, created_at) "
                    "VALUES (:id, :user_id, :rol_id, :tenant_id, now())"
                ),
                {
                    "id": uuid4(),
                    "user_id": user_id,
                    "rol_id": seed_rol_profesor,
                    "tenant_id": _DEV_TENANT_ID,
                },
            )
            await db_session.commit()


class TestUserRolRepository:
    """Test 8.9: UserRolRepository.get_role_codigos_for_user()."""

    async def test_get_role_codigos_returns_assigned_roles(
        self,
        db_session: AsyncSession,
        seed_rol_profesor: UUID,
        seed_user: User,
        seed_dev_tenant: None,
    ) -> None:
        """Asignar PROFESOR al usuario → get_role_codigos retorna ['PROFESOR']."""
        repo = UserRolRepository(session=db_session, tenant_id=_DEV_TENANT_ID)

        # Asignar rol
        await repo.assign_role(user_id=seed_user.id, rol_id=seed_rol_profesor)
        await db_session.commit()

        codigos = await repo.get_role_codigos_for_user(user_id=seed_user.id)
        assert "PROFESOR" in codigos
        assert len(codigos) == 1

    async def test_get_role_codigos_multiple_roles(
        self,
        db_session: AsyncSession,
        seed_user: User,
        seed_dev_tenant: None,
    ) -> None:
        """Usuario con 2 roles → get_role_codigos retorna ambos."""
        repo = UserRolRepository(session=db_session, tenant_id=_DEV_TENANT_ID)

        # Crear 2 roles
        rid_alumno = uuid4()
        rid_tutor = uuid4()
        await db_session.execute(
            text(
                "INSERT INTO rol (id, tenant_id, codigo, nombre, "
                "descripcion, created_at, updated_at) "
                "VALUES (:id, :tenant_id, :codigo, :nombre, :descripcion, now(), now())"
            ),
            [
                {
                    "id": rid_alumno,
                    "tenant_id": _DEV_TENANT_ID,
                    "codigo": "ALUMNO",
                    "nombre": "Alumno",
                    "descripcion": "Estudiante",
                },
                {
                    "id": rid_tutor,
                    "tenant_id": _DEV_TENANT_ID,
                    "codigo": "TUTOR",
                    "nombre": "Tutor",
                    "descripcion": "Auxiliar",
                },
            ],
        )
        await db_session.commit()

        await repo.assign_role(user_id=seed_user.id, rol_id=rid_alumno)
        await repo.assign_role(user_id=seed_user.id, rol_id=rid_tutor)
        await db_session.commit()

        codigos = await repo.get_role_codigos_for_user(user_id=seed_user.id)
        assert "ALUMNO" in codigos
        assert "TUTOR" in codigos
        assert len(codigos) == 2

    async def test_get_role_codigos_no_roles_returns_empty(
        self,
        db_session: AsyncSession,
        seed_user: User,
        seed_dev_tenant: None,
    ) -> None:
        """Usuario sin roles → lista vacía."""
        repo = UserRolRepository(session=db_session, tenant_id=_DEV_TENANT_ID)
        codigos = await repo.get_role_codigos_for_user(user_id=seed_user.id)
        assert codigos == []
