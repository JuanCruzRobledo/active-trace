"""Tests E2E de API para Comunicaciones (C-12).

Cubre:
  POST /api/comunicaciones/preview — preview de contenido
  POST /api/comunicaciones/enviar — envio masivo
  POST /api/comunicaciones/enviar-individual — envio individual
  GET /api/comunicaciones/{lote_id} — estado del lote
  PUT /api/comunicaciones/{lote_id}/aprobar — aprobar lote
  POST /api/comunicaciones/{id}/cancelar — cancelar comunicacion
  GET /api/comunicaciones/mis-envios — listado personal

Protegido con require_permission("comunicacion:enviar").
Requiere PostgreSQL real (DATABASE_URL_TEST en el entorno).
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
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


def _admin_token(user_id: UUID | None = None) -> str:
    return create_access_token(
        user_id=user_id or uuid4(),
        tenant_id=_DEV_TENANT_ID,
        secret_key=_SECRET_KEY,
        roles=["ADMIN"],
    )


def _profesor_token(user_id: UUID | None = None) -> str:
    return create_access_token(
        user_id=user_id or uuid4(),
        tenant_id=_DEV_TENANT_ID,
        secret_key=_SECRET_KEY,
        roles=["PROFESOR"],
    )


async def _seed_rbac_comunicacion(db_session: AsyncSession) -> None:
    """Seed minimo para que comunicacion:enviar y comunicacion:aprobar funcionen."""
    from sqlalchemy import text

    for permiso in ("comunicacion:enviar", "comunicacion:aprobar"):
        await db_session.execute(
            text(
                "INSERT INTO permiso (id, codigo, descripcion, created_at) "
                "VALUES (:id, :codigo, :descripcion, now()) "
                "ON CONFLICT (codigo) DO NOTHING"
            ),
            {"id": uuid4(), "codigo": permiso, "descripcion": permiso},
        )

    for rol in ("ADMIN", "PROFESOR"):
        await db_session.execute(
            text(
                "INSERT INTO rol (id, tenant_id, codigo, nombre, "
                "descripcion, created_at, updated_at) "
                "VALUES (:id, :tid, :codigo, :codigo, "
                ":desc, now(), now()) "
                "ON CONFLICT (tenant_id, codigo) DO NOTHING"
            ),
            {"id": uuid4(), "tid": _DEV_TENANT_ID, "codigo": rol, "desc": None},
        )

    for permiso in ("comunicacion:enviar", "comunicacion:aprobar"):
        p_row = (
            await db_session.execute(
                text("SELECT id FROM permiso WHERE codigo = :c"),
                {"c": permiso},
            )
        ).mappings().first()
        for rol in ("ADMIN", "PROFESOR"):
            r_row = (
                await db_session.execute(
                    text(
                        "SELECT id FROM rol "
                        "WHERE codigo = :c AND tenant_id = :tid"
                    ),
                    {"c": rol, "tid": _DEV_TENANT_ID},
                )
            ).mappings().first()
            if p_row and r_row:
                await db_session.execute(
                    text(
                        "INSERT INTO rol_permiso (id, tenant_id, rol_id, permiso_id, created_at) "
                        "VALUES (:id, :tid, :rid, :pid, now()) "
                        "ON CONFLICT DO NOTHING"
                    ),
                    {
                        "id": uuid4(),
                        "tid": _DEV_TENANT_ID,
                        "rid": r_row["id"],
                        "pid": p_row["id"],
                    },
                )

    await db_session.commit()


async def _seed_dev_tenant(db_session: AsyncSession) -> None:
    from app.models.tenant import Tenant

    exists = await db_session.get(Tenant, _DEV_TENANT_ID)
    if exists is None:
        db_session.add(
            Tenant(
                id=_DEV_TENANT_ID,
                tenant_id=_DEV_TENANT_ID,
                nombre="Dev Tenant",
            )
        )
        await db_session.commit()


async def _seed_materia_test(db_session: AsyncSession) -> UUID:
    from app.models.materia import Materia

    mid = uuid4()
    db_session.add(
        Materia(id=mid, tenant_id=_DEV_TENANT_ID, codigo="MAT-COMM", nombre="Comunicaciones Test")
    )
    await db_session.commit()
    return mid


# ── Fixtures ────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def seed_db(db_session: AsyncSession) -> dict:
    """Seed tenant + RBAC + devuelve admin y profesor con sus tokens."""
    await _seed_dev_tenant(db_session)
    await _seed_rbac_comunicacion(db_session)

    from app.models.usuario import Usuario

    admin_id = uuid4()
    profe_id = uuid4()
    db_session.add(Usuario(id=admin_id, tenant_id=_DEV_TENANT_ID, email="admin@test.com", nombre="Admin", apellidos="Test", estado="Activo"))
    db_session.add(Usuario(id=profe_id, tenant_id=_DEV_TENANT_ID, email="profesor@test.com", nombre="Profe", apellidos="Test", estado="Activo"))
    await db_session.commit()

    return {
        "admin_id": admin_id,
        "admin_token": _admin_token(admin_id),
        "profesor_token": _profesor_token(profe_id),
    }


@pytest_asyncio.fixture
async def materia_id(db_session: AsyncSession) -> UUID:
    return await _seed_materia_test(db_session)


# ── Test: POST /api/comunicaciones/preview ─────────────────────────────


class TestPreviewEndpoint:
    async def test_preview_200(
        self, client: AsyncClient, seed_db: dict
    ) -> None:
        resp = await client.post(
            "/api/comunicaciones/preview",
            json={
                "asunto": "Test asunto",
                "cuerpo": "Test cuerpo",
                "destinatarios": [{"tipo": "email", "valor": "a@test.com"}],
            },
            headers={"Authorization": f"Bearer {seed_db['admin_token']}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "preview_token" in body
        assert body["cantidad_destinatarios"] == 1

    async def test_preview_sin_auth_401(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/comunicaciones/preview",
            json={
                "asunto": "Test",
                "cuerpo": "Cuerpo",
                "destinatarios": [{"tipo": "email", "valor": "a@test.com"}],
            },
        )
        assert resp.status_code == 401

    async def test_preview_invalido_422(
        self, client: AsyncClient, seed_db: dict
    ) -> None:
        resp = await client.post(
            "/api/comunicaciones/preview",
            json={},
            headers={"Authorization": f"Bearer {seed_db['admin_token']}"},
        )
        assert resp.status_code == 422


# ── Test: POST /api/comunicaciones/enviar ──────────────────────────────


class TestEnviarEndpoint:
    async def test_enviar_200(
        self,
        client: AsyncClient,
        seed_db: dict,
        materia_id: UUID,
    ) -> None:
        headers = {"Authorization": f"Bearer {seed_db['admin_token']}"}

        preview_resp = await client.post(
            "/api/comunicaciones/preview",
            json={
                "asunto": "Test asunto",
                "cuerpo": "Test cuerpo",
                "destinatarios": [
                    {"tipo": "email", "valor": "a@test.com"},
                    {"tipo": "email", "valor": "b@test.com"},
                ],
            },
            headers=headers,
        )
        pt = preview_resp.json()["preview_token"]

        resp = await client.post(
            "/api/comunicaciones/enviar",
            json={
                "preview_token": pt,
                "asunto": "Test asunto",
                "cuerpo": "Test cuerpo",
                "materia_id": str(materia_id),
                "acepta_terminos": True,
                "destinatarios": [
                    {"tipo": "email", "valor": "a@test.com"},
                    {"tipo": "email", "valor": "b@test.com"},
                ],
            },
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "lote_id" in body
        assert body["total_mensajes"] == 2

    async def test_enviar_requiere_aprobacion(
        self,
        client: AsyncClient,
        seed_db: dict,
        materia_id: UUID,
    ) -> None:
        headers = {"Authorization": f"Bearer {seed_db['admin_token']}"}

        preview_resp = await client.post(
            "/api/comunicaciones/preview",
            json={
                "asunto": "Necesita aprob",
                "cuerpo": "Cuerpo",
                "destinatarios": [
                    {"tipo": "email", "valor": "a@test.com"},
                    {"tipo": "email", "valor": "b@test.com"},
                ],
            },
            headers=headers,
        )
        pt = preview_resp.json()["preview_token"]

        resp = await client.post(
            "/api/comunicaciones/enviar",
            json={
                "preview_token": pt,
                "asunto": "Necesita aprob",
                "cuerpo": "Cuerpo",
                "materia_id": str(materia_id),
                "acepta_terminos": True,
                "requiere_aprobacion": True,
                "destinatarios": [
                    {"tipo": "email", "valor": "a@test.com"},
                    {"tipo": "email", "valor": "b@test.com"},
                ],
            },
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["requiere_aprobacion"] is True

    async def test_enviar_sin_preview_422(
        self,
        client: AsyncClient,
        seed_db: dict,
        materia_id: UUID,
    ) -> None:
        headers = {"Authorization": f"Bearer {seed_db['admin_token']}"}
        resp = await client.post(
            "/api/comunicaciones/enviar",
            json={
                "asunto": "Test",
                "cuerpo": "Cuerpo",
                "materia_id": str(materia_id),
                "acepta_terminos": True,
                "destinatarios": [{"tipo": "email", "valor": "a@test.com"}],
            },
            headers=headers,
        )
        assert resp.status_code == 422

    async def test_enviar_sin_permiso_403(
        self,
        client: AsyncClient,
        seed_db: dict,
        materia_id: UUID,
    ) -> None:
        """Usuario con rol ALUMNO (no tiene comunicacion:enviar)."""
        alumno_token = create_access_token(
            user_id=uuid4(),
            tenant_id=_DEV_TENANT_ID,
            secret_key=_SECRET_KEY,
            roles=["ALUMNO"],
        )
        resp = await client.post(
            "/api/comunicaciones/enviar",
            json={
                "preview_token": "abc123",
                "asunto": "Test",
                "cuerpo": "Cuerpo",
                "materia_id": str(materia_id),
                "acepta_terminos": True,
                "destinatarios": [{"tipo": "email", "valor": "a@test.com"}],
            },
            headers={"Authorization": f"Bearer {alumno_token}"},
        )
        assert resp.status_code == 403


# ── Test: POST /api/comunicaciones/enviar-individual ───────────────────


class TestEnviarIndividualEndpoint:
    async def test_enviar_individual_200(
        self,
        client: AsyncClient,
        seed_db: dict,
        materia_id: UUID,
    ) -> None:
        headers = {"Authorization": f"Bearer {seed_db['admin_token']}"}
        dest_ep_id = uuid4()

        preview_resp = await client.post(
            "/api/comunicaciones/preview",
            json={
                "asunto": "Test individual",
                "cuerpo": "Cuerpo individual",
                "destinatarios": [{"tipo": "entrada_padron_id", "valor": str(dest_ep_id)}],
            },
            headers=headers,
        )
        pt = preview_resp.json()["preview_token"]

        resp = await client.post(
            "/api/comunicaciones/enviar-individual",
            json={
                "preview_token": pt,
                "asunto": "Test individual",
                "cuerpo": "Cuerpo individual",
                "materia_id": str(materia_id),
                "acepta_terminos": True,
                "entrada_padron_id": str(dest_ep_id),
            },
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "comunicacion_id" in body
        assert body["estado"] == "Pendiente"


# ── Test: GET /api/comunicaciones/{lote_id} ────────────────────────────


class TestGetLoteEndpoint:
    async def test_get_lote_200(
        self,
        client: AsyncClient,
        seed_db: dict,
        materia_id: UUID,
    ) -> None:
        headers = {"Authorization": f"Bearer {seed_db['admin_token']}"}

        preview_resp = await client.post(
            "/api/comunicaciones/preview",
            json={
                "asunto": "Test",
                "cuerpo": "Cuerpo",
                "destinatarios": [{"tipo": "email", "valor": "a@test.com"}],
            },
            headers=headers,
        )
        pt = preview_resp.json()["preview_token"]

        envio_resp = await client.post(
            "/api/comunicaciones/enviar",
            json={
                "preview_token": pt,
                "asunto": "Test",
                "cuerpo": "Cuerpo",
                "materia_id": str(materia_id),
                "acepta_terminos": True,
                "destinatarios": [{"tipo": "email", "valor": "a@test.com"}],
            },
            headers=headers,
        )
        lote_id = envio_resp.json()["lote_id"]

        resp = await client.get(f"/api/comunicaciones/{lote_id}", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["lote_id"] == lote_id


# ── Test: PUT /api/comunicaciones/{lote_id}/aprobar ────────────────────


class TestAprobarLoteEndpoint:
    async def test_aprobar_200(
        self,
        client: AsyncClient,
        seed_db: dict,
        materia_id: UUID,
    ) -> None:
        headers = {"Authorization": f"Bearer {seed_db['admin_token']}"}

        preview_resp = await client.post(
            "/api/comunicaciones/preview",
            json={
                "asunto": "Test aprobar",
                "cuerpo": "Cuerpo",
                "destinatarios": [{"tipo": "email", "valor": "a@test.com"}],
            },
            headers=headers,
        )
        pt = preview_resp.json()["preview_token"]

        envio_resp = await client.post(
            "/api/comunicaciones/enviar",
            json={
                "preview_token": pt,
                "asunto": "Test aprobar",
                "cuerpo": "Cuerpo",
                "materia_id": str(materia_id),
                "acepta_terminos": True,
                "requiere_aprobacion": True,
                "destinatarios": [{"tipo": "email", "valor": "a@test.com"}],
            },
            headers=headers,
        )
        lote_id = envio_resp.json()["lote_id"]

        resp = await client.put(
            f"/api/comunicaciones/{lote_id}/aprobar",
            json={"accion": "aprobar"},
            headers=headers,
        )
        assert resp.status_code == 200

    async def test_aprobar_403_sin_permiso(
        self,
        client: AsyncClient,
        seed_db: dict,
        materia_id: UUID,
    ) -> None:
        admin_headers = {"Authorization": f"Bearer {seed_db['admin_token']}"}

        preview_resp = await client.post(
            "/api/comunicaciones/preview",
            json={
                "asunto": "Test",
                "cuerpo": "Cuerpo",
                "destinatarios": [{"tipo": "email", "valor": "a@test.com"}],
            },
            headers=admin_headers,
        )
        pt = preview_resp.json()["preview_token"]

        envio_resp = await client.post(
            "/api/comunicaciones/enviar",
            json={
                "preview_token": pt,
                "asunto": "Test",
                "cuerpo": "Cuerpo",
                "materia_id": str(materia_id),
                "acepta_terminos": True,
                "requiere_aprobacion": True,
                "destinatarios": [{"tipo": "email", "valor": "a@test.com"}],
            },
            headers=admin_headers,
        )
        lote_id = envio_resp.json()["lote_id"]

        alumno_token = create_access_token(
            user_id=uuid4(),
            tenant_id=_DEV_TENANT_ID,
            secret_key=_SECRET_KEY,
            roles=["ALUMNO"],
        )
        resp = await client.put(
            f"/api/comunicaciones/{lote_id}/aprobar",
            json={"accion": "aprobar"},
            headers={"Authorization": f"Bearer {alumno_token}"},
        )
        assert resp.status_code == 403


# ── Test: GET /api/comunicaciones/mis-envios ───────────────────────────


class TestMisEnviosEndpoint:
    async def test_mis_envios_200(
        self,
        client: AsyncClient,
        seed_db: dict,
        materia_id: UUID,
    ) -> None:
        headers = {"Authorization": f"Bearer {seed_db['admin_token']}"}

        preview_resp = await client.post(
            "/api/comunicaciones/preview",
            json={
                "asunto": "Test",
                "cuerpo": "Cuerpo",
                "destinatarios": [{"tipo": "email", "valor": "a@test.com"}],
            },
            headers=headers,
        )
        pt = preview_resp.json()["preview_token"]

        await client.post(
            "/api/comunicaciones/enviar",
            json={
                "preview_token": pt,
                "asunto": "Test",
                "cuerpo": "Cuerpo",
                "materia_id": str(materia_id),
                "acepta_terminos": True,
                "destinatarios": [{"tipo": "email", "valor": "a@test.com"}],
            },
            headers=headers,
        )

        resp = await client.get(
            "/api/comunicaciones/mis-envios?pagina=1&tamano=10",
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert body["total"] >= 1


# ── Test: POST /api/comunicaciones/{id}/cancelar ───────────────────────


class TestCancelarEndpoint:
    async def test_cancelar_200(
        self,
        client: AsyncClient,
        seed_db: dict,
        materia_id: UUID,
    ) -> None:
        headers = {"Authorization": f"Bearer {seed_db['admin_token']}"}

        preview_resp = await client.post(
            "/api/comunicaciones/preview",
            json={
                "asunto": "Test",
                "cuerpo": "Cuerpo",
                "destinatarios": [{"tipo": "email", "valor": "a@test.com"}],
            },
            headers=headers,
        )
        pt = preview_resp.json()["preview_token"]

        envio_resp = await client.post(
            "/api/comunicaciones/enviar",
            json={
                "preview_token": pt,
                "asunto": "Test",
                "cuerpo": "Cuerpo",
                "materia_id": str(materia_id),
                "acepta_terminos": True,
                "destinatarios": [{"tipo": "email", "valor": "a@test.com"}],
            },
            headers=headers,
        )
        lote_id = envio_resp.json()["lote_id"]

        resp = await client.post(
            f"/api/comunicaciones/{lote_id}/cancelar",
            headers=headers,
        )
        assert resp.status_code == 200

    async def test_cancelar_404(
        self,
        client: AsyncClient,
        seed_db: dict,
    ) -> None:
        resp = await client.post(
            f"/api/comunicaciones/{uuid4()}/cancelar",
            headers={"Authorization": f"Bearer {seed_db['admin_token']}"},
        )
        assert resp.status_code == 404
