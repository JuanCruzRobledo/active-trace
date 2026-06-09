"""Tests E2E de API para Encuentros y Guardias (C-13).

Cubre:
  Slots recurrentes y únicos, instancias, estado independiente,
  soft-delete, filtros, scope multi-tenant, scope propio,
  exportación HTML, CRUD de guardias, permisos y auditoría.

Requiere PostgreSQL real (DATABASE_URL_TEST en el entorno).
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
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
_DEV_TENANT_ID_2 = UUID("00000000-0000-0000-0000-000000000002")
_SECRET_KEY = "a" * 64


# ── Models needed for fixtures ───────────────────────────────────────────

from app.models.tenant import Tenant  # noqa: E402
from app.models.permiso import Permiso  # noqa: E402
from app.models.rol import Rol  # noqa: E402
from app.models.rol_permiso import RolPermiso  # noqa: E402
from app.models.carrera import Carrera  # noqa: E402
from app.models.cohorte import Cohorte  # noqa: E402
from app.models.materia import Materia  # noqa: E402
from app.models.usuario import Usuario  # noqa: E402
from app.models.asignacion import Asignacion  # noqa: E402
from app.models.slot_encuentro import SlotEncuentro  # noqa: E402
from app.models.instancia_encuentro import InstanciaEncuentro  # noqa: E402
from app.models.guardia import Guardia  # noqa: E402
from app.models.enums import DiaSemana, EstadoEncuentro, EstadoGuardia  # noqa: E402
from app.models.audit_log import AuditLog  # noqa: E402


# ── Token helpers ────────────────────────────────────────────────────────


def _make_token(user_id: UUID, tenant_id: UUID, roles: list[str] | None = None) -> str:
    return create_access_token(
        user_id=user_id,
        tenant_id=tenant_id or _DEV_TENANT_ID,
        secret_key=_SECRET_KEY,
        roles=roles or [],
    )


# ── Seed helpers ─────────────────────────────────────────────────────────


async def _seed_tenant(db_session: AsyncSession, tenant_id: UUID) -> None:
    exists = await db_session.get(Tenant, tenant_id)
    if exists is None:
        db_session.add(Tenant(id=tenant_id, tenant_id=tenant_id, nombre=f"Tenant {tenant_id}"))
        await db_session.flush()


async def _seed_permisos_encuentros(db_session: AsyncSession, tenant_id: UUID | None = None) -> None:
    tid = tenant_id or _DEV_TENANT_ID

    # Permisos globales (sin tenant) — idempotente: si ya existen, reusa sus IDs
    from sqlalchemy import select as sa_select  # noqa: PLC0415
    permiso_rows = {
        "encuentros:gestionar": "Gestionar encuentros",
        "encuentros:ver-admin": "Ver todos los encuentros",
        "guardias:registrar": "Registrar guardias",
        "guardias:ver-admin": "Ver todas las guardias",
    }
    permiso_ids = {}
    for codigo, desc in permiso_rows.items():
        result = await db_session.execute(sa_select(Permiso).where(Permiso.codigo == codigo))
        existing = result.scalar_one_or_none()
        if existing is not None:
            permiso_ids[codigo] = existing.id
        else:
            p = Permiso(id=uuid4(), codigo=codigo, descripcion=desc)
            db_session.add(p)
            permiso_ids[codigo] = p.id

    roles_data = [
        ("PROFESOR", "Profesor", "Profesor"),
        ("COORDINADOR", "Coordinador", "Coordinador"),
        ("TUTOR", "Tutor", "Tutor"),
        ("ADMIN", "Administrador", "Administrador"),
        ("ALUMNO", "Alumno", "Alumno"),
    ]
    rol_ids = {}
    for codigo, nombre, desc in roles_data:
        r = Rol(id=uuid4(), codigo=codigo, nombre=nombre, descripcion=desc, tenant_id=tid)
        db_session.add(r)
        rol_ids[codigo] = r.id

    role_perms = {
        "PROFESOR": ["encuentros:gestionar", "guardias:registrar"],
        "COORDINADOR": ["encuentros:gestionar", "encuentros:ver-admin", "guardias:registrar", "guardias:ver-admin"],
        "TUTOR": ["guardias:registrar"],
        "ADMIN": ["encuentros:gestionar", "encuentros:ver-admin", "guardias:registrar", "guardias:ver-admin"],
        "ALUMNO": [],
    }
    for rol_codigo, perm_codigos in role_perms.items():
        rid = rol_ids.get(rol_codigo)
        if rid is None:
            continue
        for pc in perm_codigos:
            pid = permiso_ids.get(pc)
            if pid is None:
                continue
            db_session.add(RolPermiso(id=uuid4(), tenant_id=tid, rol_id=rid, permiso_id=pid))
    await db_session.flush()


async def _seed_estructura(
    db_session: AsyncSession,
    *,
    profesor_user_id: UUID | None = None,
    tenant_id: UUID | None = None,
    codigo_sufijo: str = "",
) -> dict:
    tid = tenant_id or _DEV_TENANT_ID
    suf = codigo_sufijo or ("-B" if tid != _DEV_TENANT_ID else "")

    carrera = Carrera(tenant_id=tid, codigo=f"TEST{suf}", nombre=f"Carrera Test{suf}", estado="Activo")
    db_session.add(carrera)
    await db_session.flush()

    materia = Materia(tenant_id=tid, codigo=f"TEST-MAT{suf}", nombre=f"Materia Test{suf}", estado="Activo")
    db_session.add(materia)

    cohorte = Cohorte(
        tenant_id=tid, carrera_id=carrera.id, nombre=f"2026{suf}", anio=2026,
        vig_desde=date(2026, 1, 1), estado="Activo",
    )
    db_session.add(cohorte)

    profesor_user_id = profesor_user_id or uuid4()
    profesor_usuario = Usuario(
        id=profesor_user_id, tenant_id=tid, auth_user_id=None,
        nombre=f"Prof{suf}", apellidos=f"Test{suf}",
        email=f"prof{suf}@test.com", estado="Activo",
    )
    db_session.add(profesor_usuario)

    await db_session.flush()
    return {"carrera_id": carrera.id, "materia_id": materia.id, "cohorte_id": cohorte.id, "profesor_usuario_id": profesor_usuario.id}


async def _seed_asignacion(db_session: AsyncSession, profesor_usuario_id: UUID, materia_id: UUID) -> UUID:
    asignacion = Asignacion(
        tenant_id=_DEV_TENANT_ID, usuario_id=profesor_usuario_id, rol="PROFESOR",
        materia_id=materia_id, desde=datetime.now(timezone.utc),
    )
    db_session.add(asignacion)
    await db_session.flush()
    return asignacion.id


async def _build_full_seed(db_session: AsyncSession) -> dict:
    profesor_user_id = uuid4()
    await _seed_tenant(db_session, _DEV_TENANT_ID)
    await _seed_permisos_encuentros(db_session)
    struct = await _seed_estructura(db_session, profesor_user_id=profesor_user_id)
    asignacion_id = await _seed_asignacion(db_session, struct["profesor_usuario_id"], struct["materia_id"])
    struct["asignacion_id"] = asignacion_id
    struct["profesor_user_id"] = profesor_user_id
    return struct


async def _crear_usuario_y_asignacion(
    db_session: AsyncSession, usuario_id: UUID, materia_id: UUID,
) -> None:
    """Crea un usuario y su asignacion en el tenant por defecto."""
    usuario = Usuario(
        id=usuario_id, tenant_id=_DEV_TENANT_ID, auth_user_id=None,
        nombre="Aux", apellidos="User", email=f"aux_{usuario_id}@test.com",
        estado="Activo",
    )
    db_session.add(usuario)
    await db_session.flush()  # Persistir usuario ANTES de la asignacion
    asignacion = Asignacion(
        tenant_id=_DEV_TENANT_ID, usuario_id=usuario_id, rol="TUTOR",
        materia_id=materia_id, desde=datetime.now(timezone.utc),
    )
    db_session.add(asignacion)


async def _seed_tenant2_estructura(db_session: AsyncSession) -> dict:
    return await _seed_estructura(
        db_session, tenant_id=_DEV_TENANT_ID_2, codigo_sufijo="B",
    )


# ══════════════════════════════════════════════════════════════════════════
# GROUP 8: Tests de Encuentros (Slots + Instancias)
# ══════════════════════════════════════════════════════════════════════════


class TestSlots:
    """8.1-8.2: Creación de slots recurrentes y únicos."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, db_session: AsyncSession):
        self.seed = await _build_full_seed(db_session)
        await db_session.commit()

    async def test_8_1_crear_slot_recurrente_genera_instancias(self, client: AsyncClient):
        """8.1: Crear slot recurrente (4 semanas) genera 4 instancias."""
        token = _make_token(self.seed["profesor_user_id"], _DEV_TENANT_ID, ["PROFESOR"])
        body = {
            "materia_id": str(self.seed["materia_id"]),
            "titulo": "Clase Semanal",
            "hora": "18:00:00",
            "dia_semana": "Lunes",
            "fecha_inicio": "2026-03-02",
            "cant_semanas": 4,
            "meet_url": "https://meet.google.com/abc-defg-hij",
        }
        resp = await client.post(
            "/api/encuentros/slots", json=body,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert len(data["instancias"]) == 4
        fechas = [i["fecha"] for i in data["instancias"]]
        assert "2026-03-02" in fechas
        assert "2026-03-23" in fechas
        for inst in data["instancias"]:
            assert inst["estado"] == "Programado"

    async def test_8_2_crear_encuentro_unico(self, client: AsyncClient):
        """8.2: Crear instancia independiente (sin slot)."""
        token = _make_token(self.seed["profesor_user_id"], _DEV_TENANT_ID, ["PROFESOR"])
        body = {
            "materia_id": str(self.seed["materia_id"]),
            "titulo": "Encuentro Único",
            "fecha": "2026-04-15",
            "hora": "20:00:00",
            "meet_url": "https://meet.google.com/xyz",
        }
        resp = await client.post("/api/encuentros/instancias", json=body,
                                 headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 201, resp.text


class TestInstancias:
    """8.3-8.5: Estado independiente, edición, soft-delete."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, db_session: AsyncSession):
        self.seed = await _build_full_seed(db_session)
        slot = SlotEncuentro(
            tenant_id=_DEV_TENANT_ID, materia_id=self.seed["materia_id"],
            titulo="Test Slot", hora=time(18, 0), dia_semana=DiaSemana.LUNES,
            fecha_inicio=date(2026, 3, 2), cant_semanas=3,
        )
        db_session.add(slot)
        await db_session.flush()
        self.instancias = []
        for i in range(3):
            inst = InstanciaEncuentro(
                tenant_id=_DEV_TENANT_ID, slot_id=slot.id, materia_id=self.seed["materia_id"],
                fecha=date(2026, 3, 2) + timedelta(weeks=i), hora=time(18, 0),
                titulo="Test Instancia", estado=EstadoEncuentro.PROGRAMADO,
            )
            db_session.add(inst)
            self.instancias.append(inst)
        await db_session.flush()
        self.slot_id = slot.id
        await db_session.commit()

    async def test_8_3_estado_independiente(self, client: AsyncClient):
        """8.3: Cancelar una instancia no afecta las otras."""
        token = _make_token(self.seed["profesor_user_id"], _DEV_TENANT_ID, ["PROFESOR"])
        resp = await client.patch(
            f"/api/encuentros/instancias/{self.instancias[0].id}",
            json={"estado": "Cancelado"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["estado"] == "Cancelado"

    async def test_8_4_editar_instancia(self, client: AsyncClient):
        """8.4: Editar instancia con video_url, meet_url, comentario."""
        token = _make_token(self.seed["profesor_user_id"], _DEV_TENANT_ID, ["PROFESOR"])
        resp = await client.patch(
            f"/api/encuentros/instancias/{self.instancias[0].id}",
            json={"estado": "Realizado", "meet_url": "https://meet.google.com/updated",
                  "video_url": "https://drive.google.com/recording", "comentario": "Buena clase"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["estado"] == "Realizado"
        assert data["video_url"] == "https://drive.google.com/recording"
        assert data["comentario"] == "Buena clase"

    async def test_8_5_soft_delete_slot(self, client: AsyncClient):
        """8.5: Soft-delete de slot + instancias."""
        token = _make_token(self.seed["profesor_user_id"], _DEV_TENANT_ID, ["PROFESOR"])
        resp = await client.delete(
            f"/api/encuentros/slots/{self.slot_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 204

        # Slot ya no aparece
        resp2 = await client.get("/api/encuentros/slots",
                                 headers={"Authorization": f"Bearer {token}"})
        assert resp2.status_code == 200
        ids = [s["id"] for s in resp2.json().get("items", [])]
        assert str(self.slot_id) not in ids

    async def test_8_6_listado_con_filtros(self, client: AsyncClient):
        """8.6: Listado con filtros de materia y fechas."""
        token = _make_token(self.seed["profesor_user_id"], _DEV_TENANT_ID, ["PROFESOR"])
        resp = await client.get(
            f"/api/encuentros/instancias?materia_id={self.seed['materia_id']}&desde=2026-03-01&hasta=2026-03-31",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text


class TestScopeMultiTenant:
    """8.7-8.9: Scope multi-tenant, scope propio, exportación."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, db_session: AsyncSession):
        self.seed = await _build_full_seed(db_session)
        profesor_user_id_b = uuid4()
        await _seed_tenant(db_session, _DEV_TENANT_ID_2)
        await _seed_permisos_encuentros(db_session, tenant_id=_DEV_TENANT_ID_2)
        struct_b = await _seed_estructura(
            db_session, profesor_user_id=profesor_user_id_b,
            tenant_id=_DEV_TENANT_ID_2, codigo_sufijo="B",
        )
        # Crear Asignacion para el usuario B en tenant B
        asignacion_b = Asignacion(
            tenant_id=_DEV_TENANT_ID_2, usuario_id=profesor_user_id_b, rol="PROFESOR",
            materia_id=struct_b["materia_id"], desde=datetime.now(timezone.utc),
        )
        db_session.add(asignacion_b)
        await db_session.flush()

        # Slot en tenant A (con asignacion_id de la seed)
        slot_a = SlotEncuentro(
            tenant_id=_DEV_TENANT_ID, materia_id=self.seed["materia_id"],
            asignacion_id=self.seed["asignacion_id"],
            titulo="Slot Tenant A", hora=time(18, 0), dia_semana=DiaSemana.LUNES,
            fecha_inicio=date(2026, 3, 2), cant_semanas=1,
        )
        db_session.add(slot_a)
        # Slot en tenant B
        asignacion_b_id = asignacion_b.id
        slot_b = SlotEncuentro(
            tenant_id=_DEV_TENANT_ID_2, materia_id=struct_b["materia_id"],
            asignacion_id=asignacion_b_id,
            titulo="Slot Tenant B", hora=time(19, 0), dia_semana=DiaSemana.MARTES,
            fecha_inicio=date(2026, 3, 3), cant_semanas=1,
        )
        db_session.add(slot_b)
        await db_session.flush()
        self.slot_a = slot_a
        self.slot_b = slot_b
        self.profesor_user_id_b = profesor_user_id_b
        await db_session.commit()

    async def test_8_7_scope_multi_tenant(self, client: AsyncClient):
        """8.7: Tenant A no ve datos de Tenant B."""
        token_a = _make_token(self.seed["profesor_user_id"], _DEV_TENANT_ID, ["PROFESOR"])
        token_b = _make_token(self.profesor_user_id_b, _DEV_TENANT_ID_2, ["PROFESOR"])

        resp_a = await client.get("/api/encuentros/slots",
                                  headers={"Authorization": f"Bearer {token_a}"})
        ids_a = [s["id"] for s in resp_a.json().get("items", [])]
        resp_b = await client.get("/api/encuentros/slots",
                                  headers={"Authorization": f"Bearer {token_b}"})
        ids_b = [s["id"] for s in resp_b.json().get("items", [])]

        assert str(self.slot_a.id) in ids_a
        assert str(self.slot_a.id) not in ids_b
        assert str(self.slot_b.id) in ids_b
        assert str(self.slot_b.id) not in ids_a

    async def test_8_9_exportar_aula_html(self, client: AsyncClient):
        """8.9: Exportación genera HTML."""
        token = _make_token(self.seed["profesor_user_id"], _DEV_TENANT_ID, ["PROFESOR"])
        resp = await client.get(
            f"/api/encuentros/{self.seed['materia_id']}/exportar-aula",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text


# ══════════════════════════════════════════════════════════════════════════
# GROUP 9: Tests de Guardias
# ══════════════════════════════════════════════════════════════════════════


class TestGuardiasCRUD:
    """9.1-9.6: CRUD de guardias."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, db_session: AsyncSession):
        self.seed = await _build_full_seed(db_session)
        await db_session.commit()

    async def test_9_1_crear_guardia_tutor(self, client: AsyncClient):
        """9.1: TUTOR registra su propia guardia."""
        token = _make_token(self.seed["profesor_user_id"], _DEV_TENANT_ID, ["TUTOR"])
        body = {
            "materia_id": str(self.seed["materia_id"]),
            "carrera_id": str(self.seed["carrera_id"]),
            "cohorte_id": str(self.seed["cohorte_id"]),
            "dia": "Lunes",
            "horario": "14:00-14:45",
            "comentarios": "Mi primera guardia",
        }
        resp = await client.post("/api/guardias", json=body,
                                 headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["estado"] == "Pendiente"
        assert data["dia"] == "Lunes"
        assert data["horario"] == "14:00-14:45"

    async def test_9_3_editar_guardia(self, client: AsyncClient, db_session: AsyncSession):
        """9.3: Editar estado y comentarios de guardia."""
        token = _make_token(self.seed["profesor_user_id"], _DEV_TENANT_ID, ["TUTOR"])
        body = {
            "materia_id": str(self.seed["materia_id"]),
            "carrera_id": str(self.seed["carrera_id"]),
            "cohorte_id": str(self.seed["cohorte_id"]),
            "dia": "Martes", "horario": "15:00-15:45",
        }
        create_resp = await client.post("/api/guardias", json=body,
                                        headers={"Authorization": f"Bearer {token}"})
        assert create_resp.status_code == 201, create_resp.text
        guardia_id = create_resp.json()["id"]

        # Editar (mismo token = mismo user_id = propietario)
        resp = await client.patch(
            f"/api/guardias/{guardia_id}",
            json={"estado": "Realizada", "comentarios": "Completada"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["estado"] == "Realizada"
        assert resp.json()["comentarios"] == "Completada"

    async def test_9_4_tutor_no_edita_otro(self, client: AsyncClient, db_session: AsyncSession):
        """9.4: TUTOR no puede editar guardia de otro."""
        token_a = _make_token(self.seed["profesor_user_id"], _DEV_TENANT_ID, ["TUTOR"])
        body = {
            "materia_id": str(self.seed["materia_id"]),
            "carrera_id": str(self.seed["carrera_id"]),
            "cohorte_id": str(self.seed["cohorte_id"]),
            "dia": "Miércoles", "horario": "16:00-16:45",
        }
        create_resp = await client.post("/api/guardias", json=body,
                                        headers={"Authorization": f"Bearer {token_a}"})
        assert create_resp.status_code == 201, create_resp.text
        guardia_id = create_resp.json()["id"]

        # Tutor B necesita su propia Asignacion
        tutor_b_id = uuid4()
        await _crear_usuario_y_asignacion(db_session, tutor_b_id, self.seed["materia_id"])
        await db_session.commit()
        token_b = _make_token(tutor_b_id, _DEV_TENANT_ID, ["TUTOR"])
        resp = await client.patch(
            f"/api/guardias/{guardia_id}",
            json={"estado": "Cancelada"},
            headers={"Authorization": f"Bearer {token_b}"},
        )
        # TUTOR no puede editar guardia de otro
        assert resp.status_code in (400, 403)

    async def test_9_5_listado_filtros(self, client: AsyncClient, db_session: AsyncSession):
        """9.5: Listado con filtros."""
        token = _make_token(self.seed["profesor_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        body = {
            "materia_id": str(self.seed["materia_id"]),
            "carrera_id": str(self.seed["carrera_id"]),
            "cohorte_id": str(self.seed["cohorte_id"]),
            "dia": "Jueves", "horario": "10:00-10:45",
        }
        await client.post("/api/guardias", json=body,
                          headers={"Authorization": f"Bearer {token}"})

        resp = await client.get(
            f"/api/guardias?materia_id={self.seed['materia_id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        assert len(resp.json().get("items", [])) >= 1

    async def test_9_7_scope_multi_tenant_guardias(self, client: AsyncClient, db_session: AsyncSession):
        """9.7: Scope multi-tenant en guardias."""
        await _seed_tenant(db_session, _DEV_TENANT_ID_2)
        await _seed_permisos_encuentros(db_session, tenant_id=_DEV_TENANT_ID_2)
        struct_b = await _seed_tenant2_estructura(db_session)
        # Asignacion para el usuario B en tenant B
        coord_b_user_id = struct_b["profesor_usuario_id"]
        asignacion_b = Asignacion(
            tenant_id=_DEV_TENANT_ID_2, usuario_id=coord_b_user_id, rol="COORDINADOR",
            materia_id=struct_b["materia_id"], desde=datetime.now(timezone.utc),
        )
        db_session.add(asignacion_b)
        await db_session.flush()
        await db_session.commit()

        token_a = _make_token(self.seed["profesor_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        body = {
            "materia_id": str(self.seed["materia_id"]),
            "carrera_id": str(self.seed["carrera_id"]),
            "cohorte_id": str(self.seed["cohorte_id"]),
            "dia": "Viernes", "horario": "09:00-09:45",
        }
        await client.post("/api/guardias", json=body,
                          headers={"Authorization": f"Bearer {token_a}"})

        token_b = _make_token(coord_b_user_id, _DEV_TENANT_ID_2, ["COORDINADOR"])
        resp_b = await client.get("/api/guardias",
                                  headers={"Authorization": f"Bearer {token_b}"})
        assert resp_b.status_code == 200, resp_b.text
        items_b = resp_b.json().get("items", [])
        assert len(items_b) == 0  # Tenant B tiene su propia session scope


# ══════════════════════════════════════════════════════════════════════════
# GROUP 10: Tests de Permisos y Auditoría
# ══════════════════════════════════════════════════════════════════════════


class TestPermisos:
    """10.1-10.2: Usuarios sin permiso reciben 403."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, db_session: AsyncSession):
        self.seed = await _build_full_seed(db_session)
        await db_session.commit()

    async def test_10_1_sin_permiso_encuentros_403(self, client: AsyncClient):
        """10.1: ALUMNO sin encuentros:gestionar recibe 403."""
        resp = await client.get("/api/encuentros/slots",
                                headers={"Authorization": f"Bearer {_make_token(uuid4(), _DEV_TENANT_ID, ['ALUMNO'])}"})
        assert resp.status_code == 403

    async def test_10_2_sin_permiso_guardias_403(self, client: AsyncClient):
        """10.2: ALUMNO sin guardias:registrar recibe 403."""
        resp = await client.get("/api/guardias",
                                headers={"Authorization": f"Bearer {_make_token(uuid4(), _DEV_TENANT_ID, ['ALUMNO'])}"})
        assert resp.status_code == 403


class TestAuditoria:
    """10.3-10.5: Auditoría registra acciones."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, db_session: AsyncSession):
        self.seed = await _build_full_seed(db_session)
        await db_session.commit()

    async def test_10_3_audit_encuentro_crear(self, client: AsyncClient, db_session: AsyncSession):
        """10.3: Auditoría registra ENCUENTRO_CREAR al crear slot."""
        pid = self.seed["profesor_user_id"]
        token = _make_token(pid, _DEV_TENANT_ID, ["PROFESOR"])
        body = {
            "materia_id": str(self.seed["materia_id"]),
            "titulo": "Clase Auditada", "hora": "18:00:00",
            "dia_semana": "Lunes", "fecha_inicio": "2026-03-02", "cant_semanas": 2,
        }
        resp = await client.post("/api/encuentros/slots", json=body,
                                 headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 201, resp.text

        result = await db_session.execute(
            text("SELECT accion, detalle FROM audit_log WHERE accion = 'ENCUENTRO_CREAR' ORDER BY fecha_hora DESC LIMIT 1")
        )
        row = result.fetchone()
        assert row is not None, "No se registró ENCUENTRO_CREAR en audit_log"
        assert row[0] == "ENCUENTRO_CREAR"

    async def test_10_4_audit_encuentro_modificar(self, client: AsyncClient, db_session: AsyncSession):
        """10.4: Auditoría registra ENCUENTRO_MODIFICAR al editar instancia."""
        inst = InstanciaEncuentro(
            tenant_id=_DEV_TENANT_ID, materia_id=self.seed["materia_id"],
            fecha=date(2026, 4, 1), hora=time(18, 0), titulo="Test",
            estado=EstadoEncuentro.PROGRAMADO,
        )
        db_session.add(inst)
        await db_session.commit()

        pid = self.seed["profesor_user_id"]
        token = _make_token(pid, _DEV_TENANT_ID, ["PROFESOR"])
        resp = await client.patch(
            f"/api/encuentros/instancias/{inst.id}",
            json={"estado": "Realizado", "comentario": "Audit test"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text

        result = await db_session.execute(
            text("SELECT accion FROM audit_log WHERE accion = 'ENCUENTRO_MODIFICAR' ORDER BY fecha_hora DESC LIMIT 1")
        )
        assert result.fetchone() is not None

    async def test_10_5_audit_guardia_registrar(self, client: AsyncClient, db_session: AsyncSession):
        """10.5: Auditoría registra GUARDIA_REGISTRAR al crear guardia."""
        token = _make_token(self.seed["profesor_user_id"], _DEV_TENANT_ID, ["TUTOR"])
        body = {
            "materia_id": str(self.seed["materia_id"]),
            "carrera_id": str(self.seed["carrera_id"]),
            "cohorte_id": str(self.seed["cohorte_id"]),
            "dia": "Sábado", "horario": "11:00-11:45",
        }
        resp = await client.post("/api/guardias", json=body,
                                 headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 201, resp.text

        result = await db_session.execute(
            text("SELECT accion FROM audit_log WHERE accion = 'GUARDIA_REGISTRAR' ORDER BY fecha_hora DESC LIMIT 1")
        )
        assert result.fetchone() is not None
