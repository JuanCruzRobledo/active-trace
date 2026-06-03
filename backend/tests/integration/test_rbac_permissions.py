"""Integration tests for C-04 RBAC Permisos Finos.

Requires PostgreSQL real (DATABASE_URL_TEST in env).
Tests the require_permission dependency, PermissionService,
tenant isolation, and GET /me extension.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from fastapi import APIRouter, Depends
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.dependencies import require_permission
from app.core.security import create_access_token
from tests.conftest import db_available

pytestmark = [
    pytest.mark.skipif(
        not db_available(),
        reason="Requiere PostgreSQL: definir DATABASE_URL_TEST en el entorno",
    ),
]

_DEV_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")
_SECRET_KEY = "a" * 64

# ── Test endpoint ──────────────────────────────────────────────────────

_test_router = APIRouter()


@_test_router.get("/test/protected")
async def _test_protected(
    _: bool = Depends(require_permission("calificaciones:importar")),
):
    return {"status": "ok"}


@_test_router.get("/test/protected-avisos")
async def _test_protected_avisos(
    _: bool = Depends(require_permission("avisos:publicar")),
):
    return {"status": "ok"}


# ── Seed helpers ───────────────────────────────────────────────────────


async def _seed_rbac_data(db_session: AsyncSession) -> dict[str, UUID]:
    """Insert seed data: permisos, roles and matrix for dev tenant.
    Returns dict of {codigo: UUID} for roles and permisos.
    """
    permisos = [
        ("ver_estado_academico", "Ver estado academico propio"),
        ("reservar_evaluacion", "Reservar instancia de evaluacion"),
        ("confirmar_avisos", "Confirmar avisos (acknowledgment)"),
        ("calificaciones:importar", "Importar calificaciones"),
        ("atrasados:ver", "Ver alumnos atrasados"),
        ("entregas_sin_corregir", "Detectar entregas sin corregir"),
        ("comunicacion:enviar", "Enviar comunicaciones a alumnos"),
        ("comunicacion:aprobar", "Aprobar comunicaciones masivas"),
        ("encuentros:gestionar", "Gestionar encuentros"),
        ("guardias:registrar", "Registrar guardias"),
        ("tareas:gestionar", "Gestionar tareas internas"),
        ("avisos:publicar", "Publicar avisos"),
        ("equipos:asignar", "Gestionar equipos docentes"),
        ("estructura:gestionar", "Gestionar estructura academica"),
        ("usuarios:gestionar", "Gestionar usuarios del tenant"),
        ("auditoria:ver", "Ver auditoria"),
        ("impersonacion:usar", "Usar impersonalizacion"),
        ("grilla_salarial:operar", "Operar grilla salarial"),
        ("liquidaciones:calcular", "Calcular liquidaciones"),
        ("liquidaciones:cerrar", "Cerrar liquidaciones"),
        ("liquidaciones:exportar", "Exportar liquidaciones"),
        ("liquidaciones:ver", "Ver liquidaciones"),
        ("facturas:gestionar", "Gestionar facturas"),
        ("tenant:configurar", "Configurar el tenant"),
    ]
    permiso_ids: dict[str, UUID] = {}
    for codigo, descripcion in permisos:
        pid = uuid4()
        await db_session.execute(
            text(
                "INSERT INTO permiso (id, codigo, descripcion, created_at) "
                "VALUES (:id, :codigo, :descripcion, now())"
            ),
            {"id": pid, "codigo": codigo, "descripcion": descripcion},
        )
        permiso_ids[codigo] = pid

    roles_data = [
        ("ALUMNO", "Alumno", "Estudiante"),
        ("TUTOR", "Tutor", "Auxiliar"),
        ("PROFESOR", "Profesor", "Docente"),
        ("COORDINADOR", "Coordinador", "Responsable"),
        ("NEXO", "Nexo", "Articulacion"),
        ("ADMIN", "Administrador", "Admin"),
        ("FINANZAS", "Finanzas", "Liquidaciones"),
    ]
    rol_ids: dict[str, UUID] = {}
    for codigo, nombre, descripcion in roles_data:
        rid = uuid4()
        await db_session.execute(
            text(
                "INSERT INTO rol (id, tenant_id, codigo, nombre, "
                "descripcion, created_at, updated_at) "
                "VALUES (:id, :tenant_id, :codigo, :nombre, "
                ":descripcion, now(), now())"
            ),
            {
                "id": rid,
                "tenant_id": _DEV_TENANT_ID,
                "codigo": codigo,
                "nombre": nombre,
                "descripcion": descripcion,
            },
        )
        rol_ids[codigo] = rid

    # Matrix seed
    matrix = {
        "ALUMNO": ["ver_estado_academico", "reservar_evaluacion", "confirmar_avisos"],
        "TUTOR": [
            "confirmar_avisos", "atrasados:ver", "entregas_sin_corregir",
            "encuentros:gestionar", "guardias:registrar",
        ],
        "PROFESOR": [
            "confirmar_avisos", "calificaciones:importar", "atrasados:ver",
            "entregas_sin_corregir", "comunicacion:enviar",
            "encuentros:gestionar", "guardias:registrar", "tareas:gestionar",
        ],
        "COORDINADOR": [
            "confirmar_avisos", "calificaciones:importar", "atrasados:ver",
            "entregas_sin_corregir", "comunicacion:enviar", "comunicacion:aprobar",
            "encuentros:gestionar", "guardias:registrar", "tareas:gestionar",
            "avisos:publicar", "equipos:asignar", "auditoria:ver",
        ],
        "NEXO": [
            "confirmar_avisos", "calificaciones:importar", "atrasados:ver",
            "entregas_sin_corregir", "comunicacion:enviar", "comunicacion:aprobar",
            "encuentros:gestionar", "guardias:registrar", "tareas:gestionar",
            "avisos:publicar", "equipos:asignar", "auditoria:ver",
        ],
        "ADMIN": [
            "ver_estado_academico", "confirmar_avisos", "calificaciones:importar",
            "atrasados:ver", "entregas_sin_corregir", "comunicacion:enviar",
            "comunicacion:aprobar", "encuentros:gestionar", "guardias:registrar",
            "tareas:gestionar", "avisos:publicar", "equipos:asignar",
            "estructura:gestionar", "usuarios:gestionar", "auditoria:ver",
            "impersonacion:usar", "tenant:configurar",
        ],
        "FINANZAS": [
            "confirmar_avisos", "auditoria:ver",
            "grilla_salarial:operar", "liquidaciones:calcular",
            "liquidaciones:cerrar", "liquidaciones:exportar",
            "liquidaciones:ver", "facturas:gestionar",
        ],
    }

    for rol_codigo, perm_codigos in matrix.items():
        for perm_codigo in perm_codigos:
            await db_session.execute(
                text(
                    "INSERT INTO rol_permiso (id, tenant_id, rol_id, "
                    "permiso_id, created_at) "
                    "VALUES (:id, :tenant_id, :rol_id, :permiso_id, now())"
                ),
                {
                    "id": uuid4(),
                    "tenant_id": _DEV_TENANT_ID,
                    "rol_id": rol_ids[rol_codigo],
                    "permiso_id": permiso_ids[perm_codigo],
                },
            )

    await db_session.commit()
    return {"roles": rol_ids, "permisos": permiso_ids}


def _make_token(
    roles: list[str],
    user_id: UUID | None = None,
    tenant_id: UUID = _DEV_TENANT_ID,
) -> str:
    return create_access_token(
        user_id=user_id or uuid4(),
        tenant_id=tenant_id,
        secret_key=_SECRET_KEY,
        roles=roles,
    )


# ── Fixtures ───────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _patch_env(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", _SECRET_KEY)
    monkeypatch.setenv("ENCRYPTION_KEY", "b" * 32)
    monkeypatch.setenv("DATABASE_URL", "placeholder")


@pytest_asyncio.fixture
async def seed_rbac(db_session) -> dict[str, UUID]:
    """Seed roles + permissions + matrix for dev tenant."""
    return await _seed_rbac_data(db_session)


@pytest_asyncio.fixture
async def rbac_client(
    settings, db_engine, seed_dev_tenant, seed_rbac
) -> AsyncClient:
    """Client with test router for protected endpoints."""
    from app.main import create_app

    application = create_app(settings)
    application.include_router(_test_router)
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ═══════════════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════════════


class TestRequirePermission:
    """require_permission dependency — integration tests."""

    async def test_valid_permission_passes(
        self, rbac_client: AsyncClient
    ):
        token = _make_token(roles=["PROFESOR"])
        resp = await rbac_client.get(
            "/test/protected",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    async def test_without_permission_returns_403(
        self, rbac_client: AsyncClient
    ):
        token = _make_token(roles=["ALUMNO"])
        resp = await rbac_client.get(
            "/test/protected",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Permission denied"

    async def test_without_auth_returns_401(
        self, rbac_client: AsyncClient
    ):
        resp = await rbac_client.get("/test/protected")
        assert resp.status_code == 401

    async def test_profesor_cannot_access_coordinador_permission(
        self, rbac_client: AsyncClient
    ):
        token = _make_token(roles=["PROFESOR"])
        resp = await rbac_client.get(
            "/test/protected-avisos",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_coordinador_can_access_avisos(
        self, rbac_client: AsyncClient
    ):
        token = _make_token(roles=["COORDINADOR"])
        resp = await rbac_client.get(
            "/test/protected-avisos",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    async def test_empty_roles_returns_403(
        self, rbac_client: AsyncClient
    ):
        token = _make_token(roles=[])
        resp = await rbac_client.get(
            "/test/protected",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


class TestMeEndpoint:
    """GET /api/auth/me includes permisos field."""

    async def test_me_includes_permisos(
        self, rbac_client: AsyncClient, db_session: AsyncSession
    ):
        from app.repositories.user_repository import UserRepository
        from app.core.security import hash_password

        # Create a test user
        repo = UserRepository(session=db_session, tenant_id=_DEV_TENANT_ID)
        user = await repo.create(
            email="test@profesor.com",
            password_hash=hash_password("TestPass1234!"),
            is_active=True,
        )
        await db_session.commit()

        token = _make_token(
            roles=["PROFESOR"],
            user_id=user.id,
        )
        resp = await rbac_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "permisos" in body
        assert isinstance(body["permisos"], list)
        assert "calificaciones:importar" in body["permisos"]
        assert "atrasados:ver" in body["permisos"]
        assert "comunicacion:enviar" in body["permisos"]


class TestTenantIsolation:
    """Roles and permissions MUST be scoped by tenant."""

    async def test_tenant_b_cannot_see_tenant_a_roles(
        self, settings, db_engine, db_session: AsyncSession
    ) -> None:
        from app.main import create_app
        from app.models.tenant import Tenant

        # Create tenant A with a custom role
        tid_a = uuid4()
        tenant_a = Tenant(id=tid_a, tenant_id=tid_a, nombre="TenantA")
        db_session.add(tenant_a)
        await db_session.flush()

        rid_a = uuid4()
        await db_session.execute(
            text(
                "INSERT INTO rol (id, tenant_id, codigo, nombre, "
                "descripcion, created_at, updated_at) "
                "VALUES (:id, :tenant_id, :codigo, :nombre, "
                ":descripcion, now(), now())"
            ),
            {
                "id": rid_a,
                "tenant_id": tid_a,
                "codigo": "CUSTOM",
                "nombre": "Custom Role",
                "descripcion": None,
            },
        )

        # Create tenant B (NO custom role)
        tid_b = uuid4()
        tenant_b = Tenant(id=tid_b, tenant_id=tid_b, nombre="TenantB")
        db_session.add(tenant_b)
        await db_session.flush()
        await db_session.commit()

        # User from tenant B with CUSTOM role should fail permission check
        token_b = _make_token(
            roles=["CUSTOM"],
            tenant_id=tid_b,
        )

        app = create_app(settings)
        app.include_router(_test_router)
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            # The role CUSTOM doesn't exist in tenant B, so
            # PermissionService returns empty set → 403
            resp = await client.get(
                "/test/protected",
                headers={"Authorization": f"Bearer {token_b}"},
            )
            assert resp.status_code == 403

    async def test_tenant_b_has_no_permissions_from_tenant_a(
        self, settings, db_engine, db_session: AsyncSession
    ) -> None:
        """User in tenant B with role "ALUMNO" but tenant B has no
        roles seeded → should get empty permissions."""
        from app.main import create_app
        from app.models.tenant import Tenant

        tid_b = uuid4()
        tenant_b = Tenant(id=tid_b, tenant_id=tid_b, nombre="TenantB")
        db_session.add(tenant_b)
        await db_session.commit()

        token_b = _make_token(
            roles=["ALUMNO"],
            tenant_id=tid_b,
        )

        app = create_app(settings)
        app.include_router(_test_router)
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            # Tenant B has no roles seeded → PermissionService
            # returns empty set → 403
            resp = await client.get(
                "/test/protected",
                headers={"Authorization": f"Bearer {token_b}"},
            )
            assert resp.status_code == 403


