"""Tests E2E de API para Usuarios (C-07).

Cubre:
  POST/GET/PATCH/DELETE /api/admin/usuarios
  Protegido con require_permission("admin:gestionar-usuarios")
  PII enmascarada en respuestas

Requiere PostgreSQL real (DATABASE_URL_TEST en el entorno).
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

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


# ── Helpers ────────────────────────────────────────────────────────────


def _admin_token() -> str:
    """Crea JWT con rol ADMIN (tiene admin:gestionar-usuarios)."""
    return create_access_token(
        user_id=uuid4(),
        tenant_id=_DEV_TENANT_ID,
        secret_key=_SECRET_KEY,
        roles=["ADMIN"],
    )


def _alumno_token() -> str:
    """Crea JWT con rol ALUMNO (NO tiene admin:gestionar-usuarios)."""
    return create_access_token(
        user_id=uuid4(),
        tenant_id=_DEV_TENANT_ID,
        secret_key=_SECRET_KEY,
        roles=["ALUMNO"],
    )


async def _seed_rbac_usuarios(db_session: AsyncSession) -> None:
    """Seed minimo para que admin:gestionar-usuarios funcione."""
    # Permiso
    perm_id = uuid4()
    await db_session.execute(
        text(
            "INSERT INTO permiso (id, codigo, descripcion, created_at) "
            "VALUES (:id, :codigo, :descripcion, now()) "
            "ON CONFLICT (codigo) DO NOTHING"
        ),
        {
            "id": perm_id,
            "codigo": "admin:gestionar-usuarios",
            "descripcion": "Gestionar usuarios del sistema",
        },
    )

    # Rol ADMIN
    rol_id = uuid4()
    await db_session.execute(
        text(
            "INSERT INTO rol (id, tenant_id, codigo, nombre, "
            "descripcion, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :codigo, :nombre, "
            ":descripcion, now(), now()) "
            "ON CONFLICT (tenant_id, codigo) DO NOTHING"
        ),
        {
            "id": rol_id,
            "tenant_id": _DEV_TENANT_ID,
            "codigo": "ADMIN",
            "nombre": "Administrador",
            "descripcion": "Admin",
        },
    )

    # Vincular
    await db_session.execute(
        text(
            "INSERT INTO rol_permiso (id, tenant_id, rol_id, permiso_id, created_at) "
            "VALUES (:id, :tenant_id, :rol_id, :permiso_id, now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {
            "id": uuid4(),
            "tenant_id": _DEV_TENANT_ID,
            "rol_id": rol_id,
            "permiso_id": perm_id,
        },
    )

    await db_session.commit()


@pytest.fixture(autouse=True)
def _patch_env(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", _SECRET_KEY)
    monkeypatch.setenv("ENCRYPTION_KEY", "b" * 32)
    monkeypatch.setenv("DATABASE_URL", "placeholder")


# ===========================================================================
# 403 — Sin permiso admin:gestionar-usuarios
# ===========================================================================


class TestUsuariosApiSinPermiso:
    """Endpoint devuelve 403 si el token no tiene admin:gestionar-usuarios."""

    async def test_post_usuarios_returns_403(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_alumno_token()}"}
        resp = await client.post(
            "/api/admin/usuarios",
            json={"nombre": "Juan", "apellidos": "Perez", "email": "juan@example.com"},
            headers=headers,
        )
        assert resp.status_code == 403

    async def test_get_usuarios_returns_403(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_alumno_token()}"}
        resp = await client.get("/api/admin/usuarios", headers=headers)
        assert resp.status_code == 403


# ===========================================================================
# Usuarios CRUD
# ===========================================================================


class TestUsuariosApi:
    """POST/GET/PATCH/DELETE /api/admin/usuarios."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(
        self, db_session: AsyncSession, seed_dev_tenant: None
    ) -> None:
        await _seed_rbac_usuarios(db_session)

    # ── POST (Create) ───────────────────────────────────────────────────

    async def test_crear_usuario_returns_201(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_admin_token()}"}
        resp = await client.post(
            "/api/admin/usuarios",
            json={
                "nombre": "Juan",
                "apellidos": "Perez",
                "email": "juan.perez@example.com",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["nombre"] == "Juan"
        assert body["apellidos"] == "Perez"
        assert "id" in body
        assert "tenant_id" in body

    async def test_crear_usuario_pii_mask(self, client: AsyncClient) -> None:
        """PII debe venir enmascarada en la respuesta."""
        headers = {"Authorization": f"Bearer {_admin_token()}"}
        resp = await client.post(
            "/api/admin/usuarios",
            json={
                "nombre": "Maria",
                "apellidos": "Gonzalez",
                "email": "maria.gonzalez@example.com",
                "dni": "12345678",
                "cuil": "20-12345678-9",
                "cbu": "0000003100012345678901",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        # PII debe estar enmascarada
        assert body["email"] == "m***@example.com"
        assert body["dni"] == "*****5678"
        assert body["cuil"] == "*****5678-9"
        assert body["cbu"] == "*****8901"

    async def test_crear_usuario_email_duplicado_returns_409(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_admin_token()}"}
        payload = {
            "nombre": "Dupe",
            "apellidos": "Test",
            "email": "dupe@example.com",
        }
        await client.post("/api/admin/usuarios", json=payload, headers=headers)
        resp = await client.post(
            "/api/admin/usuarios", json=payload, headers=headers
        )
        assert resp.status_code == 409

    async def test_crear_usuario_datos_invalidos_returns_422(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_admin_token()}"}
        resp = await client.post(
            "/api/admin/usuarios",
            json={"nombre": "", "apellidos": "", "email": "invalido"},
            headers=headers,
        )
        assert resp.status_code == 422

    # ── GET (List) ──────────────────────────────────────────────────────

    async def test_listar_usuarios_returns_200(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_admin_token()}"}
        await client.post(
            "/api/admin/usuarios",
            json={"nombre": "A", "apellidos": "B", "email": "a@example.com"},
            headers=headers,
        )
        resp = await client.get("/api/admin/usuarios", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, dict)  # paginated response
        assert "items" in body
        assert "total" in body
        assert "page" in body
        assert "page_size" in body
        assert body["total"] >= 1
        assert len(body["items"]) >= 1

    async def test_listar_usuarios_paginacion(
        self, client: AsyncClient
    ) -> None:
        """Pagina correctamente con page y page_size."""
        headers = {"Authorization": f"Bearer {_admin_token()}"}
        # Crear 3 usuarios
        for i in range(3):
            await client.post(
                "/api/admin/usuarios",
                json={
                    "nombre": f"User{i}",
                    "apellidos": "Pagination",
                    "email": f"pag{i}@example.com",
                },
                headers=headers,
            )
        # Pagina 1 con size=2
        resp = await client.get(
            "/api/admin/usuarios?page=1&page_size=2", headers=headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 3
        assert len(body["items"]) == 2
        assert body["page"] == 1
        assert body["page_size"] == 2

    async def test_listar_usuarios_con_filtro_estado(
        self, client: AsyncClient
    ) -> None:
        """Filtra por estado."""
        headers = {"Authorization": f"Bearer {_admin_token()}"}
        await client.post(
            "/api/admin/usuarios",
            json={
                "nombre": "Activo",
                "apellidos": "User",
                "email": "activo@example.com",
            },
            headers=headers,
        )
        resp = await client.get(
            "/api/admin/usuarios?estado=Activo", headers=headers
        )
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    # ── GET (By ID) ─────────────────────────────────────────────────────

    async def test_obtener_usuario_por_id_returns_200(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_admin_token()}"}
        crear = await client.post(
            "/api/admin/usuarios",
            json={
                "nombre": "Target",
                "apellidos": "User",
                "email": "target@example.com",
            },
            headers=headers,
        )
        uid = crear.json()["id"]

        resp = await client.get(
            f"/api/admin/usuarios/{uid}", headers=headers
        )
        assert resp.status_code == 200
        assert resp.json()["nombre"] == "Target"

    async def test_obtener_usuario_inexistente_returns_404(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_admin_token()}"}
        resp = await client.get(
            f"/api/admin/usuarios/{uuid4()}", headers=headers
        )
        assert resp.status_code == 404

    # ── PATCH (Update) ──────────────────────────────────────────────────

    async def test_actualizar_usuario_returns_200(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_admin_token()}"}
        crear = await client.post(
            "/api/admin/usuarios",
            json={
                "nombre": "Original",
                "apellidos": "Name",
                "email": "update@example.com",
            },
            headers=headers,
        )
        uid = crear.json()["id"]

        resp = await client.patch(
            f"/api/admin/usuarios/{uid}",
            json={"nombre": "Modificado"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["nombre"] == "Modificado"

    async def test_actualizar_usuario_inexistente_returns_404(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_admin_token()}"}
        resp = await client.patch(
            f"/api/admin/usuarios/{uuid4()}",
            json={"nombre": "X"},
            headers=headers,
        )
        assert resp.status_code == 404

    # ── DELETE (Soft-delete) ────────────────────────────────────────────

    async def test_soft_delete_usuario_returns_200(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_admin_token()}"}
        crear = await client.post(
            "/api/admin/usuarios",
            json={
                "nombre": "Delete",
                "apellidos": "Me",
                "email": "delete-sd@example.com",
            },
            headers=headers,
        )
        uid = crear.json()["id"]

        resp = await client.delete(
            f"/api/admin/usuarios/{uid}", headers=headers
        )
        assert resp.status_code == 200

        # Soft-deleteado: debe retornar con estado Inactivo (no 404)
        get_resp = await client.get(
            f"/api/admin/usuarios/{uid}", headers=headers
        )
        assert get_resp.status_code == 200
        assert get_resp.json()["estado"] == "Inactivo"

    async def test_soft_delete_ya_no_aparece_en_listado(
        self, client: AsyncClient
    ) -> None:
        """Soft-deleteado no aparece en listado por defecto."""
        headers = {"Authorization": f"Bearer {_admin_token()}"}
        crear = await client.post(
            "/api/admin/usuarios",
            json={
                "nombre": "Hidden",
                "apellidos": "User",
                "email": "hidden-sd@example.com",
            },
            headers=headers,
        )
        uid = crear.json()["id"]
        await client.delete(f"/api/admin/usuarios/{uid}", headers=headers)

        # Listar no incluye soft-deleteados
        resp = await client.get("/api/admin/usuarios", headers=headers)
        ids = [u["id"] for u in resp.json()["items"]]
        assert str(uid) not in ids
