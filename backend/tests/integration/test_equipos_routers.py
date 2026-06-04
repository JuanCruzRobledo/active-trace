"""Tests E2E de API para Equipos Docentes (C-08).

Cubre:
  GET /api/equipos/mis-equipos — Docente ve sus asignaciones
  GET /api/equipos — COORDINADOR/ADMIN gestiona todas
  POST /api/equipos/asignacion-masiva — Asignación masiva
  POST /api/equipos/clonar — Clonar equipo
  PATCH /api/equipos/vigencia — Modificar vigencia
  GET /api/equipos/export — Export CSV

Protegido con require_permission("equipos:ver" | "equipos:asignar").
Requiere PostgreSQL real (DATABASE_URL_TEST en el entorno).
"""

from __future__ import annotations

from datetime import date, datetime, timezone
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


def _docente_token(user_id: UUID | None = None) -> str:
    """Crea JWT con rol DOCENTE (tiene equipos:ver)."""
    return create_access_token(
        user_id=user_id or uuid4(),
        tenant_id=_DEV_TENANT_ID,
        secret_key=_SECRET_KEY,
        roles=["DOCENTE"],
    )


def _coord_token() -> str:
    """Crea JWT con rol COORDINADOR (tiene equipos:asignar)."""
    return create_access_token(
        user_id=uuid4(),
        tenant_id=_DEV_TENANT_ID,
        secret_key=_SECRET_KEY,
        roles=["COORDINADOR"],
    )


def _alumno_token() -> str:
    """Crea JWT con rol ALUMNO (NO tiene permisos de equipo)."""
    return create_access_token(
        user_id=uuid4(),
        tenant_id=_DEV_TENANT_ID,
        secret_key=_SECRET_KEY,
        roles=["ALUMNO"],
    )


async def _seed_rbac_equipos(db_session: AsyncSession) -> None:
    """Seed minimo para que equipos:ver y equipos:asignar funcionen."""
    # Permiso equipos:asignar
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

    # Permiso equipos:ver
    await db_session.execute(
        text(
            "INSERT INTO permiso (id, codigo, descripcion, created_at) "
            "VALUES (:id, :codigo, :descripcion, now()) "
            "ON CONFLICT (codigo) DO NOTHING"
        ),
        {
            "id": uuid4(),
            "codigo": "equipos:ver",
            "descripcion": "Ver equipos docentes propios",
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

    # Rol DOCENTE
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
            "codigo": "DOCENTE",
            "nombre": "Docente",
            "descripcion": "Docente",
        },
    )

    _coord_rol_id = (await db_session.execute(
        text("SELECT id FROM rol WHERE tenant_id=:tid AND codigo='COORDINADOR'"),
        {"tid": _DEV_TENANT_ID},
    )).scalar_one()

    _docente_rol_id = (await db_session.execute(
        text("SELECT id FROM rol WHERE tenant_id=:tid AND codigo='DOCENTE'"),
        {"tid": _DEV_TENANT_ID},
    )).scalar_one()

    _asignar_perm_id = (await db_session.execute(
        text("SELECT id FROM permiso WHERE codigo='equipos:asignar'"),
    )).scalar_one()

    _ver_perm_id = (await db_session.execute(
        text("SELECT id FROM permiso WHERE codigo='equipos:ver'"),
    )).scalar_one()

    # Vincular COORDINADOR → equipos:asignar
    await db_session.execute(
        text(
            "INSERT INTO rol_permiso (id, tenant_id, rol_id, permiso_id, created_at) "
            "VALUES (:id, :tenant_id, :rol_id, :permiso_id, now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {
            "id": uuid4(),
            "tenant_id": _DEV_TENANT_ID,
            "rol_id": _coord_rol_id,
            "permiso_id": _asignar_perm_id,
        },
    )

    # Vincular COORDINADOR → equipos:ver
    await db_session.execute(
        text(
            "INSERT INTO rol_permiso (id, tenant_id, rol_id, permiso_id, created_at) "
            "VALUES (:id, :tenant_id, :rol_id, :permiso_id, now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {
            "id": uuid4(),
            "tenant_id": _DEV_TENANT_ID,
            "rol_id": _coord_rol_id,
            "permiso_id": _ver_perm_id,
        },
    )

    # Vincular DOCENTE → equipos:ver
    await db_session.execute(
        text(
            "INSERT INTO rol_permiso (id, tenant_id, rol_id, permiso_id, created_at) "
            "VALUES (:id, :tenant_id, :rol_id, :permiso_id, now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {
            "id": uuid4(),
            "tenant_id": _DEV_TENANT_ID,
            "rol_id": _docente_rol_id,
            "permiso_id": _ver_perm_id,
        },
    )

    await db_session.commit()


async def _seed_materia(db_session: AsyncSession) -> UUID:
    """Crea una materia de prueba."""
    mid = uuid4()
    await db_session.execute(
        text(
            "INSERT INTO materia (id, tenant_id, codigo, nombre, estado, "
            "created_at, updated_at) "
            "VALUES (:id, :tenant_id, :codigo, :nombre, :estado, now(), now())"
        ),
        {
            "id": mid,
            "tenant_id": _DEV_TENANT_ID,
            "codigo": f"MAT-{uuid4().hex[:8]}",
            "nombre": "Materia Test",
            "estado": "Activa",
        },
    )
    await db_session.commit()
    return mid


async def _seed_carrera(db_session: AsyncSession) -> UUID:
    """Crea una carrera de prueba."""
    cid = uuid4()
    await db_session.execute(
        text(
            "INSERT INTO carrera (id, tenant_id, codigo, nombre, estado, "
            "created_at, updated_at) "
            "VALUES (:id, :tenant_id, :codigo, :nombre, :estado, now(), now())"
        ),
        {
            "id": cid,
            "tenant_id": _DEV_TENANT_ID,
            "codigo": f"CAR-{uuid4().hex[:8]}",
            "nombre": "Carrera Test",
            "estado": "Activa",
        },
    )
    await db_session.commit()
    return cid


async def _seed_cohorte(db_session: AsyncSession, carrera_id: UUID) -> UUID:
    """Crea una cohorte de prueba."""
    coid = uuid4()
    await db_session.execute(
        text(
            "INSERT INTO cohorte (id, tenant_id, carrera_id, nombre, anio, "
            "vig_desde, estado, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :carrera_id, :nombre, :anio, "
            ":vig_desde, :estado, now(), now())"
        ),
        {
            "id": coid,
            "tenant_id": _DEV_TENANT_ID,
            "carrera_id": carrera_id,
            "nombre": f"C-{uuid4().hex[:6]}",
            "anio": 2024,
            "vig_desde": date(2024, 1, 1),
            "estado": "Activa",
        },
    )
    await db_session.commit()
    return coid


async def _seed_usuario(db_session: AsyncSession, email: str) -> UUID:
    """Crea un usuario de prueba via ORM."""
    from app.models.usuario import Usuario

    u = Usuario(
        tenant_id=_DEV_TENANT_ID,
        nombre="Test",
        apellidos="User",
        email=email,
        dni="00000000",
        estado="Activo",
    )
    db_session.add(u)
    await db_session.flush()
    await db_session.commit()
    return u.id


async def _seed_asignacion(
    db_session: AsyncSession,
    usuario_id: UUID,
    materia_id: UUID | None = None,
    carrera_id: UUID | None = None,
    cohorte_id: UUID | None = None,
    rol: str = "PROFESOR",
) -> UUID:
    """Crea una asignacion de prueba."""
    aid = uuid4()
    await db_session.execute(
        text(
            "INSERT INTO asignacion (id, tenant_id, usuario_id, rol, "
            "materia_id, carrera_id, cohorte_id, desde, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :usuario_id, :rol, "
            ":materia_id, :carrera_id, :cohorte_id, :desde, now(), now())"
        ),
        {
            "id": aid,
            "tenant_id": _DEV_TENANT_ID,
            "usuario_id": usuario_id,
            "rol": rol,
            "materia_id": materia_id,
            "carrera_id": carrera_id,
            "cohorte_id": cohorte_id,
            "desde": datetime(2024, 1, 1, tzinfo=timezone.utc),
        },
    )
    await db_session.commit()
    return aid


@ pytest.fixture(autouse=True)
def _patch_env(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", _SECRET_KEY)
    monkeypatch.setenv("ENCRYPTION_KEY", "b" * 32)
    monkeypatch.setenv("DATABASE_URL", "placeholder")


# ===========================================================================
# 403 — Sin permisos de equipo
# ===========================================================================


class TestEquiposApiSinPermiso:
    """Endpoints devuelven 403 si el token no tiene permisos."""

    async def test_mis_equipos_returns_403(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_alumno_token()}"}
        resp = await client.get(
            "/api/equipos/mis-equipos", headers=headers
        )
        assert resp.status_code == 403

    async def test_equipos_list_returns_403(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_docente_token()}"}
        resp = await client.get("/api/equipos", headers=headers)
        assert resp.status_code == 403

    async def test_asignacion_masiva_returns_403(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_docente_token()}"}
        resp = await client.post(
            "/api/equipos/asignacion-masiva",
            json={},
            headers=headers,
        )
        assert resp.status_code == 403

    async def test_clonar_returns_403(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_alumno_token()}"}
        resp = await client.post(
            "/api/equipos/clonar",
            json={},
            headers=headers,
        )
        assert resp.status_code == 403

    async def test_vigencia_returns_403(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_alumno_token()}"}
        resp = await client.patch(
            "/api/equipos/vigencia",
            json={},
            headers=headers,
        )
        assert resp.status_code == 403

    async def test_export_returns_403(
        self, client: AsyncClient
    ) -> None:
        headers = {"Authorization": f"Bearer {_alumno_token()}"}
        resp = await client.get("/api/equipos/export", headers=headers)
        assert resp.status_code == 403


# ===========================================================================
# Equipos API
# ===========================================================================


class TestEquiposApi:
    """Equipos docentes CRUD + operaciones especiales."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(
        self, db_session: AsyncSession, seed_dev_tenant: None
    ) -> None:
        await _seed_rbac_equipos(db_session)

    # ── GET /api/equipos/mis-equipos ──────────────────────────────────

    async def test_mis_equipos_returns_user_assignments(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """mis-equipos retorna solo las asignaciones del usuario autenticado."""
        user_id = uuid4()
        otro_user_id = uuid4()
        uid = await _seed_usuario(db_session, "docente@test.com")
        otro_uid = await _seed_usuario(db_session, "otro@test.com")
        await _seed_asignacion(db_session, uid)
        await _seed_asignacion(db_session, otro_uid)

        headers = {"Authorization": f"Bearer {_docente_token(user_id=uid)}"}
        resp = await client.get(
            "/api/equipos/mis-equipos", headers=headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) == 1
        assert body[0]["usuario_id"] == str(uid)

    async def test_mis_equipos_scoped_to_jwt(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """mis-equipos respeta el user_id del JWT, no datos de body."""
        user_id = uuid4()
        otro_user_id = uuid4()
        uid = await _seed_usuario(db_session, "scope@test.com")
        otro_uid = await _seed_usuario(db_session, "scope2@test.com")
        await _seed_asignacion(db_session, uid)
        await _seed_asignacion(db_session, otro_uid)

        # Token del otro usuario — solo ve sus asignaciones
        headers = {"Authorization": f"Bearer {_docente_token(user_id=otro_uid)}"}
        resp = await client.get(
            "/api/equipos/mis-equipos", headers=headers
        )
        assert resp.status_code == 200
        body = resp.json()
        for entry in body:
            assert entry["usuario_id"] == str(otro_uid)

    # ── GET /api/equipos ──────────────────────────────────────────────

    async def test_equipos_list_returns_all(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GET /api/equipos lista todas las asignaciones del tenant."""
        uid = await _seed_usuario(db_session, "list@test.com")
        await _seed_asignacion(db_session, uid)
        await _seed_asignacion(db_session, uid, rol="TUTOR")

        headers = {"Authorization": f"Bearer {_coord_token()}"}
        resp = await client.get("/api/equipos", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) == 2

    # ── POST /api/equipos/asignacion-masiva ────────────────────────────

    async def test_asignacion_masiva_success(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """POST asignacion-masiva crea N asignaciones."""
        materia_id = await _seed_materia(db_session)
        carrera_id = await _seed_carrera(db_session)
        cohorte_id = await _seed_cohorte(db_session, carrera_id)
        u1 = await _seed_usuario(db_session, "masivo1@test.com")
        u2 = await _seed_usuario(db_session, "masivo2@test.com")

        headers = {"Authorization": f"Bearer {_coord_token()}"}
        resp = await client.post(
            "/api/equipos/asignacion-masiva",
            json={
                "usuario_ids": [str(u1), str(u2)],
                "materia_id": str(materia_id),
                "carrera_id": str(carrera_id),
                "cohorte_id": str(cohorte_id),
                "rol": "PROFESOR",
                "desde": "2024-01-01T00:00:00Z",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) == 2

    async def test_asignacion_masiva_usuario_inexistente_409(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """POST asignacion-masiva con usuario inexistente → 409."""
        materia_id = await _seed_materia(db_session)
        carrera_id = await _seed_carrera(db_session)
        cohorte_id = await _seed_cohorte(db_session, carrera_id)

        headers = {"Authorization": f"Bearer {_coord_token()}"}
        resp = await client.post(
            "/api/equipos/asignacion-masiva",
            json={
                "usuario_ids": [str(uuid4())],
                "materia_id": str(materia_id),
                "carrera_id": str(carrera_id),
                "cohorte_id": str(cohorte_id),
                "rol": "PROFESOR",
                "desde": "2024-01-01T00:00:00Z",
            },
            headers=headers,
        )
        assert resp.status_code == 409

    # ── POST /api/equipos/clonar ──────────────────────────────────────

    async def test_clonar_success(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """POST clonar duplica asignaciones de origen a destino."""
        materia_origen = await _seed_materia(db_session)
        carrera_origen = await _seed_carrera(db_session)
        cohorte_origen = await _seed_cohorte(db_session, carrera_origen)
        materia_destino = await _seed_materia(db_session)
        carrera_destino = await _seed_carrera(db_session)
        cohorte_destino = await _seed_cohorte(db_session, carrera_destino)

        uid = await _seed_usuario(db_session, "clone@test.com")
        await _seed_asignacion(db_session, uid, materia_origen, carrera_origen, cohorte_origen)
        await _seed_asignacion(
            db_session, uid, materia_origen, carrera_origen, cohorte_origen, rol="TUTOR"
        )

        headers = {"Authorization": f"Bearer {_coord_token()}"}
        resp = await client.post(
            "/api/equipos/clonar",
            json={
                "origen_materia_id": str(materia_origen),
                "origen_carrera_id": str(carrera_origen),
                "origen_cohorte_id": str(cohorte_origen),
                "destino_materia_id": str(materia_destino),
                "destino_carrera_id": str(carrera_destino),
                "destino_cohorte_id": str(cohorte_destino),
                "destino_desde": "2024-03-01T00:00:00Z",
            },
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["creadas"] == 2
        assert len(body["asignaciones"]) == 2

    async def test_clonar_origen_inexistente_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """POST clonar con origen sin asignaciones → 404."""
        materia_origen = await _seed_materia(db_session)
        carrera_origen = await _seed_carrera(db_session)
        cohorte_origen = await _seed_cohorte(db_session, carrera_origen)
        materia_destino = await _seed_materia(db_session)
        carrera_destino = await _seed_carrera(db_session)
        cohorte_destino = await _seed_cohorte(db_session, carrera_destino)

        headers = {"Authorization": f"Bearer {_coord_token()}"}
        resp = await client.post(
            "/api/equipos/clonar",
            json={
                "origen_materia_id": str(materia_origen),
                "origen_carrera_id": str(carrera_origen),
                "origen_cohorte_id": str(cohorte_origen),
                "destino_materia_id": str(materia_destino),
                "destino_carrera_id": str(carrera_destino),
                "destino_cohorte_id": str(cohorte_destino),
                "destino_desde": "2024-03-01T00:00:00Z",
            },
            headers=headers,
        )
        assert resp.status_code == 404

    # ── PATCH /api/equipos/vigencia ──────────────────────────────────

    async def test_vigencia_success(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """PATCH vigencia actualiza desde/hasta del equipo."""
        materia_id = await _seed_materia(db_session)
        carrera_id = await _seed_carrera(db_session)
        cohorte_id = await _seed_cohorte(db_session, carrera_id)

        uid = await _seed_usuario(db_session, "vig@test.com")
        for _ in range(3):
            await _seed_asignacion(db_session, uid, materia_id, carrera_id, cohorte_id)

        headers = {"Authorization": f"Bearer {_coord_token()}"}
        resp = await client.patch(
            "/api/equipos/vigencia",
            json={
                "materia_id": str(materia_id),
                "carrera_id": str(carrera_id),
                "cohorte_id": str(cohorte_id),
                "desde": "2024-03-01T00:00:00Z",
                "hasta": "2024-12-31T00:00:00Z",
            },
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["afectadas"] == 3

    async def test_vigencia_sin_asignaciones(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """PATCH vigencia con equipo vacio → 404 (design spec)."""
        materia_id = await _seed_materia(db_session)
        carrera_id = await _seed_carrera(db_session)
        cohorte_id = await _seed_cohorte(db_session, carrera_id)

        headers = {"Authorization": f"Bearer {_coord_token()}"}
        resp = await client.patch(
            "/api/equipos/vigencia",
            json={
                "materia_id": str(materia_id),
                "carrera_id": str(carrera_id),
                "cohorte_id": str(cohorte_id),
                "desde": "2024-03-01T00:00:00Z",
                "hasta": "2024-12-31T00:00:00Z",
            },
            headers=headers,
        )
        assert resp.status_code == 404

    # ── GET /api/equipos/export ───────────────────────────────────────

    async def test_export_csv_format(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GET export retorna CSV con cabeceras en espanol."""
        materia_id = await _seed_materia(db_session)
        carrera_id = await _seed_carrera(db_session)
        cohorte_id = await _seed_cohorte(db_session, carrera_id)

        uid = await _seed_usuario(db_session, "csv@test.com")
        await _seed_asignacion(db_session, uid, materia_id, carrera_id, cohorte_id)

        headers = {"Authorization": f"Bearer {_coord_token()}"}
        resp = await client.get(
            "/api/equipos/export",
            params={
                "materia_id": str(materia_id),
                "carrera_id": str(carrera_id),
                "cohorte_id": str(cohorte_id),
            },
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.headers.get("content-type") == "text/csv; charset=utf-8"
        content = resp.text
        # Cabeceras en espanol (design spec)
        assert "docente" in content
        assert "documento" in content
        assert "rol" in content
        assert "materia" in content
        assert "carrera" in content
        assert "cohorte" in content
        assert "comisiones" in content
        assert "desde" in content
        assert "hasta" in content
        assert "estado_vigencia" in content
        # Al menos una fila de datos
        lines = content.strip().split("\n")
        assert len(lines) >= 2  # header + 1 fila

    async def test_export_empty_equipo(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GET export con equipo vacio retorna CSV solo con cabeceras."""
        materia_id = await _seed_materia(db_session)
        carrera_id = await _seed_carrera(db_session)
        cohorte_id = await _seed_cohorte(db_session, carrera_id)

        headers = {"Authorization": f"Bearer {_coord_token()}"}
        resp = await client.get(
            "/api/equipos/export",
            params={
                "materia_id": str(materia_id),
                "carrera_id": str(carrera_id),
                "cohorte_id": str(cohorte_id),
            },
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.headers.get("content-type") == "text/csv; charset=utf-8"
        # Solo cabeceras
        lines = resp.text.strip().split("\n")
        assert len(lines) == 1

    # ── Audit ─────────────────────────────────────────────────────────

    async def test_audit_asignacion_masiva(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """asignacion-masiva genera ASIGNACION_MODIFICAR en audit log."""
        materia_id = await _seed_materia(db_session)
        carrera_id = await _seed_carrera(db_session)
        cohorte_id = await _seed_cohorte(db_session, carrera_id)
        uid = await _seed_usuario(db_session, "audit@test.com")

        headers = {"Authorization": f"Bearer {_coord_token()}"}
        await client.post(
            "/api/equipos/asignacion-masiva",
            json={
                "usuario_ids": [str(uid)],
                "materia_id": str(materia_id),
                "carrera_id": str(carrera_id),
                "cohorte_id": str(cohorte_id),
                "rol": "PROFESOR",
                "desde": "2024-01-01T00:00:00Z",
            },
            headers=headers,
        )

        # Verificar audit log
        result = await db_session.execute(
            text(
                "SELECT accion, filas_afectadas, materia_id "
                "FROM audit_log "
                "WHERE accion = 'ASIGNACION_MODIFICAR' "
                "ORDER BY fecha_hora DESC LIMIT 1"
            ),
        )
        row = result.fetchone()
        assert row is not None
        assert row[0] == "ASIGNACION_MODIFICAR"
        assert row[1] == 1
        assert str(row[2]) == str(materia_id)
