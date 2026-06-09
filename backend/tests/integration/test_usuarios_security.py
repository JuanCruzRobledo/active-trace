"""Tests de seguridad y cumplimiento para Usuarios (C-07, Grupo 5).

Cubre:
  5.1 PII enmascarada en respuestas HTTP (ningun campo en texto plano)
  5.2 PII no visible en logs de aplicacion (via caplog)
  5.3 Aislamiento multi-tenant: Tenant A no ve usuarios del Tenant B
  5.4 Vigencia: asignacion con ``hasta < today`` no autoriza acceso
  5.5 Jerarquia: responsable_id se persiste y puede consultarse

Requiere PostgreSQL real (DATABASE_URL_TEST en el entorno).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
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
_OTHER_TENANT_ID = UUID("00000000-0000-0000-0000-000000000099")
_SECRET_KEY = "a" * 64


# ── Helpers ────────────────────────────────────────────────────────────


def _admin_token(tenant_id: UUID = _DEV_TENANT_ID) -> str:
    """Crea JWT con rol ADMIN."""
    return create_access_token(
        user_id=uuid4(),
        tenant_id=tenant_id,
        secret_key=_SECRET_KEY,
        roles=["ADMIN"],
    )


def _coord_token(tenant_id: UUID = _DEV_TENANT_ID) -> str:
    """Crea JWT con rol COORDINADOR (tiene equipos:asignar)."""
    return create_access_token(
        user_id=uuid4(),
        tenant_id=tenant_id,
        secret_key=_SECRET_KEY,
        roles=["COORDINADOR"],
    )


async def _seed_permiso_admin(
    db_session: AsyncSession,
    tenant_id: UUID = _DEV_TENANT_ID,
) -> None:
    """Seed minimo para admin:gestionar-usuarios."""
    await db_session.execute(
        text(
            "INSERT INTO permiso (id, codigo, descripcion, created_at) "
            "VALUES (:id, :codigo, :descripcion, now()) "
            "ON CONFLICT (codigo) DO NOTHING"
        ),
        {
            "id": uuid4(),
            "codigo": "admin:gestionar-usuarios",
            "descripcion": "Gestionar usuarios del sistema",
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
            "tenant_id": tenant_id,
            "codigo": "ADMIN",
            "nombre": "Administrador",
            "descripcion": "Admin",
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
            "tenant_id": tenant_id,
            "rol_id": rol_id,
            "permiso_id": (
                await db_session.execute(
                    text("SELECT id FROM permiso WHERE codigo='admin:gestionar-usuarios'")
                )
            ).scalar_one(),
        },
    )
    await db_session.commit()


async def _seed_permiso_asignaciones(
    db_session: AsyncSession,
    tenant_id: UUID = _DEV_TENANT_ID,
) -> None:
    """Seed minimo para equipos:asignar."""
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
            "tenant_id": tenant_id,
            "codigo": "COORDINADOR",
            "nombre": "Coordinador",
            "descripcion": "Coord",
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
            "tenant_id": tenant_id,
            "rol_id": rol_id,
            "permiso_id": (
                await db_session.execute(
                    text("SELECT id FROM permiso WHERE codigo='equipos:asignar'")
                )
            ).scalar_one(),
        },
    )
    await db_session.commit()


async def _seed_usuario(
    db_session: AsyncSession,
    email: str = "security@test.com",
    tenant_id: UUID = _DEV_TENANT_ID,
) -> UUID:
    """Crea un usuario de prueba y commitea para que otras sesiones lo vean."""
    from app.models.usuario import Usuario

    u = Usuario(
        tenant_id=tenant_id,
        nombre="Security",
        apellidos="Test",
        email=email,
        dni="87654321",
        cuil="20-87654321-9",
        cbu="0000003100011234567890",
        alias_cbu="SEC.ALIAS",
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


# ═══════════════════════════════════════════════════════════════════════
# 5.1 — PII enmascarada en respuestas HTTP
# ═══════════════════════════════════════════════════════════════════════


class TestPiiMaskedInResponses:
    """Ningun campo PII aparece en texto plano en respuestas HTTP."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(
        self, db_session: AsyncSession, seed_dev_tenant: None
    ) -> None:
        await _seed_permiso_admin(db_session)

    async def test_crear_respuesta_no_expone_pii_plano(
        self, client: AsyncClient
    ) -> None:
        """La respuesta de POST no contiene los valores PII en texto plano."""
        pii_data = {
            "nombre": "PiiCheck",
            "apellidos": "User",
            "email": "pii-check@example.com",
            "dni": "11223344",
            "cuil": "27-11223344-5",
            "cbu": "0000003100019876543210",
            "alias_cbu": "PII.CHECK",
        }
        headers = {"Authorization": f"Bearer {_admin_token()}"}
        resp = await client.post(
            "/api/admin/usuarios", json=pii_data, headers=headers
        )
        assert resp.status_code == 201
        body_text = resp.text

        # Ningun valor PII en texto plano debe aparecer en la respuesta
        assert "pii-check@example.com" not in body_text
        assert "11223344" not in body_text
        assert "27-11223344-5" not in body_text
        assert "0000003100019876543210" not in body_text
        assert "PII.CHECK" not in body_text

    async def test_get_respuesta_no_expone_pii_plano(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """La respuesta de GET /{id} no contiene PII en texto plano."""
        uid = await _seed_usuario(
            db_session, email="get-pii@example.com"
        )
        await db_session.commit()

        headers = {"Authorization": f"Bearer {_admin_token()}"}
        resp = await client.get(
            f"/api/admin/usuarios/{uid}", headers=headers
        )
        assert resp.status_code == 200

        body = resp.json()
        # Verificar cada campo PII esta enmascarado
        assert body["email"] != "get-pii@example.com"
        assert "***" in body["email"]
        assert "***" in body["dni"]
        assert "***" in body["cuil"]
        assert "***" in body["cbu"]
        assert "***" in body.get("alias_cbu", "") or "***" in str(body.get("alias_cbu"))

    async def test_listar_no_expone_pii_plano(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """La respuesta de GET / no contiene PII en texto plano."""
        await _seed_usuario(db_session, email="list-pii@example.com")
        await db_session.commit()

        headers = {"Authorization": f"Bearer {_admin_token()}"}
        resp = await client.get("/api/admin/usuarios", headers=headers)
        assert resp.status_code == 200
        body_text = resp.text

        assert "list-pii@example.com" not in body_text
        assert "87654321" not in body_text


# ═══════════════════════════════════════════════════════════════════════
# 5.2 — PII no visible en logs
# ═══════════════════════════════════════════════════════════════════════


class TestPiiNoEnLogs:
    """Los logs de aplicacion no contienen PII en texto plano."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(
        self, db_session: AsyncSession, seed_dev_tenant: None
    ) -> None:
        await _seed_permiso_admin(db_session)

    async def test_crear_usuario_no_logea_pii(
        self, client: AsyncClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Crear usuario no produce logs con PII en texto plano."""
        caplog.set_level("DEBUG")
        pii_email = "log-check@example.com"

        headers = {"Authorization": f"Bearer {_admin_token()}"}
        resp = await client.post(
            "/api/admin/usuarios",
            json={
                "nombre": "Log",
                "apellidos": "Check",
                "email": pii_email,
                "dni": "99887766",
            },
            headers=headers,
        )
        assert resp.status_code == 201

        # Revisar todos los registros de log
        combined = " | ".join(rec.getMessage() for rec in caplog.records)
        assert pii_email not in combined
        assert "99887766" not in combined

    async def test_listar_usuarios_no_logea_pii(
        self, client: AsyncClient, db_session: AsyncSession, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Listar usuarios no produce logs con PII en texto plano."""
        caplog.set_level("DEBUG")
        await _seed_usuario(db_session, email="list-log@example.com")
        await db_session.commit()

        headers = {"Authorization": f"Bearer {_admin_token()}"}
        resp = await client.get("/api/admin/usuarios", headers=headers)
        assert resp.status_code == 200

        combined = " | ".join(rec.getMessage() for rec in caplog.records)
        assert "list-log@example.com" not in combined


# ═══════════════════════════════════════════════════════════════════════
# 5.3 — Aislamiento multi-tenant
# ═══════════════════════════════════════════════════════════════════════


class TestMultiTenantIsolation:
    """Tenant A no puede leer/escribir usuarios del Tenant B."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(
        self, db_session: AsyncSession, seed_dev_tenant: None
    ) -> None:
        # Seed RBAC para AMBOS tenants (cada tenant debe tener su propio ADMIN)
        await _seed_permiso_admin(db_session, _DEV_TENANT_ID)
        await _seed_permiso_admin(db_session, _OTHER_TENANT_ID)

    async def test_tenant_b_no_ve_usuarios_de_tenant_a(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Tenant B obtiene 404 al consultar usuario del Tenant A."""
        uid = await _seed_usuario(
            db_session, email="tenant-a@example.com", tenant_id=_DEV_TENANT_ID
        )
        await db_session.commit()

        # Token del Tenant B
        headers = {"Authorization": f"Bearer {_admin_token(tenant_id=_OTHER_TENANT_ID)}"}
        resp = await client.get(
            f"/api/admin/usuarios/{uid}", headers=headers
        )
        # Debe ser 404 por aislamiento (repo filtra por tenant_id)
        assert resp.status_code == 404

    async def test_tenant_b_lista_vacio(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Tenant B lista 0 usuarios del Tenant A."""
        await _seed_usuario(
            db_session, email="tenant-list@example.com", tenant_id=_DEV_TENANT_ID
        )
        await db_session.commit()

        headers = {"Authorization": f"Bearer {_admin_token(tenant_id=_OTHER_TENANT_ID)}"}
        resp = await client.get("/api/admin/usuarios", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert len(body["items"]) == 0

    async def test_tenant_b_no_edita_usuario_tenant_a(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Tenant B obtiene 404 al intentar editar usuario del Tenant A."""
        uid = await _seed_usuario(
            db_session, email="tenant-edit@example.com", tenant_id=_DEV_TENANT_ID
        )
        await db_session.commit()

        headers = {"Authorization": f"Bearer {_admin_token(tenant_id=_OTHER_TENANT_ID)}"}
        resp = await client.patch(
            f"/api/admin/usuarios/{uid}",
            json={"nombre": "Hacker"},
            headers=headers,
        )
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════
# 5.4 — Vigencia: asignacion vencida no autoriza
# ═══════════════════════════════════════════════════════════════════════


class TestVigenciaAsignacion:
    """Asignacion vencida no otorga acceso."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(
        self, db_session: AsyncSession, seed_dev_tenant: None
    ) -> None:
        await _seed_permiso_asignaciones(db_session)

    async def test_asignacion_vencida_estado_vencida(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Asignacion con hasta en el pasado tiene estado_vigencia 'Vencida'."""
        from app.models.usuario import Usuario

        u = Usuario(
            tenant_id=_DEV_TENANT_ID,
            nombre="Vencida",
            apellidos="User",
            email="vencida-vig@test.com",
            dni="11111111",
        )
        db_session.add(u)
        await db_session.flush()
        await db_session.commit()
        uid = u.id

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
        assert resp.json()["estado_vigencia"] == "Vencida"

    async def test_asignacion_vigente_estado_vigente(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Asignacion con hasta en el futuro tiene estado_vigencia 'Vigente'."""
        from app.models.usuario import Usuario

        u = Usuario(
            tenant_id=_DEV_TENANT_ID,
            nombre="Vigente",
            apellidos="User",
            email="vigente@test.com",
            dni="22222222",
        )
        db_session.add(u)
        await db_session.flush()
        await db_session.commit()
        uid = u.id

        future = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
        headers = {"Authorization": f"Bearer {_coord_token()}"}
        resp = await client.post(
            "/api/asignaciones",
            json={
                "usuario_id": str(uid),
                "rol": "PROFESOR",
                "desde": "2020-01-01T00:00:00Z",
                "hasta": future,
            },
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["estado_vigencia"] == "Vigente"

    async def test_asignacion_sin_hasta_es_vigente(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Asignacion sin hasta (None) es 'Vigente'."""
        from app.models.usuario import Usuario

        u = Usuario(
            tenant_id=_DEV_TENANT_ID,
            nombre="Abierta",
            apellidos="User",
            email="abierta@test.com",
            dni="33333333",
        )
        db_session.add(u)
        await db_session.flush()
        await db_session.commit()
        uid = u.id

        headers = {"Authorization": f"Bearer {_coord_token()}"}
        resp = await client.post(
            "/api/asignaciones",
            json={
                "usuario_id": str(uid),
                "rol": "PROFESOR",
                "desde": "2020-01-01T00:00:00Z",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["estado_vigencia"] == "Vigente"


# ═══════════════════════════════════════════════════════════════════════
# 5.5 — Jerarquia: responsable_id se persiste y consulta
# ═══════════════════════════════════════════════════════════════════════


class TestJerarquiaAsignacion:
    """responsable_id se persiste y puede consultarse."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(
        self, db_session: AsyncSession, seed_dev_tenant: None
    ) -> None:
        await _seed_permiso_asignaciones(db_session)

    async def test_asignacion_con_responsable_se_persiste(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Asignacion con responsable_id persiste el vinculo."""
        from app.models.usuario import Usuario

        responsable = Usuario(
            tenant_id=_DEV_TENANT_ID,
            nombre="Responsable",
            apellidos="User",
            email="resp@test.com",
            dni="44444444",
        )
        tutor = Usuario(
            tenant_id=_DEV_TENANT_ID,
            nombre="Tutor",
            apellidos="User",
            email="tutor-jer@test.com",
            dni="55555555",
        )
        db_session.add(responsable)
        db_session.add(tutor)
        await db_session.flush()
        await db_session.commit()

        headers = {"Authorization": f"Bearer {_coord_token()}"}
        resp = await client.post(
            "/api/asignaciones",
            json={
                "usuario_id": str(tutor.id),
                "rol": "TUTOR",
                "responsable_id": str(responsable.id),
                "desde": "2024-01-01T00:00:00Z",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["responsable_id"] == str(responsable.id)

        # Verificar que se puede consultar via GET
        aid = body["id"]
        get_resp = await client.get(
            f"/api/asignaciones/{aid}", headers=headers
        )
        assert get_resp.status_code == 200
        assert get_resp.json()["responsable_id"] == str(responsable.id)
