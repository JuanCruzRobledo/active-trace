"""Tests E2E de integración para el router de analisis (C-11).

Requiere PostgreSQL real (DATABASE_URL_TEST en el entorno).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.enums import OrigenCalificacion
from app.models.tenant import Tenant
from tests.conftest import db_available
from tests.integration.test_analisis_repository import (
    _seed_calificacion,
    _seed_estructura,
    _seed_umbral,
)

pytestmark = [
    pytest.mark.skipif(
        not db_available(),
        reason="Requiere PostgreSQL: definir DATABASE_URL_TEST en el entorno",
    ),
]


# ── Seeds ────────────────────────────────────────────────────────────


async def _seed_alumno_con_calificaciones(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
    materia_id: uuid.UUID,
    cohorte_id: uuid.UUID,
) -> dict:
    """Crea un alumno con calificaciones. Retorna IDs."""
    from app.models.version_padron import VersionPadron
    from app.models.entrada_padron import EntradaPadron
    from app.models.usuario import Usuario

    uid = uuid.uuid4()
    user = Usuario(
        id=uid,
        tenant_id=tenant_id,
        email=f"carlos{uuid.uuid4().hex[:4]}@test.com",
        nombre="Carlos",
        apellidos="Lopez",
        estado="Activo",
    )
    db_session.add(user)
    await db_session.flush()

    vp = VersionPadron(
        tenant_id=tenant_id,
        materia_id=materia_id,
        cohorte_id=cohorte_id,
        cargado_por=uid,
        cargado_at=datetime.now(timezone.utc),
        activa=True,
    )
    db_session.add(vp)
    await db_session.flush()

    ep = EntradaPadron(
        tenant_id=tenant_id,
        version_id=vp.id,
        usuario_id=uid,
        nombre="Carlos",
        apellidos="Lopez",
        email=f"carlos{uuid.uuid4().hex[:4]}@test.com",
        comision="A",
    )
    db_session.add(ep)
    await db_session.flush()

    # Calificaciones: Parcial 1 = 80 (aprobado), Parcial 2 = 40 (desaprobado)
    await _seed_calificacion(
        db_session, tenant_id, ep.id, materia_id, "Parcial 1",
        nota_numerica=Decimal("80"), aprobado=True,
    )
    await _seed_calificacion(
        db_session, tenant_id, ep.id, materia_id, "Parcial 2",
        nota_numerica=Decimal("40"), aprobado=False,
    )

    return {"usuario_id": uid, "entrada_padron_id": ep.id}


async def _seed_admin_usuario(
    db_session: AsyncSession, tenant_id: uuid.UUID
) -> uuid.UUID:
    """Crea un usuario ADMIN con permisos atrasados:ver."""
    from app.models.usuario import Usuario

    uid = uuid.uuid4()
    user = Usuario(
        id=uid,
        tenant_id=tenant_id,
        email=f"admin{uuid.uuid4().hex[:4]}@test.com",
        nombre="Admin",
        apellidos="Test",
        estado="Activo",
    )
    db_session.add(user)
    await db_session.flush()

    # Asignar rol ADMIN + permiso atrasados:ver via asignacion
    from app.models.asignacion import Asignacion
    asignacion = Asignacion(
        tenant_id=tenant_id,
        usuario_id=uid,
        rol="ADMIN",
        desde=datetime.now(timezone.utc),
    )
    db_session.add(asignacion)
    await db_session.flush()
    return uid


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def tenant(db_session: AsyncSession) -> Tenant:
    tid = uuid.uuid4()
    t = Tenant(id=tid, tenant_id=tid, nombre="AnalisisRouterTest")
    db_session.add(t)
    await db_session.flush()
    return t


@pytest_asyncio.fixture
async def setup_data(
    tenant: Tenant, db_session: AsyncSession
) -> dict:
    """Configura estructura + alumno + calificaciones + umbral."""
    est = await _seed_estructura(db_session, tenant.id)
    alumno = await _seed_alumno_con_calificaciones(
        db_session, tenant.id, est["materia"].id, est["cohorte"].id
    )
    await _seed_umbral(db_session, tenant.id, est["materia"].id, umbral_pct=60)
    admin_id = await _seed_admin_usuario(db_session, tenant.id)

    # Seed: Rol ADMIN + Permiso atrasados:ver para este tenant
    from app.models.permiso import Permiso
    from app.models.rol_permiso import RolPermiso
    from app.models.rol import Rol

    rol_admin = Rol(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        codigo="ADMIN",
        nombre="Administrador",
        descripcion="Admin de test",
    )
    db_session.add(rol_admin)
    await db_session.flush()

    permiso_atrasados = Permiso(
        id=uuid.uuid4(),
        codigo="atrasados:ver",
        descripcion="Ver analisis de atrasados",
    )
    db_session.add(permiso_atrasados)
    await db_session.flush()

    rp = RolPermiso(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        rol_id=rol_admin.id,
        permiso_id=permiso_atrasados.id,
    )
    db_session.add(rp)

    await db_session.commit()
    return {
        **est,
        "admin_id": admin_id,
        "alumno_id": alumno["usuario_id"],
        "entrada_padron_id": alumno["entrada_padron_id"],
    }


@pytest_asyncio.fixture
async def auth_headers(
    setup_data: dict, tenant: Tenant, settings: Settings
) -> dict:
    """Crea headers de autenticacion simulando un ADMIN autenticado."""
    import jwt

    from app.core.security import JWT_TYPE_ACCESS

    token = jwt.encode(
        {
            "sub": str(setup_data["admin_id"]),
            "tenant_id": str(tenant.id),
            "roles": ["ADMIN"],
            "type": JWT_TYPE_ACCESS,
            "exp": datetime.now(timezone.utc).timestamp() + 3600,
        },
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


# ── Tests: GET /api/analisis/atrasados ──────────────────────────────


class TestGetAtrasados:
    async def test_devuelve_atrasados(
        self,
        client: AsyncClient,
        setup_data: dict,
        auth_headers: dict,
    ) -> None:
        resp = await client.get(
            "/api/analisis/atrasados",
            params={"materia_id": str(setup_data["materia"].id)},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "alumnos_atrasados" in body
        assert body["total_alumnos"] >= 1

    async def test_sin_auth_devuelve_401(
        self,
        client: AsyncClient,
        setup_data: dict,
    ) -> None:
        resp = await client.get(
            "/api/analisis/atrasados",
            params={"materia_id": str(setup_data["materia"].id)},
        )
        assert resp.status_code == 401

    async def test_materia_inexistente(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ) -> None:
        resp = await client.get(
            "/api/analisis/atrasados",
            params={"materia_id": str(uuid.uuid4())},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_alumnos"] == 0


# ── Tests: GET /api/analisis/ranking ────────────────────────────────


class TestGetRanking:
    async def test_devuelve_ranking(
        self,
        client: AsyncClient,
        setup_data: dict,
        auth_headers: dict,
    ) -> None:
        resp = await client.get(
            "/api/analisis/ranking",
            params={"materia_id": str(setup_data["materia"].id)},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "ranking" in body


# ── Tests: GET /api/analisis/reporte-rapido ──────────────────────────


class TestGetReporteRapido:
    async def test_devuelve_reporte(
        self,
        client: AsyncClient,
        setup_data: dict,
        auth_headers: dict,
    ) -> None:
        resp = await client.get(
            "/api/analisis/reporte-rapido",
            params={"materia_id": str(setup_data["materia"].id)},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "total_alumnos" in body
        assert "porcentaje_aprobacion" in body


# ── Tests: GET /api/analisis/notas-finales ───────────────────────────


class TestGetNotasFinales:
    async def test_devuelve_notas(
        self,
        client: AsyncClient,
        setup_data: dict,
        auth_headers: dict,
    ) -> None:
        resp = await client.get(
            "/api/analisis/notas-finales",
            params={
                "materia_id": str(setup_data["materia"].id),
                "actividades": ["Parcial 1", "Parcial 2"],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "notas" in body


# ── Tests: GET /api/analisis/tps-sin-corregir ────────────────────────


class TestGetTpsSinCorregir:
    async def test_devuelve_pendientes(
        self,
        client: AsyncClient,
        setup_data: dict,
        auth_headers: dict,
    ) -> None:
        resp = await client.get(
            "/api/analisis/tps-sin-corregir",
            params={"materia_id": str(setup_data["materia"].id)},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "pendientes" in body


# ── Tests: GET /api/analisis/monitor-general ─────────────────────────


class TestGetMonitorGeneral:
    async def test_devuelve_monitor(
        self,
        client: AsyncClient,
        setup_data: dict,
        auth_headers: dict,
    ) -> None:
        resp = await client.get(
            "/api/analisis/monitor-general",
            params={"materia_id": str(setup_data["materia"].id)},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "alumnos" in body
        assert "total" in body


# ── Tests: GET /api/analisis/monitor-seguimiento ─────────────────────


class TestGetMonitorSeguimiento:
    async def test_devuelve_monitor_seguimiento(
        self,
        client: AsyncClient,
        setup_data: dict,
        auth_headers: dict,
    ) -> None:
        resp = await client.get(
            "/api/analisis/monitor-seguimiento",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "alumnos" in body
