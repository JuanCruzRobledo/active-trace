"""Tests de integración para el panel de auditoría y métricas (C-19).

Requiere PostgreSQL real (DATABASE_URL_TEST en el entorno).
Cubre: F9.1 (panel de interacciones) y F9.2 (log completo de auditoría).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

import jwt
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.audit_log import AuditLog
from app.models.comunicacion import Comunicacion, EstadoComunicacion
from app.models.materia import Materia
from app.models.tenant import Tenant
from app.models.usuario import Usuario
from tests.conftest import db_available

pytestmark = [
    pytest.mark.skipif(
        not db_available(),
        reason="Requiere PostgreSQL: definir DATABASE_URL_TEST en el entorno",
    ),
]


# ── Helpers ────────────────────────────────────────────────────────────


async def _seed_usuario(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
    nombre: str = "Usuario",
    apellidos: str = "Test",
) -> uuid.UUID:
    """Crea un usuario de prueba con su auth_user. Retorna ``usuario.id``.

    Crea tanto la entrada en ``users`` (tabla de auth) como en ``usuario``
    (tabla de dominio), usando el **mismo UUID** para ambas y linkeando
    ``usuario.auth_user_id = usuario.id``.

    Esto permite que los JOINs ``AuditLog.actor_id == Usuario.auth_user_id``
    funcionen (ambos referencian el mismo UUID en ``users.id``).
    """
    uid = uuid.uuid4()
    # Crear auth user en tabla `users` (mismo UUID que usuario.id)
    stmt = text(
        "INSERT INTO users (id, email, password_hash, is_active, totp_enabled, tenant_id, created_at, updated_at) "
        "VALUES (:id, :email, :pwd, :active, :totp, :tid, NOW(), NOW())"
    )
    await db_session.execute(
        stmt,
        {
            "id": uid,
            "email": f"{nombre.lower()}{uuid.uuid4().hex[:4]}@test.com",
            "pwd": "argon2_placeholder",
            "active": True,
            "totp": False,
            "tid": tenant_id,
        },
    )
    # Crear registro en tabla `usuario` (dominio)
    user = Usuario(
        id=uid,
        auth_user_id=uid,  # mismo UUID que users.id
        tenant_id=tenant_id,
        email=f"{nombre.lower()}{uuid.uuid4().hex[:4]}@test.com",
        nombre=nombre,
        apellidos=apellidos,
        estado="Activo",
    )
    db_session.add(user)
    await db_session.flush()
    return uid


async def _seed_materia(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
    nombre: str = "Matemática",
    codigo: str = "MAT",
) -> Materia:
    """Crea una materia de prueba. Retorna la instancia."""
    mid = uuid.uuid4()
    materia = Materia(
        id=mid,
        tenant_id=tenant_id,
        codigo=codigo,
        nombre=nombre,
        estado="Activa",
    )
    db_session.add(materia)
    await db_session.flush()
    return materia


async def _seed_audit_log(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
    actor_id: uuid.UUID,
    accion: str,
    materia_id: uuid.UUID | None = None,
    fecha_hora: datetime | None = None,
    ip: str | None = None,
) -> AuditLog:
    """Crea un registro de auditoría."""
    log = AuditLog(
        tenant_id=tenant_id,
        actor_id=actor_id,
        accion=accion,
        materia_id=materia_id,
        detalle={"test": True},
        ip=ip or "127.0.0.1",
        filas_afectadas=1,
        fecha_hora=fecha_hora or datetime.now(timezone.utc),
    )
    db_session.add(log)
    await db_session.flush()
    return log


async def _seed_comunicacion(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
    enviado_por_id: uuid.UUID,
    materia_id: uuid.UUID | None = None,
    estado: EstadoComunicacion = EstadoComunicacion.Enviado,
) -> Comunicacion:
    """Crea una comunicación de prueba."""
    com = Comunicacion(
        tenant_id=tenant_id,
        enviado_por_id=enviado_por_id,
        materia_id=materia_id,
        destinatario=f"alumno{uuid.uuid4().hex[:4]}@test.com",
        asunto="Test",
        cuerpo="Cuerpo del mensaje de prueba",
        estado=estado,
    )
    db_session.add(com)
    await db_session.flush()
    return com


async def _setup_permiso_auditoria(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    """Crea el permiso ``auditoria:ver`` y lo asigna al rol ADMIN."""
    from app.models.permiso import Permiso
    from app.models.rol import Rol
    from app.models.rol_permiso import RolPermiso

    # Crear permiso
    perm = Permiso(
        id=uuid.uuid4(),
        codigo="auditoria:ver",
        descripcion="Ver panel de auditoría",
    )
    db_session.add(perm)
    await db_session.flush()

    # Crear rol ADMIN y asignar permiso
    rol = Rol(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        codigo="ADMIN",
        nombre="Administrador",
        descripcion="Admin de test",
    )
    db_session.add(rol)
    await db_session.flush()

    rp = RolPermiso(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        rol_id=rol.id,
        permiso_id=perm.id,
    )
    db_session.add(rp)

    # Crear rol COORDINADOR y asignar permiso
    rol_coord = Rol(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        codigo="COORDINADOR",
        nombre="Coordinador",
        descripcion="Coordinador de test",
    )
    db_session.add(rol_coord)
    await db_session.flush()

    rp_coord = RolPermiso(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        rol_id=rol_coord.id,
        permiso_id=perm.id,
    )
    db_session.add(rp_coord)

    # Crear rol FINANZAS (sin permiso auditoria:ver para probar 403)
    rol_fin = Rol(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        codigo="FINANZAS",
        nombre="Finanzas",
        descripcion="Finanzas de test",
    )
    db_session.add(rol_fin)

    await db_session.flush()


def _make_admin_token(
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    settings: Settings,
) -> dict:
    """Crea headers de autenticación para ADMIN."""
    from app.core.security import JWT_TYPE_ACCESS

    token = jwt.encode(
        {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "roles": ["ADMIN"],
            "type": JWT_TYPE_ACCESS,
            "exp": datetime.now(timezone.utc).timestamp() + 3600,
        },
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def _make_coordinador_token(
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    settings: Settings,
) -> dict:
    """Crea headers de autenticación para COORDINADOR."""
    from app.core.security import JWT_TYPE_ACCESS

    token = jwt.encode(
        {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "roles": ["COORDINADOR"],
            "type": JWT_TYPE_ACCESS,
            "exp": datetime.now(timezone.utc).timestamp() + 3600,
        },
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def _make_finanzas_token(
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    settings: Settings,
) -> dict:
    """Crea headers de autenticación para FINANZAS (sin permisos de auditoría)."""
    from app.core.security import JWT_TYPE_ACCESS

    token = jwt.encode(
        {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "roles": ["FINANZAS"],
            "type": JWT_TYPE_ACCESS,
            "exp": datetime.now(timezone.utc).timestamp() + 3600,
        },
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


# ── Fixtures ───────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def tenant(db_session: AsyncSession) -> Tenant:
    tid = uuid.uuid4()
    t = Tenant(id=tid, tenant_id=tid, nombre="AuditoriaTest")
    db_session.add(t)
    await db_session.flush()
    return t


@pytest_asyncio.fixture
async def setup_data(
    tenant: Tenant,
    db_session: AsyncSession,
) -> dict:
    """Configura datos base para los tests: tenant, usuários, materias, permisos."""
    ten_id = tenant.id

    # Usuarios
    admin_id = await _seed_usuario(db_session, ten_id, "Admin", "Test")
    coord_id = await _seed_usuario(db_session, ten_id, "Coordi", "Nador")
    finanzas_id = await _seed_usuario(db_session, ten_id, "Finan", "Zas")

    # Materias
    materia_a = await _seed_materia(db_session, ten_id, "Matemática", "MAT")
    materia_b = await _seed_materia(db_session, ten_id, "Lengua", "LEN")

    # Asignar COORDINADOR solo a materia_a (scope propio)
    from app.models.asignacion import Asignacion

    asig = Asignacion(
        tenant_id=ten_id,
        usuario_id=coord_id,
        materia_id=materia_a.id,
        rol="COORDINADOR",
        desde=datetime.now(timezone.utc),
    )
    db_session.add(asig)

    # Asignar ADMIN (sin materia_id — ve todo)
    asig_admin = Asignacion(
        tenant_id=ten_id,
        usuario_id=admin_id,
        rol="ADMIN",
        desde=datetime.now(timezone.utc),
    )
    db_session.add(asig_admin)

    # Permisos
    await _setup_permiso_auditoria(db_session, ten_id)
    await db_session.commit()

    return {
        "tenant_id": ten_id,
        "admin_id": admin_id,
        "coord_id": coord_id,
        "finanzas_id": finanzas_id,
        "materia_a": materia_a,
        "materia_b": materia_b,
    }


@pytest_asyncio.fixture
async def seed_audit_logs(
    setup_data: dict,
    db_session: AsyncSession,
) -> None:
    """Crea registros de auditoría para los tests."""
    ten_id = setup_data["tenant_id"]
    admin_id = setup_data["admin_id"]
    coord_id = setup_data["coord_id"]
    mat_a = setup_data["materia_a"].id
    mat_b = setup_data["materia_b"].id

    now = datetime.now(timezone.utc)
    # admin: 5 acciones en materia_a, 3 en materia_b
    for i in range(5):
        await _seed_audit_log(
            db_session, ten_id, admin_id, "USUARIO_CREAR", mat_a,
            fecha_hora=now,
        )
    for i in range(3):
        await _seed_audit_log(
            db_session, ten_id, admin_id, "USUARIO_CREAR", mat_b,
            fecha_hora=now,
        )
    # coord: 2 acciones en materia_a
    for i in range(2):
        await _seed_audit_log(
            db_session, ten_id, coord_id, "MATERIA_EDITAR", mat_a,
            fecha_hora=now,
        )

    await db_session.commit()


@pytest_asyncio.fixture
async def seed_comunicaciones(
    setup_data: dict,
    db_session: AsyncSession,
) -> None:
    """Crea comunicaciones para los tests."""
    ten_id = setup_data["tenant_id"]
    admin_id = setup_data["admin_id"]
    mat_a = setup_data["materia_a"].id
    mat_b = setup_data["materia_b"].id

    # admin: 5 enviadas en materia_a, 2 fallidas en materia_b
    for i in range(5):
        await _seed_comunicacion(
            db_session, ten_id, admin_id, mat_a, EstadoComunicacion.Enviado,
        )
    for i in range(2):
        await _seed_comunicacion(
            db_session, ten_id, admin_id, mat_b, EstadoComunicacion.Error,
        )

    await db_session.commit()


@pytest_asyncio.fixture
async def auth_admin(setup_data: dict, settings: Settings) -> dict:
    return _make_admin_token(setup_data["admin_id"], setup_data["tenant_id"], settings)


@pytest_asyncio.fixture
async def auth_coordinador(setup_data: dict, settings: Settings) -> dict:
    return _make_coordinador_token(
        setup_data["coord_id"], setup_data["tenant_id"], settings
    )


@pytest_asyncio.fixture
async def auth_finanzas(setup_data: dict, settings: Settings) -> dict:
    return _make_finanzas_token(
        setup_data["finanzas_id"], setup_data["tenant_id"], settings
    )


# ══════════════════════════════════════════════════════════════════════
# Tests: GET /api/auditoria/acciones-por-dia (task 4.1)
# ══════════════════════════════════════════════════════════════════════


class TestAccionesPorDia:
    async def test_sin_filtros(
        self,
        client: AsyncClient,
        seed_audit_logs: None,
        auth_admin: dict,
    ) -> None:
        resp = await client.get(
            "/api/auditoria/acciones-por-dia",
            headers=auth_admin,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) >= 1
        assert "fecha" in body[0]
        assert "total" in body[0]
        assert body[0]["total"] >= 10  # 5+3+2

    async def test_con_rango_fechas(
        self,
        client: AsyncClient,
        seed_audit_logs: None,
        auth_admin: dict,
    ) -> None:
        today = date.today()
        resp = await client.get(
            "/api/auditoria/acciones-por-dia",
            params={"fecha_desde": today.isoformat(), "fecha_hasta": today.isoformat()},
            headers=auth_admin,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) >= 1

    async def test_con_materia_id(
        self,
        client: AsyncClient,
        seed_audit_logs: None,
        auth_admin: dict,
        setup_data: dict,
    ) -> None:
        resp = await client.get(
            "/api/auditoria/acciones-por-dia",
            params={"materia_id": str(setup_data["materia_a"].id)},
            headers=auth_admin,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) >= 1
        assert body[0]["total"] >= 7  # 5+2 de materia_a

    async def test_scope_propio_coordinador(
        self,
        client: AsyncClient,
        seed_audit_logs: None,
        auth_coordinador: dict,
    ) -> None:
        resp = await client.get(
            "/api/auditoria/acciones-por-dia",
            headers=auth_coordinador,
        )
        assert resp.status_code == 200
        body = resp.json()
        # coord solo ve materia_a: 5 admin + 2 coord = 7
        total = sum(item["total"] for item in body)
        assert total == 7

    async def test_sin_auth_devuelve_401(
        self,
        client: AsyncClient,
    ) -> None:
        resp = await client.get("/api/auditoria/acciones-por-dia")
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════
# Tests: GET /api/auditoria/comunicaciones-por-docente (task 4.2)
# ══════════════════════════════════════════════════════════════════════


class TestComunicacionesPorDocente:
    async def test_distribucion_estados(
        self,
        client: AsyncClient,
        seed_comunicaciones: None,
        auth_admin: dict,
    ) -> None:
        resp = await client.get(
            "/api/auditoria/comunicaciones-por-docente",
            headers=auth_admin,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) >= 1
        item = body[0]
        assert "usuario_id" in item
        assert "nombre" in item
        assert item["OK"] >= 5
        assert item["Fallido"] >= 2

    async def test_filtro_materia(
        self,
        client: AsyncClient,
        seed_comunicaciones: None,
        auth_admin: dict,
        setup_data: dict,
    ) -> None:
        resp = await client.get(
            "/api/auditoria/comunicaciones-por-docente",
            params={"materia_id": str(setup_data["materia_a"].id)},
            headers=auth_admin,
        )
        assert resp.status_code == 200
        body = resp.json()
        total_ok = sum(item["OK"] for item in body)
        assert total_ok == 5  # solo las de materia_a

    async def test_scope_propio(
        self,
        client: AsyncClient,
        seed_comunicaciones: None,
        auth_coordinador: dict,
    ) -> None:
        resp = await client.get(
            "/api/auditoria/comunicaciones-por-docente",
            headers=auth_coordinador,
        )
        assert resp.status_code == 200
        body = resp.json()
        total_ok = sum(item["OK"] for item in body)
        assert total_ok == 5  # coord solo ve materia_a

    async def test_sin_auth_devuelve_401(
        self,
        client: AsyncClient,
    ) -> None:
        resp = await client.get("/api/auditoria/comunicaciones-por-docente")
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════
# Tests: GET /api/auditoria/interacciones-por-docente-materia (task 4.3)
# ══════════════════════════════════════════════════════════════════════


class TestInteraccionesPorDocenteMateria:
    async def test_agregacion_por_accion(
        self,
        client: AsyncClient,
        seed_audit_logs: None,
        auth_admin: dict,
    ) -> None:
        resp = await client.get(
            "/api/auditoria/interacciones-por-docente-materia",
            headers=auth_admin,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) >= 1
        item = body[0]
        assert "usuario_id" in item
        assert "nombre" in item
        assert "materia_id" in item
        assert "materia_nombre" in item
        assert "acciones" in item
        assert "total" in item

    async def test_con_fechas(
        self,
        client: AsyncClient,
        seed_audit_logs: None,
        auth_admin: dict,
    ) -> None:
        today = date.today()
        resp = await client.get(
            "/api/auditoria/interacciones-por-docente-materia",
            params={"fecha_desde": today.isoformat(), "fecha_hasta": today.isoformat()},
            headers=auth_admin,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) >= 1

    async def test_scope_propio(
        self,
        client: AsyncClient,
        seed_audit_logs: None,
        auth_coordinador: dict,
    ) -> None:
        resp = await client.get(
            "/api/auditoria/interacciones-por-docente-materia",
            headers=auth_coordinador,
        )
        assert resp.status_code == 200
        body = resp.json()
        # coord solo ve materia_a: todos los items deben ser de materia_a
        for item in body:
            assert item["materia_nombre"] == "Matemática"
        total = sum(item["total"] for item in body)
        assert total == 7  # 5 admin + 2 coord en materia_a

    async def test_sin_auth_devuelve_401(
        self,
        client: AsyncClient,
    ) -> None:
        resp = await client.get("/api/auditoria/interacciones-por-docente-materia")
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════
# Tests: GET /api/auditoria/ultimas-acciones (task 4.4)
# ══════════════════════════════════════════════════════════════════════


class TestUltimasAcciones:
    async def test_default_limit(
        self,
        client: AsyncClient,
        seed_audit_logs: None,
        auth_admin: dict,
    ) -> None:
        resp = await client.get(
            "/api/auditoria/ultimas-acciones",
            headers=auth_admin,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) == 10  # 10 audit logs creados

    async def test_limit_explicito(
        self,
        client: AsyncClient,
        seed_audit_logs: None,
        auth_admin: dict,
    ) -> None:
        resp = await client.get(
            "/api/auditoria/ultimas-acciones",
            params={"limit": 3},
            headers=auth_admin,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 3

    async def test_techo_duro_1000(
        self,
        client: AsyncClient,
        seed_audit_logs: None,
        auth_admin: dict,
    ) -> None:
        # Validar que el endpoint acepta limit=1000 (no explota)
        resp = await client.get(
            "/api/auditoria/ultimas-acciones",
            params={"limit": 1000},
            headers=auth_admin,
        )
        assert resp.status_code == 200

    async def test_limit_excede_techo(
        self,
        client: AsyncClient,
        seed_audit_logs: None,
        auth_admin: dict,
    ) -> None:
        # El schema valida con le=1000, así que 1001 debe dar 422
        resp = await client.get(
            "/api/auditoria/ultimas-acciones",
            params={"limit": 1001},
            headers=auth_admin,
        )
        assert resp.status_code == 422

    async def test_scope_propio(
        self,
        client: AsyncClient,
        seed_audit_logs: None,
        auth_coordinador: dict,
    ) -> None:
        resp = await client.get(
            "/api/auditoria/ultimas-acciones",
            headers=auth_coordinador,
        )
        assert resp.status_code == 200
        body = resp.json()
        # coord solo ve materia_a: 7 registros
        assert len(body) == 7

    async def test_sin_auth_devuelve_401(
        self,
        client: AsyncClient,
    ) -> None:
        resp = await client.get("/api/auditoria/ultimas-acciones")
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════
# Tests: GET /api/auditoria/log (task 4.5)
# ══════════════════════════════════════════════════════════════════════


class TestLogAuditoria:
    async def test_paginacion(
        self,
        client: AsyncClient,
        seed_audit_logs: None,
        auth_admin: dict,
    ) -> None:
        resp = await client.get(
            "/api/auditoria/log",
            params={"offset": 0, "limit": 5},
            headers=auth_admin,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert "offset" in body
        assert "limit" in body
        assert len(body["items"]) == 5
        assert body["total"] == 10
        assert body["offset"] == 0
        assert body["limit"] == 5

    async def test_filtros_combinables(
        self,
        client: AsyncClient,
        seed_audit_logs: None,
        auth_admin: dict,
        setup_data: dict,
    ) -> None:
        resp = await client.get(
            "/api/auditoria/log",
            params={
                "materia_id": str(setup_data["materia_b"].id),
                "accion": "USUARIO_CREAR",
            },
            headers=auth_admin,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 3  # 3 USUARIO_CREAR en materia_b
        assert len(body["items"]) == 3

    async def test_acceso_admin_ok(
        self,
        client: AsyncClient,
        seed_audit_logs: None,
        auth_admin: dict,
    ) -> None:
        resp = await client.get(
            "/api/auditoria/log",
            headers=auth_admin,
        )
        assert resp.status_code == 200

    async def test_acceso_coordinador_403(
        self,
        client: AsyncClient,
        seed_audit_logs: None,
        auth_coordinador: dict,
    ) -> None:
        resp = await client.get(
            "/api/auditoria/log",
            headers=auth_coordinador,
        )
        assert resp.status_code == 403

    async def test_acceso_finanzas_403(
        self,
        client: AsyncClient,
        seed_audit_logs: None,
        auth_finanzas: dict,
    ) -> None:
        resp = await client.get(
            "/api/auditoria/log",
            headers=auth_finanzas,
        )
        assert resp.status_code == 403

    async def test_sin_auth_devuelve_401(
        self,
        client: AsyncClient,
    ) -> None:
        resp = await client.get("/api/auditoria/log")
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════
# Tests: Scope propio COORDINADOR (task 4.6)
# ══════════════════════════════════════════════════════════════════════


class TestScopePropio:
    """Verifica que COORDINADOR solo ve datos de sus materias asignadas."""

    async def test_coordinador_solo_ve_su_materia(
        self,
        client: AsyncClient,
        setup_data: dict,
        db_session: AsyncSession,
        seed_audit_logs: None,
        auth_coordinador: dict,
    ) -> None:
        """Crea datos en dos materias, coord solo ve la suya."""
        ten_id = setup_data["tenant_id"]
        admin_id = setup_data["admin_id"]
        mat_b = setup_data["materia_b"].id

        # Datos extras SOLO en materia_b (coord tiene scope en materia_a, NO debería ver estos)
        await _seed_audit_log(db_session, ten_id, admin_id, "USUARIO_CREAR", mat_b)
        await _seed_audit_log(db_session, ten_id, admin_id, "USUARIO_CREAR", mat_b)
        await db_session.commit()

        # Verificar que coord solo ve materia_a (7 del seed_audit_logs)
        resp = await client.get(
            "/api/auditoria/acciones-por-dia",
            headers=auth_coordinador,
        )
        assert resp.status_code == 200
        body = resp.json()
        total = sum(item["total"] for item in body)
        assert total == 7  # 5 admin + 2 coord en materia_a del seed_audit_logs
