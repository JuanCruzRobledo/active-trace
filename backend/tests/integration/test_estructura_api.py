"""Tests E2E de API para estructura académica (C-06).

Cubre endpoints ABM protegidos con require_permission("estructura:gestionar"):
  POST/GET/PATCH /api/admin/carreras
  POST/GET/PATCH /api/admin/materias
  POST/GET/PATCH /api/admin/cohortes

Requiere PostgreSQL real (DATABASE_URL_TEST en el entorno).
"""

from __future__ import annotations

from datetime import date
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
    """Crea JWT con rol ADMIN (tiene estructura:gestionar)."""
    return create_access_token(
        user_id=uuid4(),
        tenant_id=_DEV_TENANT_ID,
        secret_key=_SECRET_KEY,
        roles=["ADMIN"],
    )


def _alumno_token() -> str:
    """Crea JWT con rol ALUMNO (NO tiene estructura:gestionar)."""
    return create_access_token(
        user_id=uuid4(),
        tenant_id=_DEV_TENANT_ID,
        secret_key=_SECRET_KEY,
        roles=["ALUMNO"],
    )


async def _seed_rbac_base(db_session: AsyncSession) -> None:
    """Seed minimo para que estructura:gestionar funcione.

    Inserta permiso, rol ADMIN y la relacion rol_permiso para
    el tenant de desarrollo (0000...001).
    """
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
            "codigo": "estructura:gestionar",
            "descripcion": "Gestionar estructura academica",
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
# 403 — Sin permiso estructura:gestionar
# ===========================================================================


class TestEstructuraApiSinPermiso:
    """Endpoint devuelve 403 si el token no tiene estructura:gestionar."""

    async def test_post_carreras_returns_403(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_alumno_token()}"}
        resp = await client.post(
            "/api/admin/carreras",
            json={"codigo": "LIC", "nombre": "Licenciatura"},
            headers=headers,
        )
        assert resp.status_code == 403

    async def test_post_materias_returns_403(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_alumno_token()}"}
        resp = await client.post(
            "/api/admin/materias",
            json={"codigo": "M01", "nombre": "Matematicas"},
            headers=headers,
        )
        assert resp.status_code == 403

    async def test_post_cohortes_returns_403(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_alumno_token()}"}
        resp = await client.post(
            "/api/admin/cohortes",
            json={
                "carrera_id": "a" * 36, "nombre": "2024A",
                "anio": 2024, "vig_desde": "2024-03-01",
            },
            headers=headers,
        )
        assert resp.status_code == 403

    async def test_get_carreras_returns_403(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_alumno_token()}"}
        resp = await client.get("/api/admin/carreras", headers=headers)
        assert resp.status_code == 403


# ===========================================================================
# Carreras CRUD
# ===========================================================================


class TestCarrerasApi:
    """POST/GET/PATCH /api/admin/carreras."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(
        self, db_session: AsyncSession, seed_dev_tenant: None
    ) -> None:
        await _seed_rbac_base(db_session)

    async def test_crear_carrera_returns_201(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_admin_token()}"}
        resp = await client.post(
            "/api/admin/carreras",
            json={"codigo": "LIC", "nombre": "Licenciatura en Sistemas"},
            headers=headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["codigo"] == "LIC"
        assert body["nombre"] == "Licenciatura en Sistemas"
        assert body["estado"] == "Activa"
        assert "id" in body
        assert "tenant_id" in body

    async def test_crear_carrera_duplicada_returns_409(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_admin_token()}"}
        await client.post(
            "/api/admin/carreras",
            json={"codigo": "MED", "nombre": "Medicina"},
            headers=headers,
        )
        resp = await client.post(
            "/api/admin/carreras",
            json={"codigo": "MED", "nombre": "Medicina Dup"},
            headers=headers,
        )
        assert resp.status_code == 409

    async def test_listar_carreras_returns_200(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_admin_token()}"}
        await client.post(
            "/api/admin/carreras",
            json={"codigo": "A", "nombre": "Alpha"},
            headers=headers,
        )
        await client.post(
            "/api/admin/carreras",
            json={"codigo": "B", "nombre": "Beta"},
            headers=headers,
        )

        resp = await client.get("/api/admin/carreras", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) >= 2

    async def test_obtener_carrera_por_id_returns_200(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_admin_token()}"}
        crear = await client.post(
            "/api/admin/carreras",
            json={"codigo": "ING", "nombre": "Ingenieria"},
            headers=headers,
        )
        cid = crear.json()["id"]

        resp = await client.get(
            f"/api/admin/carreras/{cid}",
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["codigo"] == "ING"

    async def test_obtener_carrera_inexistente_returns_404(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_admin_token()}"}
        resp = await client.get(
            f"/api/admin/carreras/{uuid4()}",
            headers=headers,
        )
        assert resp.status_code == 404

    async def test_actualizar_carrera_returns_200(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_admin_token()}"}
        crear = await client.post(
            "/api/admin/carreras",
            json={"codigo": "ARQ", "nombre": "Arquitectura"},
            headers=headers,
        )
        cid = crear.json()["id"]

        resp = await client.patch(
            f"/api/admin/carreras/{cid}",
            json={"nombre": "Arquitectura y Urbanismo"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["nombre"] == "Arquitectura y Urbanismo"

    async def test_actualizar_carrera_inexistente_returns_404(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_admin_token()}"}
        resp = await client.patch(
            f"/api/admin/carreras/{uuid4()}",
            json={"nombre": "X"},
            headers=headers,
        )
        assert resp.status_code == 404

    async def test_crear_carrera_con_datos_invalidos_returns_422(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_admin_token()}"}
        resp = await client.post(
            "/api/admin/carreras",
            json={"codigo": "", "nombre": "X"},
            headers=headers,
        )
        assert resp.status_code == 422


# ===========================================================================
# Materias CRUD
# ===========================================================================


class TestMateriasApi:
    """POST/GET/PATCH /api/admin/materias."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(
        self, db_session: AsyncSession, seed_dev_tenant: None
    ) -> None:
        await _seed_rbac_base(db_session)

    async def test_crear_materia_returns_201(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_admin_token()}"}
        resp = await client.post(
            "/api/admin/materias",
            json={"codigo": "M01", "nombre": "Matematicas I"},
            headers=headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["codigo"] == "M01"
        assert body["nombre"] == "Matematicas I"

    async def test_crear_materia_duplicada_returns_409(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_admin_token()}"}
        await client.post(
            "/api/admin/materias",
            json={"codigo": "M01", "nombre": "Matematicas"},
            headers=headers,
        )
        resp = await client.post(
            "/api/admin/materias",
            json={"codigo": "M01", "nombre": "Matematicas Dup"},
            headers=headers,
        )
        assert resp.status_code == 409

    async def test_listar_materias_returns_200(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_admin_token()}"}
        await client.post(
            "/api/admin/materias",
            json={"codigo": "M01", "nombre": "Matematicas"},
            headers=headers,
        )
        resp = await client.get("/api/admin/materias", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_actualizar_materia_returns_200(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_admin_token()}"}
        crear = await client.post(
            "/api/admin/materias",
            json={"codigo": "M01", "nombre": "Matematicas"},
            headers=headers,
        )
        mid = crear.json()["id"]

        resp = await client.patch(
            f"/api/admin/materias/{mid}",
            json={"nombre": "Matematicas Avanzadas"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["nombre"] == "Matematicas Avanzadas"


# ===========================================================================
# Cohortes CRUD
# ===========================================================================


class TestCohortesApi:
    """POST/GET/PATCH /api/admin/cohortes."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(
        self, db_session: AsyncSession, seed_dev_tenant: None
    ) -> None:
        await _seed_rbac_base(db_session)

    async def test_crear_cohorte_returns_201(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_admin_token()}"}

        # Crear carrera primero
        carrera_resp = await client.post(
            "/api/admin/carreras",
            json={"codigo": "LIC", "nombre": "Licenciatura"},
            headers=headers,
        )
        carrera_id = carrera_resp.json()["id"]

        resp = await client.post(
            "/api/admin/cohortes",
            json={
                "carrera_id": carrera_id,
                "nombre": "2024A",
                "anio": 2024,
                "vig_desde": "2024-03-01",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["nombre"] == "2024A"
        assert body["anio"] == 2024

    async def test_crear_cohorte_carrera_inactiva_returns_409(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_admin_token()}"}

        carrera_resp = await client.post(
            "/api/admin/carreras",
            json={"codigo": "LIC", "nombre": "Lic.", "estado": "Inactiva"},
            headers=headers,
        )
        carrera_id = carrera_resp.json()["id"]

        resp = await client.post(
            "/api/admin/cohortes",
            json={
                "carrera_id": carrera_id,
                "nombre": "2024A", "anio": 2024,
                "vig_desde": "2024-03-01",
            },
            headers=headers,
        )
        assert resp.status_code == 409

    async def test_crear_cohorte_carrera_inexistente_returns_409(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_admin_token()}"}
        resp = await client.post(
            "/api/admin/cohortes",
            json={
                "carrera_id": str(uuid4()),
                "nombre": "2024A", "anio": 2024,
                "vig_desde": "2024-03-01",
            },
            headers=headers,
        )
        assert resp.status_code in (404, 409)

    async def test_listar_cohortes_returns_200(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_admin_token()}"}

        carrera_resp = await client.post(
            "/api/admin/carreras",
            json={"codigo": "LIC", "nombre": "Licenciatura"},
            headers=headers,
        )
        carrera_id = carrera_resp.json()["id"]

        await client.post(
            "/api/admin/cohortes",
            json={
                "carrera_id": carrera_id,
                "nombre": "2024A", "anio": 2024,
                "vig_desde": "2024-03-01",
            },
            headers=headers,
        )

        resp = await client.get("/api/admin/cohortes", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_actualizar_cohorte_returns_200(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_admin_token()}"}

        carrera_resp = await client.post(
            "/api/admin/carreras",
            json={"codigo": "LIC", "nombre": "Licenciatura"},
            headers=headers,
        )
        carrera_id = carrera_resp.json()["id"]

        crear = await client.post(
            "/api/admin/cohortes",
            json={
                "carrera_id": carrera_id,
                "nombre": "2024A", "anio": 2024,
                "vig_desde": "2024-03-01",
            },
            headers=headers,
        )
        coh_id = crear.json()["id"]

        resp = await client.patch(
            f"/api/admin/cohortes/{coh_id}",
            json={"estado": "Inactiva"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["estado"] == "Inactiva"

    async def test_crear_cohorte_datos_invalidos_returns_422(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_admin_token()}"}
        resp = await client.post(
            "/api/admin/cohortes",
            json={
                "carrera_id": "short",
                "nombre": "2024A", "anio": 2024,
                "vig_desde": "2024-03-01",
            },
            headers=headers,
        )
        assert resp.status_code == 422
