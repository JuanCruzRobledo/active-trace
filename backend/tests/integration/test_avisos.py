"""Tests E2E de Avisos — CRUD, timeline, acknowledgment, tracking, multi-tenant (C-15).

Cubre:
  CRUD de avisos (crear, editar, eliminar hard/soft), timeline por rol,
  acknowledgment con duplicados, tracking con agregados, multi-tenant.

Requiere PostgreSQL real (DATABASE_URL_TEST en el entorno).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import text as sa_text
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

# ── Models ───────────────────────────────────────────────────────────────

from app.models.tenant import Tenant  # noqa: E402
from app.models.permiso import Permiso  # noqa: E402
from app.models.rol import Rol  # noqa: E402
from app.models.rol_permiso import RolPermiso  # noqa: E402
from app.models.carrera import Carrera  # noqa: E402
from app.models.cohorte import Cohorte  # noqa: E402
from app.models.materia import Materia  # noqa: E402
from app.models.usuario import Usuario  # noqa: E402
from app.models.asignacion import Asignacion  # noqa: E402
from app.models.aviso import Aviso  # noqa: E402
from app.models.acknowledgment_aviso import AcknowledgmentAviso  # noqa: E402
from app.models.enums import AlcanceAviso, SeveridadAviso  # noqa: E402
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


async def _seed_permisos_avisos(db_session: AsyncSession, tenant_id: UUID | None = None) -> None:
    tid = tenant_id or _DEV_TENANT_ID
    from sqlalchemy import select as sa_select

    permiso_rows = {
        "avisos:gestionar": "Gestionar avisos institucionales",
        "avisos:ver": "Ver avisos, timeline y confirmar lectura",
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
        ("ADMIN", "Administrador", "Administrador"),
        ("ALUMNO", "Alumno", "Alumno"),
        ("TUTOR", "Tutor", "Tutor"),
    ]
    rol_ids = {}
    for codigo, nombre, desc in roles_data:
        r = Rol(id=uuid4(), codigo=codigo, nombre=nombre, descripcion=desc, tenant_id=tid)
        db_session.add(r)
        rol_ids[codigo] = r.id

    role_perms = {
        "COORDINADOR": ["avisos:gestionar", "avisos:ver"],
        "PROFESOR": ["avisos:ver"],
        "ALUMNO": ["avisos:ver"],
        "TUTOR": ["avisos:ver"],
        "ADMIN": ["avisos:gestionar", "avisos:ver"],
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
        vig_desde=datetime.now(timezone.utc).date(), estado="Activo",
    )
    db_session.add(cohorte)
    await db_session.flush()

    return {"carrera_id": carrera.id, "materia_id": materia.id, "cohorte_id": cohorte.id}


async def _seed_usuario(
    db_session: AsyncSession, tenant_id: UUID, rol: str, sufijo: str = ""
) -> dict:
    uid = uuid4()
    usuario = Usuario(
        id=uid, tenant_id=tenant_id, auth_user_id=None,
        nombre=f"User{sufijo}", apellidos=f"Test{sufijo}",
        email=f"user{sufijo}_{uid}@test.com", estado="Activo",
    )
    db_session.add(usuario)
    await db_session.flush()
    return {"usuario_id": uid, "usuario": usuario}


async def _build_full_seed(db_session: AsyncSession, tenant_id: UUID | None = None) -> dict:
    tid = tenant_id or _DEV_TENANT_ID
    await _seed_tenant(db_session, tid)
    await _seed_permisos_avisos(db_session, tid)
    struct = await _seed_estructura(db_session, tenant_id=tid)
    coord = await _seed_usuario(db_session, tid, "COORDINADOR", "_coord")
    alumno = await _seed_usuario(db_session, tid, "ALUMNO", "_alumno")
    struct["coord_user_id"] = coord["usuario_id"]
    struct["alumno_user_id"] = alumno["usuario_id"]
    return struct


async def _crear_aviso_en_seed(
    db_session: AsyncSession,
    materia_id: UUID | None = None,
    tenant_id: UUID | None = None,
) -> Aviso:
    tid = tenant_id or _DEV_TENANT_ID
    inicio = datetime.now(timezone.utc).replace(microsecond=0)
    aviso = Aviso(
        tenant_id=tid,
        alcance=AlcanceAviso.GLOBAL if materia_id is None else AlcanceAviso.POR_MATERIA,
        materia_id=materia_id,
        cohorte_id=None,
        rol_destino=None,
        severidad=SeveridadAviso.ADVERTENCIA,
        titulo="Aviso de prueba",
        cuerpo="Este es un aviso de prueba para tests",
        inicio_en=inicio,
        fin_en=inicio + timedelta(days=30),
        orden=1,
        activo=True,
        requiere_ack=True,
    )
    db_session.add(aviso)
    await db_session.flush()
    return aviso


# ══════════════════════════════════════════════════════════════════════════
# 6.1 Tests de Repositorio
# ══════════════════════════════════════════════════════════════════════════


class TestAvisoRepository:
    """6.1: CRUD Aviso, timeline, hard/soft delete, tenant scope."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, db_session: AsyncSession):
        self.seed = await _build_full_seed(db_session)
        self.aviso = await _crear_aviso_en_seed(
            db_session, self.seed["materia_id"], _DEV_TENANT_ID,
        )
        await db_session.commit()
        from app.repositories.aviso_repository import AvisoRepository
        self.repo = AvisoRepository(db_session, _DEV_TENANT_ID)

    async def test_6_1_1_get_by_id(self, db_session: AsyncSession):
        """Obtener aviso por ID."""
        aviso = await self.repo.get_by_id(self.aviso.id)
        assert aviso is not None
        assert aviso.id == self.aviso.id
        assert aviso.titulo == "Aviso de prueba"

    async def test_6_1_2_get_by_id_not_found(self, db_session: AsyncSession):
        """get_by_id con ID inexistente retorna None."""
        aviso = await self.repo.get_by_id(uuid4())
        assert aviso is None

    async def test_6_1_3_listar_sin_filtros(self, db_session: AsyncSession):
        """Listar sin filtros retorna todos."""
        items = await self.repo.listar()
        assert len(items) >= 1

    async def test_6_1_4_listar_con_filtros(self, db_session: AsyncSession):
        """Listar filtrado por severidad."""
        items = await self.repo.listar(severidad="Advertencia")
        assert len(items) >= 1
        assert items[0].severidad.value == "Advertencia"

    async def test_6_1_5_listar_filtro_alcance(self, db_session: AsyncSession):
        """Listar filtrado por alcance."""
        items = await self.repo.listar(alcance="PorMateria")
        assert len(items) >= 1

    async def test_6_1_6_listar_filtro_activo(self, db_session: AsyncSession):
        """Listar filtrado por activo."""
        items = await self.repo.listar(activo=True)
        assert len(items) >= 1

    async def test_6_1_7_actualizar(self, db_session: AsyncSession):
        """Actualizar campos de un aviso."""
        actualizado = await self.repo.actualizar(
            self.aviso.id, {"titulo": "Editado"}
        )
        assert actualizado is not None
        assert actualizado.titulo == "Editado"

    async def test_6_1_8_actualizar_not_found(self, db_session: AsyncSession):
        """Actualizar aviso inexistente retorna None."""
        result = await self.repo.actualizar(uuid4(), {"titulo": "Nope"})
        assert result is None

    async def test_6_1_9_tiene_acknowledgments_false(self, db_session: AsyncSession):
        """Aviso sin acuses retorna False."""
        tiene = await self.repo.tiene_acknowledgments(self.aviso.id)
        assert tiene is False

    async def test_6_1_10_tiene_acknowledgments_true(self, db_session: AsyncSession):
        """Aviso con acuses retorna True."""
        ack = AcknowledgmentAviso(
            tenant_id=_DEV_TENANT_ID,
            aviso_id=self.aviso.id,
            usuario_id=self.seed["alumno_user_id"],
        )
        db_session.add(ack)
        await db_session.flush()
        tiene = await self.repo.tiene_acknowledgments(self.aviso.id)
        assert tiene is True

    async def test_6_1_11_hard_delete_sin_acks(self, db_session: AsyncSession):
        """Hard delete de aviso sin acuses elimina el registro."""
        aviso_sin_ack = await _crear_aviso_en_seed(
            db_session, self.seed["materia_id"], _DEV_TENANT_ID,
        )
        await db_session.flush()
        await self.repo.hard_delete(aviso_sin_ack.id)
        result = await self.repo.get_by_id(aviso_sin_ack.id)
        assert result is None

    async def test_6_1_12_soft_delete_con_acks(self, db_session: AsyncSession):
        """Soft delete de aviso con acuses marca deleted_at."""
        ack = AcknowledgmentAviso(
            tenant_id=_DEV_TENANT_ID,
            aviso_id=self.aviso.id,
            usuario_id=self.seed["alumno_user_id"],
        )
        db_session.add(ack)
        await db_session.flush()
        await self.repo.soft_delete(self.aviso)
        # get_by_id excluye soft-deleteados → None
        result = await self.repo.get_by_id(self.aviso.id)
        assert result is None
        # Verificar que la instancia original tiene deleted_at seteado
        assert self.aviso.deleted_at is not None

    async def test_6_1_13_tenant_scope(self, db_session: AsyncSession):
        """Repo filtra por tenant automaticamente."""
        otro_tenant = _DEV_TENANT_ID_2
        await _seed_tenant(db_session, otro_tenant)
        await db_session.commit()
        repo_otro = type(self.repo)(db_session, otro_tenant)
        items = await repo_otro.listar()
        assert len(items) == 0


class TestAcknowledgmentRepository:
    """6.1: CRUD Acknowledgment."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, db_session: AsyncSession):
        self.seed = await _build_full_seed(db_session)
        self.aviso = await _crear_aviso_en_seed(
            db_session, self.seed["materia_id"], _DEV_TENANT_ID,
        )
        await db_session.commit()
        from app.repositories.acknowledgment_repository import (
            AcknowledgmentRepository,
        )
        self.repo = AcknowledgmentRepository(db_session, _DEV_TENANT_ID)

    async def test_6_1_14_crear_ack(self, db_session: AsyncSession):
        """Crear acknowledgment exitoso."""
        ack = await self.repo.crear(self.aviso.id, self.seed["alumno_user_id"])
        assert ack is not None
        assert ack.aviso_id == self.aviso.id
        assert ack.usuario_id == self.seed["alumno_user_id"]

    async def test_6_1_15_crear_duplicado_retorna_none(self, db_session: AsyncSession):
        """Crear acknowledgment duplicado retorna None."""
        await self.repo.crear(self.aviso.id, self.seed["alumno_user_id"])
        ack2 = await self.repo.crear(self.aviso.id, self.seed["alumno_user_id"])
        assert ack2 is None

    async def test_6_1_16_buscar_existente(self, db_session: AsyncSession):
        """Buscar acknowledgment existente."""
        await self.repo.crear(self.aviso.id, self.seed["alumno_user_id"])
        ack = await self.repo.buscar(self.aviso.id, self.seed["alumno_user_id"])
        assert ack is not None
        assert ack.usuario_id == self.seed["alumno_user_id"]

    async def test_6_1_17_buscar_inexistente(self, db_session: AsyncSession):
        """Buscar acknowledgment inexistente retorna None."""
        ack = await self.repo.buscar(self.aviso.id, uuid4())
        assert ack is None

    async def test_6_1_18_listar_por_aviso(self, db_session: AsyncSession):
        """Listar acknowledgments de un aviso."""
        al1 = (await _seed_usuario(db_session, _DEV_TENANT_ID, "ALUMNO", "_l1"))["usuario_id"]
        al2 = (await _seed_usuario(db_session, _DEV_TENANT_ID, "ALUMNO", "_l2"))["usuario_id"]
        await self.repo.crear(self.aviso.id, al1)
        await self.repo.crear(self.aviso.id, al2)
        acks = await self.repo.listar_por_aviso(self.aviso.id)
        assert len(acks) >= 2

    async def test_6_1_19_contar_por_aviso(self, db_session: AsyncSession):
        """Contar acknowledgments de un aviso."""
        al1 = (await _seed_usuario(db_session, _DEV_TENANT_ID, "ALUMNO", "_c1"))["usuario_id"]
        await self.repo.crear(self.aviso.id, al1)
        count = await self.repo.contar_por_aviso(self.aviso.id)
        assert count >= 1


# ══════════════════════════════════════════════════════════════════════════
# 6.2 Tests de Servicio
# ══════════════════════════════════════════════════════════════════════════


class TestAvisoService:
    """6.2: Logica de negocio de avisos."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, db_session: AsyncSession):
        self.seed = await _build_full_seed(db_session)
        await db_session.commit()
        from app.services.aviso_service import AvisoService
        self.svc = AvisoService(
            session=db_session,
            tenant_id=_DEV_TENANT_ID,
            actor_id=self.seed["coord_user_id"],
            roles=["COORDINADOR"],
        )

    async def test_6_2_1_crear_aviso(self, db_session: AsyncSession):
        """Crear aviso exitosamente."""
        from app.schemas.avisos import AvisoCreate
        datos = AvisoCreate(
            alcance="Global",
            severidad="Info",
            titulo="Aviso de prueba",
            cuerpo="Contenido del aviso",
            inicio_en=datetime.now(timezone.utc),
            fin_en=datetime.now(timezone.utc) + timedelta(days=30),
            requiere_ack=False,
        )
        resultado = await self.svc.crear_aviso(datos)
        assert resultado["titulo"] == "Aviso de prueba"
        assert resultado["activo"] is True
        assert resultado["alcance"] == "Global"

    async def test_6_2_2_crear_aviso_alcance_invalido(self, db_session: AsyncSession):
        """Crear aviso PorMateria sin materia_id lanza BusinessError."""
        from app.core.exceptions import BusinessError
        from app.schemas.avisos import AvisoCreate
        datos = AvisoCreate(
            alcance="PorMateria",
            severidad="Info",
            titulo="Aviso sin materia",
            cuerpo="Test",
            inicio_en=datetime.now(timezone.utc),
            fin_en=datetime.now(timezone.utc) + timedelta(days=30),
            requiere_ack=False,
        )
        with pytest.raises(BusinessError, match="requiere materia_id"):
            await self.svc.crear_aviso(datos)

    async def test_6_2_3_editar_aviso(self, db_session: AsyncSession):
        """Editar aviso exitosamente."""
        aviso = await _crear_aviso_en_seed(db_session, self.seed["materia_id"], _DEV_TENANT_ID)
        await db_session.commit()
        from app.schemas.avisos import AvisoUpdate
        datos = AvisoUpdate(titulo="Aviso editado")
        resultado = await self.svc.editar_aviso(aviso.id, datos)
        assert resultado["titulo"] == "Aviso editado"

    async def test_6_2_4_editar_aviso_con_acks_raise(self, db_session: AsyncSession):
        """Editar aviso que ya tiene acuses lanza BusinessError."""
        aviso = await _crear_aviso_en_seed(db_session, self.seed["materia_id"], _DEV_TENANT_ID)
        from app.repositories.acknowledgment_repository import AcknowledgmentRepository
        ack_repo = AcknowledgmentRepository(db_session, _DEV_TENANT_ID)
        await ack_repo.crear(aviso.id, self.seed["alumno_user_id"])
        await db_session.commit()
        from app.core.exceptions import BusinessError
        from app.schemas.avisos import AvisoUpdate
        datos = AvisoUpdate(titulo="No deberia editar")
        with pytest.raises(BusinessError, match="ya tiene acknowledgments"):
            await self.svc.editar_aviso(aviso.id, datos)

    async def test_6_2_5_eliminar_aviso_hard(self, db_session: AsyncSession):
        """Eliminar aviso sin acuses es hard delete."""
        aviso = await _crear_aviso_en_seed(db_session, self.seed["materia_id"], _DEV_TENANT_ID)
        await db_session.commit()
        resultado = await self.svc.eliminar_aviso(aviso.id)
        assert resultado["eliminado"] is True
        assert resultado["metodo"] == "hard_delete"

    async def test_6_2_6_eliminar_aviso_soft(self, db_session: AsyncSession):
        """Eliminar aviso con acuses es soft delete."""
        aviso = await _crear_aviso_en_seed(db_session, self.seed["materia_id"], _DEV_TENANT_ID)
        from app.repositories.acknowledgment_repository import AcknowledgmentRepository
        ack_repo = AcknowledgmentRepository(db_session, _DEV_TENANT_ID)
        await ack_repo.crear(aviso.id, self.seed["alumno_user_id"])
        await db_session.commit()
        resultado = await self.svc.eliminar_aviso(aviso.id)
        assert resultado["eliminado"] is True
        assert resultado["metodo"] == "soft_delete"

    async def test_6_2_7_eliminar_inexistente_raise(self, db_session: AsyncSession):
        """Eliminar aviso inexistente lanza BusinessError."""
        from app.core.exceptions import BusinessError
        with pytest.raises(BusinessError, match="Aviso no encontrado"):
            await self.svc.eliminar_aviso(uuid4())

    async def test_6_2_8_obtener_aviso(self, db_session: AsyncSession):
        """Obtener detalle de aviso."""
        aviso = await _crear_aviso_en_seed(db_session, self.seed["materia_id"], _DEV_TENANT_ID)
        await db_session.commit()
        resultado = await self.svc.obtener_aviso(aviso.id)
        assert resultado["id"] == aviso.id

    async def test_6_2_9_obtener_inexistente_raise(self, db_session: AsyncSession):
        """Obtener aviso inexistente lanza BusinessError."""
        from app.core.exceptions import BusinessError
        with pytest.raises(BusinessError, match="Aviso no encontrado"):
            await self.svc.obtener_aviso(uuid4())

    async def test_6_2_10_acknowledge(self, db_session: AsyncSession):
        """Acknowledge exitoso."""
        aviso = await _crear_aviso_en_seed(db_session, self.seed["materia_id"], _DEV_TENANT_ID)
        await db_session.commit()
        svc_alumno = type(self.svc)(
            session=db_session,
            tenant_id=_DEV_TENANT_ID,
            actor_id=self.seed["alumno_user_id"],
            roles=["ALUMNO"],
        )
        resultado = await svc_alumno.acknowledge(aviso.id)
        assert resultado["aviso_id"] == aviso.id
        assert resultado["usuario_id"] == self.seed["alumno_user_id"]

    async def test_6_2_11_acknowledge_no_requiere(self, db_session: AsyncSession):
        """Acknowledge de aviso que no requiere ack lanza BusinessError."""
        aviso = Aviso(
            tenant_id=_DEV_TENANT_ID,
            alcance=AlcanceAviso.GLOBAL,
            severidad=SeveridadAviso.INFO,
            titulo="Aviso sin ack",
            cuerpo="No requiere acuse",
            inicio_en=datetime.now(timezone.utc),
            fin_en=datetime.now(timezone.utc) + timedelta(days=30),
            orden=1,
            activo=True,
            requiere_ack=False,
        )
        db_session.add(aviso)
        await db_session.commit()
        from app.core.exceptions import BusinessError
        svc_alumno = type(self.svc)(
            session=db_session,
            tenant_id=_DEV_TENANT_ID,
            actor_id=self.seed["alumno_user_id"],
            roles=["ALUMNO"],
        )
        with pytest.raises(BusinessError, match="no requiere acknowledgment"):
            await svc_alumno.acknowledge(aviso.id)

    async def test_6_2_12_acknowledge_duplicado(self, db_session: AsyncSession):
        """Acknowledge duplicado lanza BusinessError."""
        aviso = await _crear_aviso_en_seed(db_session, self.seed["materia_id"], _DEV_TENANT_ID)
        await db_session.commit()
        from app.core.exceptions import BusinessError
        svc_alumno = type(self.svc)(
            session=db_session,
            tenant_id=_DEV_TENANT_ID,
            actor_id=self.seed["alumno_user_id"],
            roles=["ALUMNO"],
        )
        await svc_alumno.acknowledge(aviso.id)
        with pytest.raises(BusinessError, match="(?i)ya has confirmado"):
            await svc_alumno.acknowledge(aviso.id)

    async def test_6_2_13_obtener_tracking(self, db_session: AsyncSession):
        """Tracking con zeros."""
        aviso = await _crear_aviso_en_seed(db_session, self.seed["materia_id"], _DEV_TENANT_ID)
        await db_session.commit()
        tracking = await self.svc.obtener_tracking(aviso.id)
        assert tracking["total_ack"] == 0
        assert tracking["porcentaje"] == 0.0

    async def test_6_2_14_obtener_tracking_con_acks(self, db_session: AsyncSession):
        """Tracking con acknowledgments."""
        aviso = await _crear_aviso_en_seed(db_session, self.seed["materia_id"], _DEV_TENANT_ID)
        from app.repositories.acknowledgment_repository import AcknowledgmentRepository
        ack_repo = AcknowledgmentRepository(db_session, _DEV_TENANT_ID)
        await ack_repo.crear(aviso.id, self.seed["alumno_user_id"])
        await db_session.commit()
        tracking = await self.svc.obtener_tracking(aviso.id)
        assert tracking["total_ack"] >= 1

    async def test_6_2_15_listar_avisos(self, db_session: AsyncSession):
        """Listar avisos con filtros."""
        aviso = await _crear_aviso_en_seed(db_session, self.seed["materia_id"], _DEV_TENANT_ID)
        await db_session.commit()
        resultado = await self.svc.listar_avisos(
            alcance="PorMateria", activo=True,
        )
        assert resultado["total"] >= 1
        assert resultado["items"][0]["id"] == aviso.id


# ══════════════════════════════════════════════════════════════════════════
# 6.3 Tests de Router
# ══════════════════════════════════════════════════════════════════════════


class TestAvisoRouter:
    """6.3: Endpoints REST con auth, permisos, flujos felices y errores."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, db_session: AsyncSession):
        self.seed = await _build_full_seed(db_session)
        await db_session.commit()

    async def _crear_aviso_http(
        self, client: AsyncClient, token: str, body: dict | None = None
    ) -> dict:
        payload = body or {
            "alcance": "Global",
            "severidad": "Info",
            "titulo": "Aviso HTTP test",
            "cuerpo": "Cuerpo del aviso",
            "inicio_en": datetime.now(timezone.utc).isoformat(),
            "fin_en": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "requiere_ack": True,
        }
        resp = await client.post(
            "/api/avisos", json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201, resp.text
        return resp.json()

    # ── CRUD ───────────────────────────────────────────────────────────

    async def test_6_3_1_crear_aviso_201(self, client: AsyncClient):
        """POST /api/avisos -> 201 Created."""
        token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        body = {
            "alcance": "Global",
            "severidad": "Info",
            "titulo": "Aviso de prueba",
            "cuerpo": "Contenido del aviso",
            "inicio_en": datetime.now(timezone.utc).isoformat(),
            "fin_en": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "requiere_ack": True,
        }
        resp = await client.post(
            "/api/avisos", json=body,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["titulo"] == "Aviso de prueba"
        assert data["activo"] is True

    async def test_6_3_2_crear_aviso_403_sin_permiso(self, client: AsyncClient):
        """POST sin avisos:gestionar -> 403."""
        token = _make_token(self.seed["alumno_user_id"], _DEV_TENANT_ID, ["ALUMNO"])
        body = {
            "alcance": "Global",
            "severidad": "Info",
            "titulo": "Sin permiso",
            "cuerpo": "Test",
            "inicio_en": datetime.now(timezone.utc).isoformat(),
            "fin_en": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "requiere_ack": True,
        }
        resp = await client.post(
            "/api/avisos", json=body,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403, resp.text

    async def test_6_3_3_listar_avisos(self, client: AsyncClient):
        """GET /api/avisos -> lista."""
        coord_token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        await self._crear_aviso_http(client, coord_token)
        resp = await client.get(
            "/api/avisos",
            headers={"Authorization": f"Bearer {coord_token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["total"] >= 1

    async def test_6_3_4_obtener_aviso(self, client: AsyncClient):
        """GET /api/avisos/{id} -> detalle."""
        coord_token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        created = await self._crear_aviso_http(client, coord_token)
        alumno_token = _make_token(self.seed["alumno_user_id"], _DEV_TENANT_ID, ["ALUMNO"])
        resp = await client.get(
            f"/api/avisos/{created['id']}",
            headers={"Authorization": f"Bearer {alumno_token}"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["id"] == created["id"]

    async def test_6_3_5_obtener_aviso_404(self, client: AsyncClient):
        """GET /api/avisos/{id} inexistente -> 404."""
        alumno_token = _make_token(self.seed["alumno_user_id"], _DEV_TENANT_ID, ["ALUMNO"])
        resp = await client.get(
            f"/api/avisos/{uuid4()}",
            headers={"Authorization": f"Bearer {alumno_token}"},
        )
        assert resp.status_code == 404, resp.text

    async def test_6_3_6_editar_aviso(self, client: AsyncClient):
        """PUT /api/avisos/{id} -> 200."""
        coord_token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        created = await self._crear_aviso_http(client, coord_token)
        resp = await client.put(
            f"/api/avisos/{created['id']}",
            json={"titulo": "Editado"},
            headers={"Authorization": f"Bearer {coord_token}"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["titulo"] == "Editado"

    async def test_6_3_7_editar_aviso_403(self, client: AsyncClient):
        """PUT sin avisos:gestionar -> 403."""
        coord_token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        created = await self._crear_aviso_http(client, coord_token)
        alumno_token = _make_token(self.seed["alumno_user_id"], _DEV_TENANT_ID, ["ALUMNO"])
        resp = await client.put(
            f"/api/avisos/{created['id']}",
            json={"titulo": "No editable"},
            headers={"Authorization": f"Bearer {alumno_token}"},
        )
        assert resp.status_code == 403, resp.text

    async def test_6_3_8_eliminar_aviso(self, client: AsyncClient):
        """DELETE /api/avisos/{id} -> 200."""
        coord_token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        created = await self._crear_aviso_http(client, coord_token)
        resp = await client.delete(
            f"/api/avisos/{created['id']}",
            headers={"Authorization": f"Bearer {coord_token}"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["eliminado"] is True

    # ── Timeline ──────────────────────────────────────────────────────

    async def test_6_3_9_timeline(self, client: AsyncClient):
        """GET /api/avisos/timeline -> 200."""
        coord_token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        await self._crear_aviso_http(client, coord_token)
        alumno_token = _make_token(self.seed["alumno_user_id"], _DEV_TENANT_ID, ["ALUMNO"])
        resp = await client.get(
            "/api/avisos/timeline",
            headers={"Authorization": f"Bearer {alumno_token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "items" in data
        assert "total" in data

    async def test_6_3_10_timeline_403_sin_permiso(self, client: AsyncClient):
        """GET timeline sin avisos:ver -> 403 (rol sin permiso)."""
        token = _make_token(uuid4(), _DEV_TENANT_ID, [])
        resp = await client.get(
            "/api/avisos/timeline",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403, resp.text

    # ── Acknowledgment ────────────────────────────────────────────────

    async def test_6_3_11_acknowledge(self, client: AsyncClient):
        """POST /api/avisos/{id}/acknowledge -> 200."""
        coord_token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        created = await self._crear_aviso_http(client, coord_token)
        alumno_token = _make_token(self.seed["alumno_user_id"], _DEV_TENANT_ID, ["ALUMNO"])
        resp = await client.post(
            f"/api/avisos/{created['id']}/acknowledge",
            headers={"Authorization": f"Bearer {alumno_token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["aviso_id"] == created["id"]

    async def test_6_3_12_acknowledge_duplicado_409(self, client: AsyncClient):
        """POST acknowledge duplicado -> 409."""
        coord_token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        created = await self._crear_aviso_http(client, coord_token)
        alumno_token = _make_token(self.seed["alumno_user_id"], _DEV_TENANT_ID, ["ALUMNO"])
        await client.post(
            f"/api/avisos/{created['id']}/acknowledge",
            headers={"Authorization": f"Bearer {alumno_token}"},
        )
        resp = await client.post(
            f"/api/avisos/{created['id']}/acknowledge",
            headers={"Authorization": f"Bearer {alumno_token}"},
        )
        assert resp.status_code == 409, resp.text

    # ── Tracking ──────────────────────────────────────────────────────

    async def test_6_3_13_tracking(self, client: AsyncClient):
        """GET /api/avisos/{id}/tracking -> 200."""
        coord_token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        created = await self._crear_aviso_http(client, coord_token)
        resp = await client.get(
            f"/api/avisos/{created['id']}/tracking",
            headers={"Authorization": f"Bearer {coord_token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "total_ack" in data
        assert "porcentaje" in data

    async def test_6_3_14_tracking_403_sin_permiso(self, client: AsyncClient):
        """GET tracking sin avisos:gestionar -> 403."""
        coord_token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        created = await self._crear_aviso_http(client, coord_token)
        alumno_token = _make_token(self.seed["alumno_user_id"], _DEV_TENANT_ID, ["ALUMNO"])
        resp = await client.get(
            f"/api/avisos/{created['id']}/tracking",
            headers={"Authorization": f"Bearer {alumno_token}"},
        )
        assert resp.status_code == 403, resp.text


# ══════════════════════════════════════════════════════════════════════════
# 6.4 Timeline por rol / contexto
# ══════════════════════════════════════════════════════════════════════════


class TestTimelineContexto:
    """6.4: Timeline filtra correctamente por rol y contexto."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, db_session: AsyncSession):
        self.seed = await _build_full_seed(db_session)
        # Crear aviso Global (todos lo ven)
        self.global_aviso = Aviso(
            tenant_id=_DEV_TENANT_ID,
            alcance=AlcanceAviso.GLOBAL,
            severidad=SeveridadAviso.INFO,
            titulo="Aviso Global",
            cuerpo="Para todos",
            inicio_en=datetime.now(timezone.utc),
            fin_en=datetime.now(timezone.utc) + timedelta(days=30),
            orden=1,
            activo=True,
            requiere_ack=False,
        )
        db_session.add(self.global_aviso)
        # Crear aviso PorMateria
        self.materia_aviso = Aviso(
            tenant_id=_DEV_TENANT_ID,
            alcance=AlcanceAviso.POR_MATERIA,
            materia_id=self.seed["materia_id"],
            severidad=SeveridadAviso.ADVERTENCIA,
            titulo="Aviso por Materia",
            cuerpo="Solo materia",
            inicio_en=datetime.now(timezone.utc),
            fin_en=datetime.now(timezone.utc) + timedelta(days=30),
            orden=2,
            activo=True,
            requiere_ack=False,
        )
        db_session.add(self.materia_aviso)
        await db_session.commit()

    async def test_6_4_1_timeline_ve_global(self, db_session: AsyncSession):
        """Usuario ve avisos globales."""
        from app.services.aviso_service import AvisoService
        from app.models.asignacion import Asignacion

        # Asignar alumno a materia
        asignacion = Asignacion(
            tenant_id=_DEV_TENANT_ID,
            usuario_id=self.seed["alumno_user_id"],
            rol="ALUMNO",
            materia_id=self.seed["materia_id"],
            desde=datetime.now(timezone.utc),
        )
        db_session.add(asignacion)
        await db_session.commit()

        svc = AvisoService(
            session=db_session,
            tenant_id=_DEV_TENANT_ID,
            actor_id=self.seed["alumno_user_id"],
            roles=["ALUMNO"],
        )
        timeline = await svc.obtener_timeline(
            usuario_id=self.seed["alumno_user_id"],
            materia_ids=[self.seed["materia_id"]],
            cohorte_ids=[],
        )
        assert timeline["total"] >= 1
        ids = {item["id"] for item in timeline["items"]}
        assert self.global_aviso.id in ids

    async def test_6_4_2_timeline_ve_materia_asignada(self, db_session: AsyncSession):
        """Usuario ve avisos de materia a la que esta asignado."""
        from app.services.aviso_service import AvisoService
        from app.models.asignacion import Asignacion

        asignacion = Asignacion(
            tenant_id=_DEV_TENANT_ID,
            usuario_id=self.seed["alumno_user_id"],
            rol="ALUMNO",
            materia_id=self.seed["materia_id"],
            desde=datetime.now(timezone.utc),
        )
        db_session.add(asignacion)
        await db_session.commit()

        svc = AvisoService(
            session=db_session,
            tenant_id=_DEV_TENANT_ID,
            actor_id=self.seed["alumno_user_id"],
            roles=["ALUMNO"],
        )
        timeline = await svc.obtener_timeline(
            usuario_id=self.seed["alumno_user_id"],
            materia_ids=[self.seed["materia_id"]],
            cohorte_ids=[],
        )
        ids = {item["id"] for item in timeline["items"]}
        assert self.materia_aviso.id in ids


# ══════════════════════════════════════════════════════════════════════════
# 6.5 Multi-tenant isolation
# ══════════════════════════════════════════════════════════════════════════


class TestMultiTenantAvisos:
    """6.5: Aislamiento multi-tenant en avisos."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, db_session: AsyncSession):
        # Tenant 1
        await _seed_tenant(db_session, _DEV_TENANT_ID)
        await _seed_permisos_avisos(db_session, _DEV_TENANT_ID)
        struct1 = await _seed_estructura(db_session, tenant_id=_DEV_TENANT_ID)
        coord1 = await _seed_usuario(db_session, _DEV_TENANT_ID, "COORDINADOR", "_t1")
        aviso1 = await _crear_aviso_en_seed(
            db_session, struct1["materia_id"], _DEV_TENANT_ID,
        )
        # Tenant 2
        await _seed_tenant(db_session, _DEV_TENANT_ID_2)
        await _seed_permisos_avisos(db_session, _DEV_TENANT_ID_2)
        struct2 = await _seed_estructura(db_session, tenant_id=_DEV_TENANT_ID_2, codigo_sufijo="B")
        coord2 = await _seed_usuario(db_session, _DEV_TENANT_ID_2, "COORDINADOR", "_t2")
        aviso2 = await _crear_aviso_en_seed(
            db_session, struct2["materia_id"], _DEV_TENANT_ID_2,
        )
        await db_session.commit()
        self.tenant1 = {"coord_user_id": coord1["usuario_id"], "aviso_id": aviso1.id}
        self.tenant2 = {"coord_user_id": coord2["usuario_id"], "aviso_id": aviso2.id}

    async def test_6_5_1_tenant1_no_ve_tenant2(self, client: AsyncClient):
        """Tenant 1 no ve avisos del Tenant 2."""
        token = _make_token(self.tenant1["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        resp = await client.get(
            "/api/avisos",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        ids = {item["id"] for item in data["items"]}
        assert str(self.tenant1["aviso_id"]) in ids
        assert str(self.tenant2["aviso_id"]) not in ids

    async def test_6_5_2_tenant2_no_ve_tenant1(self, client: AsyncClient):
        """Tenant 2 no ve avisos del Tenant 1."""
        token = _make_token(self.tenant2["coord_user_id"], _DEV_TENANT_ID_2, ["COORDINADOR"])
        resp = await client.get(
            "/api/avisos",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        ids = {item["id"] for item in data["items"]}
        assert str(self.tenant2["aviso_id"]) in ids
        assert str(self.tenant1["aviso_id"]) not in ids
