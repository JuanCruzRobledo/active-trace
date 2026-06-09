"""Integration tests for login flow with roles (8.10, 8.11).

Tests the full cycle: user creation → role assignment → login → JWT with roles
→ GET /me → permisos efectivos.

Requires PostgreSQL real (DATABASE_URL_TEST in env).
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    JWT_CLAIM_ROLES,
    decode_access_token,
)
from app.repositories.user_repository import UserRepository
from app.repositories.user_rol_repository import UserRolRepository
from app.models.user_rol import UserRol
from tests.conftest import _DEV_TENANT_ID, db_available

_SECRET_KEY = "a" * 64


@pytest.fixture(autouse=True)
def _patch_env(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", _SECRET_KEY)
    monkeypatch.setenv("ENCRYPTION_KEY", "b" * 32)
    monkeypatch.setenv("DATABASE_URL", "placeholder")


@pytest_asyncio.fixture
async def seed_full_rbac(db_session: AsyncSession) -> dict:
    """Seed RBAC completo: permisos, roles, matrix, user, user_rol."""
    from app.core.security import hash_password

    # 1. Permisos (subset para el test)
    perm_ids = {}
    permisos = [
        ("ver_estado_academico", "Ver estado"),
        ("calificaciones:importar", "Importar calificaciones"),
        ("atrasados:ver", "Ver atrasados"),
    ]
    for codigo, desc in permisos:
        pid = uuid4()
        await db_session.execute(
            text(
                "INSERT INTO permiso (id, codigo, descripcion, created_at) "
                "VALUES (:id, :codigo, :descripcion, now())"
            ),
            {"id": pid, "codigo": codigo, "descripcion": desc},
        )
        perm_ids[codigo] = pid

    # 2. Rol PROFESOR
    rid_profesor = uuid4()
    await db_session.execute(
        text(
            "INSERT INTO rol (id, tenant_id, codigo, nombre, "
            "descripcion, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :codigo, :nombre, :descripcion, now(), now())"
        ),
        {
            "id": rid_profesor,
            "tenant_id": _DEV_TENANT_ID,
            "codigo": "PROFESOR",
            "nombre": "Profesor",
            "descripcion": "Docente",
        },
    )

    # 3. Rol ALUMNO
    rid_alumno = uuid4()
    await db_session.execute(
        text(
            "INSERT INTO rol (id, tenant_id, codigo, nombre, "
            "descripcion, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :codigo, :nombre, :descripcion, now(), now())"
        ),
        {
            "id": rid_alumno,
            "tenant_id": _DEV_TENANT_ID,
            "codigo": "ALUMNO",
            "nombre": "Alumno",
            "descripcion": "Estudiante",
        },
    )

    # 4. Matrix: PROFESOR → calificaciones:importar, atrasados:ver
    await db_session.execute(
        text(
            "INSERT INTO rol_permiso (id, tenant_id, rol_id, permiso_id, created_at) "
            "VALUES (:id, :tenant_id, :rol_id, :permiso_id, now())"
        ),
        [
            {
                "id": uuid4(),
                "tenant_id": _DEV_TENANT_ID,
                "rol_id": rid_profesor,
                "permiso_id": perm_ids["calificaciones:importar"],
            },
            {
                "id": uuid4(),
                "tenant_id": _DEV_TENANT_ID,
                "rol_id": rid_profesor,
                "permiso_id": perm_ids["atrasados:ver"],
            },
            {
                "id": uuid4(),
                "tenant_id": _DEV_TENANT_ID,
                "rol_id": rid_alumno,
                "permiso_id": perm_ids["ver_estado_academico"],
            },
        ],
    )

    # 5. Usuario PROFESOR
    user_repo = UserRepository(session=db_session, tenant_id=_DEV_TENANT_ID)
    user_profesor = await user_repo.create(
        email="profesor_test@flow.com",
        password_hash=hash_password("Test1234!"),
        is_active=True,
    )

    # 6. Usuario ALUMNO (sin roles en DB)
    user_alumno = await user_repo.create(
        email="alumno_test@flow.com",
        password_hash=hash_password("Test1234!"),
        is_active=True,
    )

    # 7. Asignar PROFESOR al user_profesor
    ur_repo = UserRolRepository(session=db_session, tenant_id=_DEV_TENANT_ID)
    await ur_repo.assign_role(user_id=user_profesor.id, rol_id=rid_profesor)

    await db_session.commit()

    return {
        "user_profesor_id": user_profesor.id,
        "user_alumno_id": user_alumno.id,
    }


@pytest_asyncio.fixture
async def client(settings, db_engine, seed_dev_tenant, seed_full_rbac) -> AsyncClient:
    """HTTP client with seeded RBAC data."""
    from app.main import create_app

    application = create_app(settings)
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestLoginFlow:
    """Test 8.10: Login + JWT con roles."""

    async def test_login_returns_jwt_with_roles(
        self, client: AsyncClient
    ) -> None:
        """Login como PROFESOR → JWT contiene roles=['PROFESOR']."""
        resp = await client.post(
            "/api/auth/login",
            json={"email": "profesor_test@flow.com", "password": "Test1234!"},
            headers={"X-Tenant-Id": str(_DEV_TENANT_ID)},
        )
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        body = resp.json()

        assert "access_token" in body
        token = body["access_token"]

        # Decodificar JWT y verificar claim roles
        payload = decode_access_token(token, _SECRET_KEY)
        roles = payload.get(JWT_CLAIM_ROLES, [])
        assert "PROFESOR" in roles, f"Expected PROFESOR in roles, got {roles}"

    async def test_login_without_roles_returns_empty_roles(
        self, client: AsyncClient
    ) -> None:
        """Usuario sin roles en DB → JWT roles=[]."""
        resp = await client.post(
            "/api/auth/login",
            json={"email": "alumno_test@flow.com", "password": "Test1234!"},
            headers={"X-Tenant-Id": str(_DEV_TENANT_ID)},
        )
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        body = resp.json()

        payload = decode_access_token(body["access_token"], _SECRET_KEY)
        roles = payload.get(JWT_CLAIM_ROLES, [])
        assert roles == [], f"Expected empty roles, got {roles}"


class TestMeEndpointConRoles:
    """Test 8.10 (cont): GET /me con roles cargados."""

    async def test_me_returns_roles_and_permisos(
        self, client: AsyncClient
    ) -> None:
        """Login + /me devuelve roles y permisos del usuario."""
        resp = await client.post(
            "/api/auth/login",
            json={"email": "profesor_test@flow.com", "password": "Test1234!"},
            headers={"X-Tenant-Id": str(_DEV_TENANT_ID)},
        )
        assert resp.status_code == 200
        token = resp.json()["access_token"]

        # GET /me
        resp = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.json()

        assert body["roles"] == ["PROFESOR"], f"Roles: {body['roles']}"
        assert "calificaciones:importar" in body["permisos"], (
            f"Permisos: {body['permisos']}"
        )
        assert "atrasados:ver" in body["permisos"]
        assert "ver_estado_academico" not in body["permisos"], (
            "PROFESOR no debe tener ver_estado_academico"
        )

    async def test_me_without_roles_returns_empty(
        self, client: AsyncClient
    ) -> None:
        """Usuario sin roles → /me roles=[], permisos=[]."""
        resp = await client.post(
            "/api/auth/login",
            json={"email": "alumno_test@flow.com", "password": "Test1234!"},
            headers={"X-Tenant-Id": str(_DEV_TENANT_ID)},
        )
        assert resp.status_code == 200
        token = resp.json()["access_token"]

        resp = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.json()

        assert body["roles"] == [], f"Roles: {body['roles']}"
        assert body["permisos"] == [], f"Permisos: {body['permisos']}"


class TestRefreshConRoles:
    """8.11 Refresh flow: los roles sobreviven a la rotación."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(not db_available(), reason="No PostgreSQL")
    async def test_refresh_preserves_roles(
        self,
        client: AsyncClient,
        seed_full_rbac: dict,
    ) -> None:
        """Refresh token → nuevo access token mantiene los roles."""
        # 1. Login
        resp = await client.post(
            "/api/auth/login",
            json={"email": "profesor_test@flow.com", "password": "Test1234!"},
            headers={"X-Tenant-Id": str(_DEV_TENANT_ID)},
        )
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        body = resp.json()
        refresh_token = body["refresh_token"]

        # 2. Refresh
        resp = await client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token},
            headers={"X-Tenant-Id": str(_DEV_TENANT_ID)},
        )
        assert resp.status_code == 200, f"Refresh failed: {resp.text}"
        new_body = resp.json()
        new_access = new_body["access_token"]
        new_refresh = new_body["refresh_token"]

        # 3. El nuevo access token debe tener PROFESOR en roles
        payload = decode_access_token(new_access, _SECRET_KEY)
        assert "PROFESOR" in payload.get(JWT_CLAIM_ROLES, []), (
            f"Expected PROFESOR in refreshed JWT, got {payload.get(JWT_CLAIM_ROLES)}"
        )

        # 4. /me con el nuevo token muestra roles
        resp = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {new_access}"},
        )
        assert resp.status_code == 200
        me = resp.json()
        assert me["roles"] == ["PROFESOR"], f"Roles after refresh: {me['roles']}"

        # 5. Segundo refresh del nuevo refresh token también funciona
        resp = await client.post(
            "/api/auth/refresh",
            json={"refresh_token": new_refresh},
            headers={"X-Tenant-Id": str(_DEV_TENANT_ID)},
        )
        assert resp.status_code == 200, f"Second refresh failed: {resp.text}"
        payload2 = decode_access_token(
            resp.json()["access_token"], _SECRET_KEY
        )
        assert "PROFESOR" in payload2.get(JWT_CLAIM_ROLES, []), (
            f"Expected PROFESOR after second refresh, got "
            f"{payload2.get(JWT_CLAIM_ROLES)}"
        )
