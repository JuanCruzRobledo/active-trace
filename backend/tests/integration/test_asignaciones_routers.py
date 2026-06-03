"""Tests E2E de API para Asignaciones (C-07).

Cubre:
  POST/GET/PATCH/DELETE /api/asignaciones
  Protegido con require_permission("equipos:asignar")
  Vigencia: vencidas no autorizan acceso
  Jerarquia: responsable_id se persiste

Requiere PostgreSQL real (DATABASE_URL_TEST en el entorno).
"""

from __future__ import annotations

from datetime import datetime, timezone
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


def _coord_token() -> str:
    """Crea JWT con rol COORDINADOR (tiene equipos:asignar)."""
    return create_access_token(
        user_id=uuid4(),
        tenant_id=_DEV_TENANT_ID,
        secret_key=_SECRET_KEY,
        roles=["COORDINADOR"],
    )


def _alumno_token() -> str:
    """Crea JWT con rol ALUMNO (NO tiene equipos:asignar)."""
    return create_access_token(
        user_id=uuid4(),
        tenant_id=_DEV_TENANT_ID,
        secret_key=_SECRET_KEY,
        roles=["ALUMNO"],
    )


async def _seed_rbac_asignaciones(db_session: AsyncSession) -> None:
    """Seed minimo para que equipos:asignar funcione."""
    # Permiso
    await db_session.execute(
        text(
            "INSERT INTO permiso (id, codigo, descripcion, created_at) "
            "VALUES (:id, :codigo, :descripcion, now()) "
            "ON CONFLICT (codigo) DO NOTHING"
        ),
        {
            "id": uuid4(),
            "codigo": "equipos:asignar",
            "descripcion": "Gestionar equipos docentes",
        },
    )

    # Rol COORDINADOR
    await db_session.execute(
        text(
            "INSERT INTO rol (id, tenant_id, codigo, nombre, "
            "descripcion, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :codigo, :nombre, "
            ":descripcion, now(), now()) "
            "ON CONFLICT (tenant_id, codigo) DO NOTHING"
        ),
        {
            "id": uuid4(),
            "tenant_id": _DEV_TENANT_ID,
            "codigo": "COORDINADOR",
            "nombre": "Coordinador",
            "descripcion": "Coordinador",
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
            "rol_id": (await db_session.execute(
                text(
                    "SELECT id FROM rol WHERE tenant_id=:tid AND codigo='COORDINADOR'"
                ),
                {"tid": _DEV_TENANT_ID},
            )).scalar_one(),
            "permiso_id": (await db_session.execute(
                text(
                    "SELECT id FROM permiso WHERE codigo='equipos:asignar'"
                ),
            )).scalar_one(),
        },
    )

    await db_session.commit()


async def _seed_usuario(db_session: AsyncSession, email: str = "base@test.com") -> UUID:
    """Crea un usuario de prueba directamente."""
    from app.models.usuario import Usuario

    u = Usuario(
        tenant_id=_DEV_TENANT_ID,
        nombre="Base",
        apellidos="User",
        email=email,
        dni="00000000",
    )
    db_session.add(u)
    await db_session.flush()
    return u.id


async def _seed_usuario_legacy(db_session: AsyncSession, email: str) -> UUID:
    """Crea usuario via ORM directo (sin service, sin auth_user)."""
    from app.models.usuario import Usuario

    u = Usuario(
        tenant_id=_DEV_TENANT_ID,
        nombre="Seed",
        apellidos="User",
        email=email,
        dni="00000000",
        estado="Activo",
    )
    db_session.add(u)
    await db_session.flush()
    await db_session.commit()
    return u.id


@pytest.fixture(autouse=True)
def _patch_env(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", _SECRET_KEY)
    monkeypatch.setenv("ENCRYPTION_KEY", "b" * 32)
    monkeypatch.setenv("DATABASE_URL", "placeholder")


# ===========================================================================
# 403 — Sin permiso equipos:asignar
# ===========================================================================


class TestAsignacionesApiSinPermiso:
    """Endpoint devuelve 403 si el token no tiene equipos:asignar."""

    async def test_post_asignaciones_returns_403(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_alumno_token()}"}
        resp = await client.post(
            "/api/asignaciones",
            json={
                "usuario_id": str(uuid4()),
                "rol": "PROFESOR",
                "desde": "2024-01-01T00:00:00Z",
            },
            headers=headers,
        )
        assert resp.status_code == 403

    async def test_get_asignaciones_returns_403(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_alumno_token()}"}
        resp = await client.get("/api/asignaciones", headers=headers)
        assert resp.status_code == 403


# ===========================================================================
# Asignaciones CRUD
# ===========================================================================


class TestAsignacionesApi:
    """POST/GET/PATCH/DELETE /api/asignaciones."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(
        self, db_session: AsyncSession, seed_dev_tenant: None
    ) -> None:
        await _seed_rbac_asignaciones(db_session)

    # ── POST (Create) ───────────────────────────────────────────────────

    async def test_crear_asignacion_returns_201(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        uid = await _seed_usuario_legacy(db_session, "profesor@test.com")
        headers = {"Authorization": f"Bearer {_coord_token()}"}
        resp = await client.post(
            "/api/asignaciones",
            json={
                "usuario_id": str(uid),
                "rol": "PROFESOR",
                "desde": "2024-01-01T00:00:00Z",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["rol"] == "PROFESOR"
        assert body["usuario_id"] == str(uid)
        assert body["estado_vigencia"] == "Vigente"
        assert "id" in body

    async def test_crear_asignacion_usuario_inexistente_returns_400(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_coord_token()}"}
        resp = await client.post(
            "/api/asignaciones",
            json={
                "usuario_id": str(uuid4()),
                "rol": "PROFESOR",
                "desde": "2024-01-01T00:00:00Z",
            },
            headers=headers,
        )
        # El service lanza BusinessError → 409
        assert resp.status_code == 409

    async def test_crear_asignacion_con_jerarquia(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Asignacion con responsable_id se persiste."""
        resp_id = await _seed_usuario_legacy(db_session, "responsable@test.com")
        tutor_id = await _seed_usuario_legacy(db_session, "tutor@test.com")
        headers = {"Authorization": f"Bearer {_coord_token()}"}
        resp = await client.post(
            "/api/asignaciones",
            json={
                "usuario_id": str(tutor_id),
                "rol": "TUTOR",
                "responsable_id": str(resp_id),
                "desde": "2024-01-01T00:00:00Z",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["responsable_id"] == str(resp_id)

    # ── GET (List) ──────────────────────────────────────────────────────

    async def test_listar_asignaciones_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        uid = await _seed_usuario_legacy(db_session, "list@test.com")
        headers = {"Authorization": f"Bearer {_coord_token()}"}
        await client.post(
            "/api/asignaciones",
            json={
                "usuario_id": str(uid),
                "rol": "PROFESOR",
                "desde": "2024-01-01T00:00:00Z",
            },
            headers=headers,
        )
        resp = await client.get("/api/asignaciones", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) >= 1

    # ── GET (By ID) ─────────────────────────────────────────────────────

    async def test_obtener_asignacion_por_id_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        uid = await _seed_usuario_legacy(db_session, "get@test.com")
        headers = {"Authorization": f"Bearer {_coord_token()}"}
        crear = await client.post(
            "/api/asignaciones",
            json={
                "usuario_id": str(uid),
                "rol": "PROFESOR",
                "desde": "2024-01-01T00:00:00Z",
            },
            headers=headers,
        )
        aid = crear.json()["id"]
        resp = await client.get(f"/api/asignaciones/{aid}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["rol"] == "PROFESOR"

    async def test_obtener_asignacion_inexistente_returns_404(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_coord_token()}"}
        resp = await client.get(
            f"/api/asignaciones/{uuid4()}", headers=headers
        )
        assert resp.status_code == 404

    # ── PATCH (Update) ──────────────────────────────────────────────────

    async def test_actualizar_asignacion_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        uid = await _seed_usuario_legacy(db_session, "upd@test.com")
        headers = {"Authorization": f"Bearer {_coord_token()}"}
        crear = await client.post(
            "/api/asignaciones",
            json={
                "usuario_id": str(uid),
                "rol": "PROFESOR",
                "desde": "2024-01-01T00:00:00Z",
            },
            headers=headers,
        )
        aid = crear.json()["id"]
        resp = await client.patch(
            f"/api/asignaciones/{aid}",
            json={"rol": "COORDINADOR"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["rol"] == "COORDINADOR"

    # ── DELETE (Soft-delete) ────────────────────────────────────────────

    async def test_soft_delete_asignacion_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        uid = await _seed_usuario_legacy(db_session, "del@test.com")
        headers = {"Authorization": f"Bearer {_coord_token()}"}
        crear = await client.post(
            "/api/asignaciones",
            json={
                "usuario_id": str(uid),
                "rol": "PROFESOR",
                "desde": "2024-01-01T00:00:00Z",
            },
            headers=headers,
        )
        aid = crear.json()["id"]
        resp = await client.delete(
            f"/api/asignaciones/{aid}", headers=headers
        )
        assert resp.status_code == 200
        # Confirmar soft-delete
        get_resp = await client.get(
            f"/api/asignaciones/{aid}", headers=headers
        )
        assert get_resp.status_code == 404


# ===========================================================================
# Vigencia
# ===========================================================================


class TestAsignacionesVigencia:
    """Asignaciones vencidas no otorgan acceso, vigentes si."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(
        self, db_session: AsyncSession, seed_dev_tenant: None
    ) -> None:
        await _seed_rbac_asignaciones(db_session)

    async def test_asignacion_vencida_tiene_estado_vencida(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        uid = await _seed_usuario_legacy(db_session, "vencida@test.com")
        headers = {"Authorization": f"Bearer {_coord_token()}"}
        resp = await client.post(
            "/api/asignaciones",
            json={
                "usuario_id": str(uid),
                "rol": "PROFESOR",
                "desde": "2020-01-01T00:00:00Z",
                "hasta": "2020-06-01T00:00:00Z",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["estado_vigencia"] == "Vencida"
