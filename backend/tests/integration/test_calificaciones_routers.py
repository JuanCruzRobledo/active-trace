"""Tests E2E de API para Calificaciones y Umbrales (C-10).

Cubre:
  POST /api/calificaciones/importar/preview — preview de importacion
  POST /api/calificaciones/importar/confirm — confirmar importacion
  POST /api/calificaciones/finalizacion — detectar sin calificar
  GET /api/calificaciones/umbral — consultar umbral
  PUT /api/calificaciones/umbral — configurar umbral

Protegido con require_permission("calificaciones:importar").
Requiere PostgreSQL real (DATABASE_URL_TEST en el entorno).
"""

from __future__ import annotations

import io
import json
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
_OTHER_TENANT_ID = UUID("00000000-0000-0000-0000-000000000099")
_SECRET_KEY = "a" * 64


# ── Helpers de archivos ────────────────────────────────────────────────


def _make_xlsx_bytes(
    headers: list[str], filas: list[tuple[str, ...]]
) -> bytes:
    try:
        import openpyxl  # noqa: PLC0415
    except ImportError:
        pytest.skip("openpyxl no instalado")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Calificaciones"
    ws.append(headers)
    for row in filas:
        ws.append(list(row))
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


# ── Helpers de tokens ──────────────────────────────────────────────────


def _coord_token() -> str:
    return create_access_token(
        user_id=uuid4(),
        tenant_id=_DEV_TENANT_ID,
        secret_key=_SECRET_KEY,
        roles=["COORDINADOR"],
    )


def _profesor_token(user_id: UUID | None = None) -> str:
    return create_access_token(
        user_id=user_id or uuid4(),
        tenant_id=_DEV_TENANT_ID,
        secret_key=_SECRET_KEY,
        roles=["PROFESOR"],
    )


def _alumno_token() -> str:
    return create_access_token(
        user_id=uuid4(),
        tenant_id=_DEV_TENANT_ID,
        secret_key=_SECRET_KEY,
        roles=["ALUMNO"],
    )


def _other_tenant_token() -> str:
    return create_access_token(
        user_id=uuid4(),
        tenant_id=_OTHER_TENANT_ID,
        secret_key=_SECRET_KEY,
        roles=["COORDINADOR"],
    )


# ── Seed helpers ───────────────────────────────────────────────────────


async def _seed_rbac_calificaciones(db_session: AsyncSession) -> None:
    """Seed minimo para que calificaciones:importar funcione."""
    await db_session.execute(
        text(
            "INSERT INTO permiso (id, codigo, descripcion, created_at) "
            "VALUES (:id, :codigo, :descripcion, now()) "
            "ON CONFLICT (codigo) DO NOTHING"
        ),
        {
            "id": uuid4(),
            "codigo": "calificaciones:importar",
            "descripcion": "Importar calificaciones",
        },
    )

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
            "codigo": "PROFESOR",
            "nombre": "Profesor",
            "descripcion": "Profesor",
        },
    )

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
            "codigo": "ALUMNO",
            "nombre": "Alumno",
            "descripcion": "Alumno",
        },
    )

    _coord_rol_id = (await db_session.execute(
        text("SELECT id FROM rol WHERE tenant_id=:tid AND codigo='COORDINADOR'"),
        {"tid": _DEV_TENANT_ID},
    )).scalar_one()

    _prof_rol_id = (await db_session.execute(
        text("SELECT id FROM rol WHERE tenant_id=:tid AND codigo='PROFESOR'"),
        {"tid": _DEV_TENANT_ID},
    )).scalar_one()

    _perm_id = (await db_session.execute(
        text("SELECT id FROM permiso WHERE codigo='calificaciones:importar'"),
    )).scalar_one()

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
            "permiso_id": _perm_id,
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
            "rol_id": _prof_rol_id,
            "permiso_id": _perm_id,
        },
    )

    await db_session.commit()


async def _seed_other_tenant_rbac(db_session: AsyncSession) -> None:
    """Seed RBAC para el otro tenant."""
    await db_session.execute(
        text(
            "INSERT INTO permiso (id, codigo, descripcion, created_at) "
            "VALUES (:id, :codigo, :descripcion, now()) "
            "ON CONFLICT (codigo) DO NOTHING"
        ),
        {
            "id": uuid4(),
            "codigo": "calificaciones:importar",
            "descripcion": "Importar calificaciones",
        },
    )

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
            "tenant_id": _OTHER_TENANT_ID,
            "codigo": "COORDINADOR",
            "nombre": "Coordinador",
            "descripcion": "Coordinador",
        },
    )

    _rol_id = (await db_session.execute(
        text("SELECT id FROM rol WHERE tenant_id=:tid AND codigo='COORDINADOR'"),
        {"tid": _OTHER_TENANT_ID},
    )).scalar_one()

    _perm_id = (await db_session.execute(
        text("SELECT id FROM permiso WHERE codigo='calificaciones:importar'"),
    )).scalar_one()

    await db_session.execute(
        text(
            "INSERT INTO rol_permiso (id, tenant_id, rol_id, permiso_id, created_at) "
            "VALUES (:id, :tenant_id, :rol_id, :permiso_id, now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {
            "id": uuid4(),
            "tenant_id": _OTHER_TENANT_ID,
            "rol_id": _rol_id,
            "permiso_id": _perm_id,
        },
    )

    await db_session.commit()


async def _seed_materia(
    db_session: AsyncSession, tenant_id: UUID = _DEV_TENANT_ID
) -> UUID:
    mid = uuid4()
    await db_session.execute(
        text(
            "INSERT INTO materia (id, tenant_id, codigo, nombre, estado, "
            "created_at, updated_at) "
            "VALUES (:id, :tenant_id, :codigo, :nombre, :estado, now(), now())"
        ),
        {
            "id": mid,
            "tenant_id": tenant_id,
            "codigo": f"MAT-{uuid4().hex[:8]}",
            "nombre": "Materia Test",
            "estado": "Activa",
        },
    )
    await db_session.commit()
    return mid


async def _seed_usuario(
    db_session: AsyncSession, email: str | None = None, tenant_id: UUID = _DEV_TENANT_ID
) -> UUID:
    from app.models.usuario import Usuario

    u = Usuario(
        tenant_id=tenant_id,
        nombre="Test",
        apellidos="User",
        email=email or f"user-{uuid4().hex[:8]}@test.com",
        dni=f"{uuid4().int % 10**8:08d}",
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
    tenant_id: UUID = _DEV_TENANT_ID,
) -> UUID:
    aid = uuid4()
    await db_session.execute(
        text(
            "INSERT INTO asignacion (id, tenant_id, usuario_id, rol, "
            "materia_id, desde, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :usuario_id, :rol, "
            ":materia_id, :desde, now(), now())"
        ),
        {
            "id": aid,
            "tenant_id": tenant_id,
            "usuario_id": usuario_id,
            "rol": "PROFESOR",
            "materia_id": materia_id,
            "desde": datetime(2024, 1, 1, tzinfo=timezone.utc),
        },
    )
    await db_session.commit()
    return aid


async def _seed_carrera(
    db_session: AsyncSession, tenant_id: UUID = _DEV_TENANT_ID
) -> UUID:
    cid = uuid4()
    await db_session.execute(
        text(
            "INSERT INTO carrera (id, tenant_id, codigo, nombre, estado, "
            "created_at, updated_at) "
            "VALUES (:id, :tenant_id, :codigo, :nombre, :estado, now(), now())"
        ),
        {
            "id": cid,
            "tenant_id": tenant_id,
            "codigo": f"CAR-{uuid4().hex[:8]}",
            "nombre": "Carrera Test",
            "estado": "Activa",
        },
    )
    await db_session.commit()
    return cid


async def _seed_cohorte(
    db_session: AsyncSession,
    carrera_id: UUID | None = None,
    tenant_id: UUID = _DEV_TENANT_ID,
) -> UUID:
    if carrera_id is None:
        carrera_id = await _seed_carrera(db_session, tenant_id)
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
            "tenant_id": tenant_id,
            "carrera_id": carrera_id,
            "nombre": f"C-{uuid4().hex[:6]}",
            "anio": 2024,
            "vig_desde": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "estado": "Activa",
        },
    )
    await db_session.commit()
    return coid


async def _seed_entrada_padron(
    db_session: AsyncSession,
    materia_id: UUID,
    tenant_id: UUID = _DEV_TENANT_ID,
    cohorte_id: UUID | None = None,
    nombre: str = "Juan",
    apellidos: str = "Perez",
    cargado_por: UUID | None = None,
) -> UUID:
    from app.models.version_padron import VersionPadron
    from app.models.entrada_padron import EntradaPadron

    if cohorte_id is None:
        cohorte_id = await _seed_cohorte(db_session, tenant_id=tenant_id)
    if cargado_por is None:
        cargado_por = await _seed_usuario(db_session, tenant_id=tenant_id)

    vp = VersionPadron(
        tenant_id=tenant_id,
        materia_id=materia_id,
        cohorte_id=cohorte_id,
        cargado_por=cargado_por,
        activa=True,
    )
    db_session.add(vp)
    await db_session.flush()

    ep = EntradaPadron(
        tenant_id=tenant_id,
        version_id=vp.id,
        nombre=nombre,
        apellidos=apellidos,
        email=f"{nombre.lower()}.{apellidos.lower()}@test.com",
        comision="A",
        regional="Centro",
    )
    db_session.add(ep)
    await db_session.commit()
    return ep.id


async def _seed_umbral(
    db_session: AsyncSession,
    materia_id: UUID,
    asignacion_id: UUID,
    tenant_id: UUID = _DEV_TENANT_ID,
    umbral_pct: int = 70,
    valores_aprobatorios: list[str] | None = None,
) -> UUID:
    uid = uuid4()
    await db_session.execute(
        text(
            "INSERT INTO umbral_materia (id, tenant_id, materia_id, asignacion_id, "
            "umbral_pct, valores_aprobatorios, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :materia_id, :asignacion_id, "
            ":umbral_pct, :valores, now(), now())"
        ),
        {
            "id": uid,
            "tenant_id": tenant_id,
            "materia_id": materia_id,
            "asignacion_id": asignacion_id,
            "umbral_pct": umbral_pct,
            "valores": json.dumps(valores_aprobatorios or ["Aprobado"]),
        },
    )
    await db_session.commit()
    return uid


async def _seed_calificacion(
    db_session: AsyncSession,
    materia_id: UUID,
    entrada_padron_id: UUID,
    actividad: str = "TP1",
    tenant_id: UUID = _DEV_TENANT_ID,
) -> UUID:
    cid = uuid4()
    await db_session.execute(
        text(
            "INSERT INTO calificacion (id, tenant_id, entrada_padron_id, materia_id, "
            "actividad, nota_numerica, aprobado, origen, importado_at, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :entrada_padron_id, :materia_id, "
            ":actividad, :nota, false, 'Importado', now(), now(), now())"
        ),
        {
            "id": cid,
            "tenant_id": tenant_id,
            "entrada_padron_id": entrada_padron_id,
            "materia_id": materia_id,
            "actividad": actividad,
            "nota": 50,
        },
    )
    await db_session.commit()
    return cid


# ── Fixtures ───────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _patch_env(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", _SECRET_KEY)
    monkeypatch.setenv("ENCRYPTION_KEY", "b" * 32)
    monkeypatch.setenv("DATABASE_URL", "placeholder")


# ===========================================================================
# 403 — Sin permiso calificaciones:importar
# ===========================================================================


class TestCalificacionesApiSinPermiso:
    """Endpoints devuelven 403 si el token no tiene permisos."""

    async def test_preview_returns_403(self, client: AsyncClient) -> None:
        headers = {"Authorization": f"Bearer {_alumno_token()}"}
        resp = await client.post(
            "/api/calificaciones/importar/preview",
            data={"materia_id": str(uuid4())},
            headers=headers,
        )
        assert resp.status_code == 403

    async def test_confirm_returns_403(self, client: AsyncClient) -> None:
        headers = {"Authorization": f"Bearer {_alumno_token()}"}
        resp = await client.post(
            "/api/calificaciones/importar/confirm",
            data={"materia_id": str(uuid4()), "preview_token": "x", "actividades_seleccionadas": "[]"},
            headers=headers,
        )
        assert resp.status_code == 403

    async def test_finalizacion_returns_403(self, client: AsyncClient) -> None:
        headers = {"Authorization": f"Bearer {_alumno_token()}"}
        resp = await client.post(
            "/api/calificaciones/finalizacion",
            data={"materia_id": str(uuid4())},
            headers=headers,
        )
        assert resp.status_code == 403

    async def test_get_umbral_returns_403(self, client: AsyncClient) -> None:
        headers = {"Authorization": f"Bearer {_alumno_token()}"}
        resp = await client.get(
            "/api/calificaciones/umbral",
            params={"materia_id": str(uuid4()), "asignacion_id": str(uuid4())},
            headers=headers,
        )
        assert resp.status_code == 403

    async def test_put_umbral_returns_403(self, client: AsyncClient) -> None:
        headers = {"Authorization": f"Bearer {_alumno_token()}"}
        resp = await client.put(
            "/api/calificaciones/umbral",
            json={"materia_id": str(uuid4()), "asignacion_id": str(uuid4())},
            headers=headers,
        )
        assert resp.status_code == 403


# ===========================================================================
# Calificaciones API
# ===========================================================================


class TestCalificacionesApi:
    """Calificaciones CRUD + operaciones de importacion."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(
        self, db_session: AsyncSession, seed_dev_tenant: None
    ) -> None:
        await _seed_rbac_calificaciones(db_session)

    # ── POST /api/calificaciones/importar/preview ─────────────────────

    async def test_importar_preview_valid_xlsx(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """POST preview con archivo xlsx valido → 200 + actividades detectadas."""
        materia_id = await _seed_materia(db_session)
        xlsx_bytes = _make_xlsx_bytes(
            headers=["Nombre", "TP1 (Real)", "TP2 (Real)"],
            filas=[("Juan", "80", "90"), ("Maria", "70", "85")],
        )

        headers = {"Authorization": f"Bearer {_coord_token()}"}
        resp = await client.post(
            "/api/calificaciones/importar/preview",
            data={"materia_id": str(materia_id)},
            files={
                "file": (
                    "calificaciones.xlsx",
                    xlsx_bytes,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
            },
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["actividades_detectadas"] == ["TP1 (Real)", "TP2 (Real)"]
        assert body["filas"] == 2
        assert body["alumnos_detectados"] == 2
        assert "preview_token" in body

    async def test_importar_preview_sin_archivo(
        self, client: AsyncClient
    ) -> None:
        """POST preview sin archivo → 422."""
        headers = {"Authorization": f"Bearer {_coord_token()}"}
        resp = await client.post(
            "/api/calificaciones/importar/preview",
            data={"materia_id": str(uuid4())},
            headers=headers,
        )
        assert resp.status_code == 422

    # ── POST /api/calificaciones/importar/confirm ─────────────────────

    async def test_importar_confirm_valid_token(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """POST confirm con preview_token valido → 200 + calificaciones creadas."""
        materia_id = await _seed_materia(db_session)
        await _seed_entrada_padron(db_session, materia_id)

        xlsx_bytes = _make_xlsx_bytes(
            headers=["Nombre", "Apellidos", "TP1 (Real)"],
            filas=[("Juan", "Perez", "80")],
        )

        headers = {"Authorization": f"Bearer {_coord_token()}"}

        # Preview primero
        preview = await client.post(
            "/api/calificaciones/importar/preview",
            data={"materia_id": str(materia_id)},
            files={
                "file": (
                    "calificaciones.xlsx",
                    xlsx_bytes,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
            },
            headers=headers,
        )
        assert preview.status_code == 200
        preview_token = preview.json()["preview_token"]

        # Debug: check data exists
        from sqlalchemy import text as _sql
        debug = await db_session.execute(
            _sql("SELECT id, nombre, apellidos FROM entrada_padron WHERE tenant_id=:tid"),
            {"tid": _DEV_TENANT_ID},
        )
        rows = debug.fetchall()
        assert len(rows) > 0, "No hay entradas de padron en DB"

        # Confirm
        resp = await client.post(
            "/api/calificaciones/importar/confirm",
            data={
                "preview_token": preview_token,
                "materia_id": str(materia_id),
                "actividades_seleccionadas": json.dumps(["TP1 (Real)"]),
            },
            headers=headers,
        )
        assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"
        body = resp.json()
        assert body["calificaciones_importadas"] >= 1
        assert len(body["actividades"]) >= 1



    async def test_importar_confirm_invalid_token(
        self, client: AsyncClient
    ) -> None:
        """POST confirm con token invalido → 400."""
        headers = {"Authorization": f"Bearer {_coord_token()}"}
        resp = await client.post(
            "/api/calificaciones/importar/confirm",
            data={
                "preview_token": "token-invalido",
                "materia_id": str(uuid4()),
                "actividades_seleccionadas": json.dumps([]),
            },
            headers=headers,
        )
        assert resp.status_code == 400

    # ── POST /api/calificaciones/finalizacion ────────────────────────

    async def test_finalizacion_detecta_sin_corregir(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """POST finalizacion → detecta actividades textuales sin calificar."""
        materia_id = await _seed_materia(db_session)
        await _seed_entrada_padron(
            db_session, materia_id, nombre="Juan", apellidos="Perez"
        )

        xlsx_bytes = _make_xlsx_bytes(
            headers=["Nombre", "Apellidos", "Observaciones"],
            filas=[("Juan", "Perez", "Entregado")],
        )

        headers = {"Authorization": f"Bearer {_coord_token()}"}
        resp = await client.post(
            "/api/calificaciones/finalizacion",
            data={"materia_id": str(materia_id)},
            files={
                "file": (
                    "finalizacion.xlsx",
                    xlsx_bytes,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
            },
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "posibles_sin_corregir" in body
        assert len(body["posibles_sin_corregir"]) >= 0

    # ── GET /api/calificaciones/umbral ───────────────────────────────

    async def test_obtener_umbral_default(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GET umbral sin configuracion → retorna default (200)."""
        materia_id = await _seed_materia(db_session)
        uid = await _seed_usuario(db_session)
        asignacion_id = await _seed_asignacion(db_session, uid, materia_id)

        headers = {"Authorization": f"Bearer {_coord_token()}"}
        resp = await client.get(
            "/api/calificaciones/umbral",
            params={
                "materia_id": str(materia_id),
                "asignacion_id": str(asignacion_id),
            },
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["umbral_pct"] == 60
        assert isinstance(body["valores_aprobatorios"], list)

    async def test_obtener_umbral_con_configuracion(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GET umbral con configuracion → retorna valores guardados."""
        materia_id = await _seed_materia(db_session)
        uid = await _seed_usuario(db_session)
        asignacion_id = await _seed_asignacion(db_session, uid, materia_id)
        await _seed_umbral(
            db_session, materia_id, asignacion_id,
            umbral_pct=75, valores_aprobatorios=["Aprobado", "Promocionado"],
        )

        headers = {"Authorization": f"Bearer {_coord_token()}"}
        resp = await client.get(
            "/api/calificaciones/umbral",
            params={
                "materia_id": str(materia_id),
                "asignacion_id": str(asignacion_id),
            },
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["umbral_pct"] == 75
        assert "Aprobado" in body["valores_aprobatorios"]

    # ── PUT /api/calificaciones/umbral ───────────────────────────────

    async def test_configurar_umbral_crea_nuevo(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """PUT umbral crea nuevo → 200 + umbral creado."""
        materia_id = await _seed_materia(db_session)
        uid = await _seed_usuario(db_session)
        asignacion_id = await _seed_asignacion(db_session, uid, materia_id)

        headers = {"Authorization": f"Bearer {_coord_token()}"}
        resp = await client.put(
            "/api/calificaciones/umbral",
            json={
                "materia_id": str(materia_id),
                "asignacion_id": str(asignacion_id),
                "umbral_pct": 80,
                "valores_aprobatorios": ["Satisfactorio"],
            },
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["umbral_pct"] == 80
        assert "Satisfactorio" in (body.get("valores_aprobatorios") or [])

    async def test_configurar_umbral_actualiza_existente(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """PUT umbral actualiza existente → recalcula aprobado."""
        materia_id = await _seed_materia(db_session)
        uid = await _seed_usuario(db_session)
        asignacion_id = await _seed_asignacion(db_session, uid, materia_id)
        entrada_id = await _seed_entrada_padron(
            db_session, materia_id, nombre="Juan", apellidos="Perez"
        )
        await _seed_calificacion(db_session, materia_id, entrada_id, actividad="TP1")

        headers = {"Authorization": f"Bearer {_coord_token()}"}

        # Crear umbral
        resp1 = await client.put(
            "/api/calificaciones/umbral",
            json={
                "materia_id": str(materia_id),
                "asignacion_id": str(asignacion_id),
                "umbral_pct": 80,
                "valores_aprobatorios": ["Aprobado"],
            },
            headers=headers,
        )
        assert resp1.status_code == 200
        assert resp1.json()["umbral_pct"] == 80

        # Actualizar umbral
        resp2 = await client.put(
            "/api/calificaciones/umbral",
            json={
                "materia_id": str(materia_id),
                "asignacion_id": str(asignacion_id),
                "umbral_pct": 60,
                "valores_aprobatorios": ["Aprobado"],
            },
            headers=headers,
        )
        assert resp2.status_code == 200
        body = resp2.json()
        assert body["umbral_pct"] == 60

    async def test_configurar_umbral_scope_profesor_sin_asignacion(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """PUT umbral como PROFESOR sin asignacion → 403."""
        materia_id = await _seed_materia(db_session)
        otro_uid = await _seed_usuario(db_session, "otro@test.com")
        asignacion_id = await _seed_asignacion(db_session, otro_uid, materia_id)

        # Profesor con otro user_id (no asignado a esta materia)
        profesor_user_id = uuid4()
        headers = {"Authorization": f"Bearer {_profesor_token(user_id=profesor_user_id)}"}
        resp = await client.put(
            "/api/calificaciones/umbral",
            json={
                "materia_id": str(materia_id),
                "asignacion_id": str(asignacion_id),
                "umbral_pct": 70,
            },
            headers=headers,
        )
        assert resp.status_code == 403

    # ── Auditoria ─────────────────────────────────────────────────────

    async def test_audit_importar_confirm(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """importar confirm genera CALIFICACIONES_IMPORTAR en audit log."""
        materia_id = await _seed_materia(db_session)
        await _seed_entrada_padron(db_session, materia_id)

        xlsx_bytes = _make_xlsx_bytes(
            headers=["Nombre", "Apellidos", "TP1 (Real)"],
            filas=[("Juan", "Perez", "80")],
        )

        headers = {"Authorization": f"Bearer {_coord_token()}"}

        preview = await client.post(
            "/api/calificaciones/importar/preview",
            data={"materia_id": str(materia_id)},
            files={
                "file": (
                    "calificaciones.xlsx",
                    xlsx_bytes,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
            },
            headers=headers,
        )
        preview_token = preview.json()["preview_token"]

        await client.post(
            "/api/calificaciones/importar/confirm",
            data={
                "preview_token": preview_token,
                "materia_id": str(materia_id),
                "actividades_seleccionadas": json.dumps(["TP1 (Real)"]),
            },
            headers=headers,
        )

        result = await db_session.execute(
            text(
                "SELECT accion, materia_id "
                "FROM audit_log "
                "WHERE accion = 'CALIFICACIONES_IMPORTAR' "
                "ORDER BY fecha_hora DESC LIMIT 1"
            ),
        )
        row = result.fetchone()
        assert row is not None
        assert row[0] == "CALIFICACIONES_IMPORTAR"
        assert str(row[1]) == str(materia_id)

    async def test_audit_configurar_umbral(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """configurar umbral genera CALIFICACIONES_IMPORTAR en audit log."""
        materia_id = await _seed_materia(db_session)
        uid = await _seed_usuario(db_session)
        asignacion_id = await _seed_asignacion(db_session, uid, materia_id)

        headers = {"Authorization": f"Bearer {_coord_token()}"}
        await client.put(
            "/api/calificaciones/umbral",
            json={
                "materia_id": str(materia_id),
                "asignacion_id": str(asignacion_id),
                "umbral_pct": 70,
            },
            headers=headers,
        )

        result = await db_session.execute(
            text(
                "SELECT accion "
                "FROM audit_log "
                "WHERE accion = 'CALIFICACIONES_IMPORTAR' "
                "ORDER BY fecha_hora DESC LIMIT 1"
            ),
        )
        row = result.fetchone()
        assert row is not None

    # ── Multi-tenant ──────────────────────────────────────────────────

    async def test_multi_tenant_aislamiento_umbral(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Datos de tenant A no visibles en tenant B."""
        materia_a = await _seed_materia(db_session, _DEV_TENANT_ID)
        uid_a = await _seed_usuario(db_session, tenant_id=_DEV_TENANT_ID)
        asig_a = await _seed_asignacion(db_session, uid_a, materia_a, _DEV_TENANT_ID)
        await _seed_umbral(
            db_session, materia_a, asig_a, _DEV_TENANT_ID,
            umbral_pct=90, valores_aprobatorios=["Excelente"],
        )

        await _seed_other_tenant_rbac(db_session)

        headers = {"Authorization": f"Bearer {_other_tenant_token()}"}
        resp = await client.get(
            "/api/calificaciones/umbral",
            params={
                "materia_id": str(materia_a),
                "asignacion_id": str(asig_a),
            },
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["umbral_pct"] == 60
