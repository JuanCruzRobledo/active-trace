"""Tests E2E de API para padron-ingesta (C-09).

Cubre:
  POST /api/padron/importar  — preview + confirm xlsx/csv
  GET  /api/padron/{materia_id}/{cohorte_id} — padron activo
  DELETE /api/padron/{materia_id}/vaciar — vaciar materia

Protegido con require_permission("padron:importar").

Requiere PostgreSQL real (DATABASE_URL_TEST en el entorno).
"""

from __future__ import annotations

import io
from uuid import UUID, uuid4

import pytest
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
    """Crea JWT con rol ADMIN (tiene padron:importar)."""
    return create_access_token(
        user_id=uuid4(),
        tenant_id=_DEV_TENANT_ID,
        secret_key=_SECRET_KEY,
        roles=["ADMIN"],
    )


def _alumno_token() -> str:
    """Crea JWT con rol ALUMNO (NO tiene padron:importar)."""
    return create_access_token(
        user_id=uuid4(),
        tenant_id=_DEV_TENANT_ID,
        secret_key=_SECRET_KEY,
        roles=["ALUMNO"],
    )


async def _seed_rbac_padron(db_session: AsyncSession) -> None:
    """Seed minimo para que padron:importar funcione."""
    perm_id = uuid4()
    await db_session.execute(
        text(
            "INSERT INTO permiso (id, codigo, descripcion, created_at) "
            "VALUES (:id, :codigo, :descripcion, now()) "
            "ON CONFLICT (codigo) DO NOTHING"
        ),
        {
            "id": perm_id,
            "codigo": "padron:importar",
            "descripcion": "Importar padron de alumnos",
        },
    )

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
            "descripcion": "Admin del sistema",
        },
    )

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


async def _seed_materia_cohorte(db_session: AsyncSession) -> tuple[UUID, UUID]:
    """Inserta materia y cohorte de prueba, retorna (materia_id, cohorte_id)."""
    materia_id = uuid4()
    cohorte_id = uuid4()

    # Carrera
    carrera_id = uuid4()
    await db_session.execute(
        text(
            "INSERT INTO carrera (id, tenant_id, nombre, codigo, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :nombre, :codigo, now(), now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {
            "id": carrera_id,
            "tenant_id": _DEV_TENANT_ID,
            "nombre": "Ingenieria",
            "codigo": "ING",
        },
    )

    # Materia
    await db_session.execute(
        text(
            "INSERT INTO materia (id, tenant_id, nombre, codigo, "
            "carrera_id, carga_horaria, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :nombre, :codigo, :carrera_id, :carga, now(), now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {
            "id": materia_id,
            "tenant_id": _DEV_TENANT_ID,
            "nombre": "Matematicas",
            "codigo": "MAT101",
            "carrera_id": carrera_id,
            "carga": 120,
        },
    )

    # Cohorte
    await db_session.execute(
        text(
            "INSERT INTO cohorte (id, tenant_id, nombre, codigo, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :nombre, :codigo, now(), now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {
            "id": cohorte_id,
            "tenant_id": _DEV_TENANT_ID,
            "nombre": "2025",
            "codigo": "C2025",
        },
    )

    await db_session.commit()
    return materia_id, cohorte_id


async def _seed_usuario_email(db_session: AsyncSession, email: str) -> UUID:
    """Inserta un usuario de prueba y retorna su ID."""
    user_id = uuid4()
    await db_session.execute(
        text(
            "INSERT INTO usuario (id, tenant_id, email, nombres, apellidos, "
            "activo, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :email, :nombres, :apellidos, true, now(), now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {
            "id": user_id,
            "tenant_id": _DEV_TENANT_ID,
            "email": email,
            "nombres": "Juan",
            "apellidos": "Perez",
        },
    )
    await db_session.commit()
    return user_id


def _make_xlsx_bytes() -> bytes:
    """Genera un xlsx en memoria con 3 filas de alumnos."""
    try:
        import openpyxl  # noqa: PLC0415
    except ImportError:
        pytest.skip("openpyxl no instalado")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Alumnos"
    ws.append(["nombre", "apellidos", "email", "comision", "regional"])
    ws.append(["Juan", "Perez", "juan@test.com", "A", "CABA"])
    ws.append(["Maria", "Garcia", "maria@test.com", "B", "GBA"])
    ws.append(["Carlos", "Lopez", "carlos@test.com", "A", "CABA"])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


def _make_csv_bytes() -> bytes:
    """Genera un CSV en memoria con 2 filas de alumnos."""
    import csv  # noqa: PLC0415
    import io  # noqa: PLC0415

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["nombre", "apellidos", "email", "comision", "regional"])
    writer.writerow(["Ana", "Diaz", "ana@test.com", "A", "CABA"])
    writer.writerow(["Pedro", "Ramirez", "pedro@test.com", "B", "GBA"])
    return buf.getvalue().encode("utf-8-sig")


# ── Fixtures ───────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _patch_env(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", _SECRET_KEY)
    monkeypatch.setenv("ENCRYPTION_KEY", "b" * 32)


# ═══════════════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════════════


class TestImportarPadron:
    """POST /api/padron/importar — preview y confirm."""

    async def test_preview_xlsx(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """F1a: Preview de xlsx devuelve preview con filas leidas."""
        await _seed_rbac_padron(db_session)
        token = _admin_token()
        materia_id, cohorte_id = await _seed_materia_cohorte(db_session)
        xlsx_data = _make_xlsx_bytes()

        response = await client.post(
            "/api/padron/importar",
            files={"file": ("alumnos.xlsx", xlsx_data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={
                "materia_id": str(materia_id),
                "cohorte_id": str(cohorte_id),
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["preview"] is True
        assert body["filas_leidas"] == 3
        assert "preview_token" in body
        assert len(body["filas"]) == 3
        assert body["filas"][0]["nombre"] == "Juan"

    async def test_preview_csv(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """F1a: Preview de csv devuelve preview con filas leidas."""
        await _seed_rbac_padron(db_session)
        token = _admin_token()
        materia_id, cohorte_id = await _seed_materia_cohorte(db_session)
        csv_data = _make_csv_bytes()

        response = await client.post(
            "/api/padron/importar",
            files={"file": ("alumnos.csv", csv_data, "text/csv")},
            data={
                "materia_id": str(materia_id),
                "cohorte_id": str(cohorte_id),
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["preview"] is True
        assert body["filas_leidas"] == 2
        assert "preview_token" in body

    async def test_confirm_importacion(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """F1b: Confirm importacion persiste version + entradas y retorna summary."""
        await _seed_rbac_padron(db_session)
        token = _admin_token()
        materia_id, cohorte_id = await _seed_materia_cohorte(db_session)
        xlsx_data = _make_xlsx_bytes()

        # Paso 1: preview
        preview_resp = await client.post(
            "/api/padron/importar",
            files={"file": ("alumnos.xlsx", xlsx_data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={
                "materia_id": str(materia_id),
                "cohorte_id": str(cohorte_id),
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert preview_resp.status_code == 200
        preview_token = preview_resp.json()["preview_token"]

        # Paso 2: confirm
        confirm_resp = await client.post(
            "/api/padron/importar",
            files={"file": ("alumnos.xlsx", xlsx_data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={
                "materia_id": str(materia_id),
                "cohorte_id": str(cohorte_id),
                "preview_token": preview_token,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert confirm_resp.status_code == 200
        body = confirm_resp.json()
        assert body["version_id"] is not None
        assert body["materia_id"] == str(materia_id)
        assert body["cantidad_entradas"] == 3

    async def test_confirm_token_invalido(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """F1c: Token invalido → 400."""
        await _seed_rbac_padron(db_session)
        token = _admin_token()
        materia_id, cohorte_id = await _seed_materia_cohorte(db_session)

        response = await client.post(
            "/api/padron/importar",
            files={"file": ("alumnos.xlsx", b"fake", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={
                "materia_id": str(materia_id),
                "cohorte_id": str(cohorte_id),
                "preview_token": "token-invalido",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400
        assert "preview" in response.json()["detail"].lower()

    async def test_autorizacion_denegada(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """F1d: ALUMNO no tiene padron:importar → 403."""
        await _seed_rbac_padron(db_session)
        token = _alumno_token()
        materia_id, cohorte_id = await _seed_materia_cohorte(db_session)

        response = await client.post(
            "/api/padron/importar",
            files={"file": ("alumnos.xlsx", b"test", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={
                "materia_id": str(materia_id),
                "cohorte_id": str(cohorte_id),
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403

    async def test_archivo_vacio(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """F1e: Archivo vacio → 422."""
        await _seed_rbac_padron(db_session)
        token = _admin_token()
        materia_id, cohorte_id = await _seed_materia_cohorte(db_session)

        response = await client.post(
            "/api/padron/importar",
            files={"file": ("vacio.xlsx", b"", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={
                "materia_id": str(materia_id),
                "cohorte_id": str(cohorte_id),
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 422

    async def test_import_con_matching_email(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """F2a: Alumnos con email coincidente se vinculan a usuario existente."""
        await _seed_rbac_padron(db_session)
        token = _admin_token()
        materia_id, cohorte_id = await _seed_materia_cohorte(db_session)
        user_id = await _seed_usuario_email(db_session, "juan@test.com")

        xlsx_data = _make_xlsx_bytes()

        # preview
        preview_resp = await client.post(
            "/api/padron/importar",
            files={"file": ("alumnos.xlsx", xlsx_data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={
                "materia_id": str(materia_id),
                "cohorte_id": str(cohorte_id),
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        preview_token = preview_resp.json()["preview_token"]

        # confirm
        confirm_resp = await client.post(
            "/api/padron/importar",
            files={"file": ("alumnos.xlsx", xlsx_data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={
                "materia_id": str(materia_id),
                "cohorte_id": str(cohorte_id),
                "preview_token": preview_token,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert confirm_resp.status_code == 200

        # Verificar que juan@test.com quedo vinculado
        version_id = confirm_resp.json()["version_id"]
        get_response = await client.get(
            f"/api/padron/{materia_id}/{cohorte_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_response.status_code == 200
        entradas = get_response.json()["entradas"]
        juan = next(e for e in entradas if e["email"] == "juan@test.com")
        assert juan["usuario_id"] is not None


class TestObtenerPadronActivo:
    """GET /api/padron/{materia_id}/{cohorte_id}."""

    async def test_obtener_padron_activo(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """F3a: Retorna version activa con entradas."""
        await _seed_rbac_padron(db_session)
        token = _admin_token()
        materia_id, cohorte_id = await _seed_materia_cohorte(db_session)
        xlsx_data = _make_xlsx_bytes()

        # Preview + confirm
        preview_resp = await client.post(
            "/api/padron/importar",
            files={"file": ("alumnos.xlsx", xlsx_data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={
                "materia_id": str(materia_id),
                "cohorte_id": str(cohorte_id),
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        preview_token = preview_resp.json()["preview_token"]

        await client.post(
            "/api/padron/importar",
            files={"file": ("alumnos.xlsx", xlsx_data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={
                "materia_id": str(materia_id),
                "cohorte_id": str(cohorte_id),
                "preview_token": preview_token,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        # GET activo
        response = await client.get(
            f"/api/padron/{materia_id}/{cohorte_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["materia_id"] == str(materia_id)
        assert body["activa"] is True
        assert len(body["entradas"]) == 3

    async def test_sin_padron_activo(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """F3b: Sin padron activo → 404."""
        await _seed_rbac_padron(db_session)
        token = _admin_token()

        response = await client.get(
            f"/api/padron/{uuid4()}/{uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404


class TestVaciarPadron:
    """DELETE /api/padron/{materia_id}/vaciar."""

    async def test_vaciar_materia(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """F4a: Vaciar desactiva versiones y elimina entradas."""
        await _seed_rbac_padron(db_session)
        token = _admin_token()
        materia_id, cohorte_id = await _seed_materia_cohorte(db_session)
        xlsx_data = _make_xlsx_bytes()

        # Crear padron primero
        preview_resp = await client.post(
            "/api/padron/importar",
            files={"file": ("alumnos.xlsx", xlsx_data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={
                "materia_id": str(materia_id),
                "cohorte_id": str(cohorte_id),
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        preview_token = preview_resp.json()["preview_token"]

        await client.post(
            "/api/padron/importar",
            files={"file": ("alumnos.xlsx", xlsx_data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={
                "materia_id": str(materia_id),
                "cohorte_id": str(cohorte_id),
                "preview_token": preview_token,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        # Vaciar
        response = await client.delete(
            f"/api/padron/{materia_id}/vaciar",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["versiones_desactivadas"] >= 1
        assert body["entradas_eliminadas"] == 3

        # Verificar que ya no hay padron activo
        get_response = await client.get(
            f"/api/padron/{materia_id}/{cohorte_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_response.status_code == 404

    async def test_vaciar_materia_sin_datos(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """F4b: Vaciar materia sin datos → 200 con 0."""
        await _seed_rbac_padron(db_session)
        token = _admin_token()
        materia_id = uuid4()

        response = await client.delete(
            f"/api/padron/{materia_id}/vaciar",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["versiones_desactivadas"] == 0
        assert body["entradas_eliminadas"] == 0
