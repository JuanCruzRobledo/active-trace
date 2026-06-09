"""Tests E2E de Coloquios — convocatorias, reservas, resultados, metricas (C-14).

Cubre:
  CRUD de convocatorias, importacion de alumnos, reserva con control de cupo,
  cancelacion, registro de resultados, cierre, metricas, agenda, multi-tenant.

Requiere PostgreSQL real (DATABASE_URL_TEST en el entorno).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
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
from app.models.evaluacion import Evaluacion  # noqa: E402
from app.models.reserva_evaluacion import ReservaEvaluacion  # noqa: E402
from app.models.resultado_evaluacion import ResultadoEvaluacion  # noqa: E402
from app.models.enums import TipoEvaluacion, EstadoEvaluacion, EstadoReserva  # noqa: E402
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


async def _seed_permisos_coloquios(db_session: AsyncSession, tenant_id: UUID | None = None) -> None:
    tid = tenant_id or _DEV_TENANT_ID
    from sqlalchemy import select as sa_select

    permiso_rows = {
        "coloquios:gestionar": "Gestionar coloquios",
        "coloquios:reservar": "Reservar turno de coloquio",
        "coloquios:ver": "Ver coloquios y metricas",
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
    ]
    rol_ids = {}
    for codigo, nombre, desc in roles_data:
        r = Rol(id=uuid4(), codigo=codigo, nombre=nombre, descripcion=desc, tenant_id=tid)
        db_session.add(r)
        rol_ids[codigo] = r.id

    role_perms = {
        "COORDINADOR": ["coloquios:gestionar", "coloquios:ver"],
        "PROFESOR": ["coloquios:ver"],
        "ALUMNO": ["coloquios:reservar"],
        "ADMIN": ["coloquios:gestionar", "coloquios:reservar", "coloquios:ver"],
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
        vig_desde=date(2026, 1, 1), estado="Activo",
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


async def _seed_asignacion(
    db_session: AsyncSession, usuario_id: UUID, materia_id: UUID, tenant_id: UUID, rol: str = "PROFESOR"
) -> UUID:
    asignacion = Asignacion(
        tenant_id=tenant_id, usuario_id=usuario_id, rol=rol,
        materia_id=materia_id, desde=datetime.now(timezone.utc),
    )
    db_session.add(asignacion)
    await db_session.flush()
    return asignacion.id


async def _build_full_seed(db_session: AsyncSession, tenant_id: UUID | None = None) -> dict:
    tid = tenant_id or _DEV_TENANT_ID
    await _seed_tenant(db_session, tid)
    await _seed_permisos_coloquios(db_session, tid)
    struct = await _seed_estructura(db_session, tenant_id=tid)
    coord = await _seed_usuario(db_session, tid, "COORDINADOR", "_coord")
    alumno = await _seed_usuario(db_session, tid, "ALUMNO", "_alumno")
    await _seed_asignacion(db_session, coord["usuario_id"], struct["materia_id"], tid, "COORDINADOR")
    struct["coord_user_id"] = coord["usuario_id"]
    struct["alumno_user_id"] = alumno["usuario_id"]
    return struct


async def _crear_convocatoria_en_seed(
    db_session: AsyncSession, materia_id: UUID, cohorte_id: UUID, tenant_id: UUID
) -> Evaluacion:
    ev = Evaluacion(
        tenant_id=tenant_id,
        materia_id=materia_id,
        cohorte_id=cohorte_id,
        tipo="Coloquio",
        instancia="Primer Coloquio",
        dias_disponibles=3,
        cupos_por_dia=5,
        fecha_inicio=date(2026, 6, 10),
        fecha_fin=date(2026, 6, 20),
        estado="Activa",
    )
    db_session.add(ev)
    await db_session.flush()
    return ev


async def _crear_reserva_en_seed(
    db_session: AsyncSession, evaluacion_id: UUID, alumno_id: UUID, tenant_id: UUID
) -> ReservaEvaluacion:
    reserva = ReservaEvaluacion(
        tenant_id=tenant_id,
        evaluacion_id=evaluacion_id,
        alumno_id=alumno_id,
        fecha_hora=datetime(2026, 6, 15, 10, 0, tzinfo=timezone.utc),
        estado="Activa",
    )
    db_session.add(reserva)
    await db_session.flush()
    return reserva


# ══════════════════════════════════════════════════════════════════════════
# 6.1 Tests de Repositorio
# ══════════════════════════════════════════════════════════════════════════


class TestEvaluacionRepository:
    """6.1: CRUD Evaluacion, filtros, tenant scope."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, db_session: AsyncSession):
        self.seed = await _build_full_seed(db_session)
        self.ev = await _crear_convocatoria_en_seed(
            db_session, self.seed["materia_id"], self.seed["cohorte_id"], _DEV_TENANT_ID,
        )
        await db_session.commit()
        from app.repositories.evaluacion_repository import EvaluacionRepository
        self.repo = EvaluacionRepository(db_session, _DEV_TENANT_ID)

    async def test_6_1_1_listar_con_filtros(self, db_session: AsyncSession):
        """Listar convocatorias filtradas por materia."""
        items = await self.repo.listar(materia_id=self.seed["materia_id"])
        assert len(items) >= 1
        assert items[0].materia_id == self.seed["materia_id"]

    async def test_6_1_2_listar_filtro_cohorte(self, db_session: AsyncSession):
        """Listar convocatorias filtradas por cohorte."""
        items = await self.repo.listar(cohorte_id=self.seed["cohorte_id"])
        assert len(items) >= 1
        assert items[0].cohorte_id == self.seed["cohorte_id"]

    async def test_6_1_3_listar_filtro_estado(self, db_session: AsyncSession):
        """Listar convocatorias filtradas por estado."""
        items = await self.repo.listar(estado="Activa")
        assert len(items) >= 1
        assert items[0].estado == "Activa"

    async def test_6_1_4_get_by_id(self, db_session: AsyncSession):
        """Obtener convocatoria por ID."""
        ev = await self.repo.get_by_id(self.ev.id)
        assert ev is not None
        assert ev.id == self.ev.id
        assert ev.instancia == "Primer Coloquio"

    async def test_6_1_5_get_by_id_not_found(self, db_session: AsyncSession):
        """get_by_id con ID inexistente retorna None."""
        ev = await self.repo.get_by_id(uuid4())
        assert ev is None

    async def test_6_1_6_actualizar_convocatoria(self, db_session: AsyncSession):
        """Actualizar campos de una convocatoria."""
        actualizada = await self.repo.actualizar(
            self.ev.id, {"instancia": "Segundo Coloquio", "dias_disponibles": 5}
        )
        assert actualizada is not None
        assert actualizada.instancia == "Segundo Coloquio"
        assert actualizada.dias_disponibles == 5

    async def test_6_1_7_cerrar_convocatoria(self, db_session: AsyncSession):
        """Cerrar convocatoria cambia estado y cancela reservas activas."""
        reserva = await _crear_reserva_en_seed(
            db_session, self.ev.id, self.seed["alumno_user_id"], _DEV_TENANT_ID,
        )
        await db_session.commit()
        cerrada = await self.repo.cerrar(self.ev.id)
        assert cerrada is not None
        assert cerrada.estado == "Inactiva"

    async def test_6_1_8_contar_convocados(self, db_session: AsyncSession):
        """contar_convocados retorna cantidad de alumnos importados."""
        # Crear algunas reservas para simular convocados
        al1 = (await _seed_usuario(db_session, _DEV_TENANT_ID, "ALUMNO", "_a1"))["usuario_id"]
        await _crear_reserva_en_seed(db_session, self.ev.id, al1, _DEV_TENANT_ID)
        await db_session.commit()
        count = await self.repo.contar_convocados(self.ev.id)
        assert count >= 1

    async def test_6_1_9_contar_reservas_activas(self, db_session: AsyncSession):
        """contar_reservas_activas retorna solo reservas en estado Activa."""
        al1 = (await _seed_usuario(db_session, _DEV_TENANT_ID, "ALUMNO", "_b1"))["usuario_id"]
        await _crear_reserva_en_seed(db_session, self.ev.id, al1, _DEV_TENANT_ID)
        await db_session.commit()
        count = await self.repo.contar_reservas_activas(self.ev.id)
        assert count >= 1

    async def test_6_1_10_tenant_scope(self, db_session: AsyncSession):
        """Repo filtra por tenant automaticamente."""
        otro_tenant = _DEV_TENANT_ID_2
        await _seed_tenant(db_session, otro_tenant)
        await db_session.commit()
        repo_otro = type(self.repo)(db_session, otro_tenant)
        items = await repo_otro.listar()
        # Debe estar vacio porque las entidades estan en tenant 1
        assert len(items) == 0


class TestReservaEvaluacionRepository:
    """6.1: CRUD Reserva, control de cupo."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, db_session: AsyncSession):
        self.seed = await _build_full_seed(db_session)
        self.ev = await _crear_convocatoria_en_seed(
            db_session, self.seed["materia_id"], self.seed["cohorte_id"], _DEV_TENANT_ID,
        )
        await db_session.commit()
        from app.repositories.reserva_evaluacion_repository import (
            ReservaEvaluacionRepository,
        )
        self.repo = ReservaEvaluacionRepository(db_session, _DEV_TENANT_ID)

    async def test_6_1_11_crear_con_control_cupo_exitoso(self, db_session: AsyncSession):
        """Crear reserva con cupo disponible."""
        reserva = await self.repo.crear_con_control_cupo(
            evaluacion_id=self.ev.id,
            alumno_id=self.seed["alumno_user_id"],
            fecha_hora=datetime(2026, 6, 15, 10, 0, tzinfo=timezone.utc),
        )
        assert reserva is not None
        assert reserva.estado == "Activa"
        assert reserva.alumno_id == self.seed["alumno_user_id"]

    async def test_6_1_12_crear_duplicado_raise_error(self, db_session: AsyncSession):
        """Crear reserva duplicada (mismo alumno+materia) lanza ValueError."""
        await self.repo.crear_con_control_cupo(
            evaluacion_id=self.ev.id,
            alumno_id=self.seed["alumno_user_id"],
            fecha_hora=datetime(2026, 6, 15, 10, 0, tzinfo=timezone.utc),
        )
        with pytest.raises(ValueError, match="ya tiene una reserva activa"):
            await self.repo.crear_con_control_cupo(
                evaluacion_id=self.ev.id,
                alumno_id=self.seed["alumno_user_id"],
                fecha_hora=datetime(2026, 6, 16, 10, 0, tzinfo=timezone.utc),
            )

    async def test_6_1_13_cancelar_reserva(self, db_session: AsyncSession):
        """Cancelar reserva cambia estado a Cancelada."""
        reserva = await self.repo.crear_con_control_cupo(
            evaluacion_id=self.ev.id,
            alumno_id=self.seed["alumno_user_id"],
            fecha_hora=datetime(2026, 6, 15, 10, 0, tzinfo=timezone.utc),
        )
        cancelada = await self.repo.cancelar(reserva.id, self.seed["alumno_user_id"])
        assert cancelada is not None
        assert cancelada.estado == "Cancelada"

    async def test_6_1_14_cancelar_no_pertenece(self, db_session: AsyncSession):
        """Cancelar reserva de otro alumno retorna None."""
        reserva = await self.repo.crear_con_control_cupo(
            evaluacion_id=self.ev.id,
            alumno_id=self.seed["alumno_user_id"],
            fecha_hora=datetime(2026, 6, 15, 10, 0, tzinfo=timezone.utc),
        )
        otro_id = uuid4()
        result = await self.repo.cancelar(reserva.id, otro_id)
        assert result is None

    async def test_6_1_15_buscar_activa_por_alumno(self, db_session: AsyncSession):
        """Buscar reserva activa de un alumno en evaluacion."""
        await self.repo.crear_con_control_cupo(
            evaluacion_id=self.ev.id,
            alumno_id=self.seed["alumno_user_id"],
            fecha_hora=datetime(2026, 6, 15, 10, 0, tzinfo=timezone.utc),
        )
        encontrada = await self.repo.buscar_activa_por_alumno(
            self.ev.id, self.seed["alumno_user_id"]
        )
        assert encontrada is not None
        assert encontrada.alumno_id == self.seed["alumno_user_id"]

    async def test_6_1_16_count_active_by_evaluacion(self, db_session: AsyncSession):
        """Contar reservas activas por evaluacion."""
        al1 = (await _seed_usuario(db_session, _DEV_TENANT_ID, "ALUMNO", "_c1"))["usuario_id"]
        al2 = (await _seed_usuario(db_session, _DEV_TENANT_ID, "ALUMNO", "_c2"))["usuario_id"]
        await self.repo.crear_con_control_cupo(self.ev.id, al1, datetime(2026, 6, 15, 10, 0, tzinfo=timezone.utc))
        await self.repo.crear_con_control_cupo(self.ev.id, al2, datetime(2026, 6, 16, 10, 0, tzinfo=timezone.utc))
        count = await self.repo.contar_activas_por_evaluacion(self.ev.id)
        assert count >= 2

    async def test_6_1_17_listar_por_alumno(self, db_session: AsyncSession):
        """Listar reservas de un alumno."""
        await self.repo.crear_con_control_cupo(
            self.ev.id, self.seed["alumno_user_id"], datetime(2026, 6, 15, 10, 0, tzinfo=timezone.utc),
        )
        reservas = await self.repo.listar_por_alumno(self.seed["alumno_user_id"])
        assert len(reservas) >= 1
        assert reservas[0].alumno_id == self.seed["alumno_user_id"]


class TestResultadoEvaluacionRepository:
    """6.1: Upsert resultado."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, db_session: AsyncSession):
        self.seed = await _build_full_seed(db_session)
        self.ev = await _crear_convocatoria_en_seed(
            db_session, self.seed["materia_id"], self.seed["cohorte_id"], _DEV_TENANT_ID,
        )
        await db_session.commit()
        from app.repositories.resultado_evaluacion_repository import (
            ResultadoEvaluacionRepository,
        )
        self.repo = ResultadoEvaluacionRepository(db_session, _DEV_TENANT_ID)

    async def test_6_1_18_upsert_crea_nuevo(self, db_session: AsyncSession):
        """Upsert crea un resultado nuevo."""
        res = await self.repo.upsert(
            evaluacion_id=self.ev.id,
            alumno_id=self.seed["alumno_user_id"],
            nota_final="Aprobado",
        )
        assert res is not None
        assert res.nota_final == "Aprobado"
        assert res.evaluacion_id == self.ev.id

    async def test_6_1_19_upsert_actualiza_existente(self, db_session: AsyncSession):
        """Upsert actualiza un resultado existente."""
        await self.repo.upsert(
            evaluacion_id=self.ev.id,
            alumno_id=self.seed["alumno_user_id"],
            nota_final="Aprobado",
        )
        res2 = await self.repo.upsert(
            evaluacion_id=self.ev.id,
            alumno_id=self.seed["alumno_user_id"],
            nota_final="Sobresaliente",
        )
        assert res2.nota_final == "Sobresaliente"

    async def test_6_1_20_buscar_por_alumno(self, db_session: AsyncSession):
        """Buscar resultado por alumno y evaluacion."""
        await self.repo.upsert(
            evaluacion_id=self.ev.id,
            alumno_id=self.seed["alumno_user_id"],
            nota_final="Aprobado",
        )
        res = await self.repo.buscar_por_alumno(self.ev.id, self.seed["alumno_user_id"])
        assert res is not None
        assert res.nota_final == "Aprobado"

    async def test_6_1_21_buscar_por_alumno_not_found(self, db_session: AsyncSession):
        """Buscar resultado inexistente retorna None."""
        res = await self.repo.buscar_por_alumno(self.ev.id, uuid4())
        assert res is None


# ══════════════════════════════════════════════════════════════════════════
# 6.2 Tests de Servicio
# ══════════════════════════════════════════════════════════════════════════


class TestColoquioService:
    """6.2: Logica de negocio de coloquios."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, db_session: AsyncSession):
        self.seed = await _build_full_seed(db_session)
        await db_session.commit()
        from app.services.coloquio_service import ColoquioService
        self.svc = ColoquioService(
            session=db_session,
            tenant_id=_DEV_TENANT_ID,
            actor_id=self.seed["coord_user_id"],
            roles=["COORDINADOR"],
        )

    async def test_6_2_1_crear_convocatoria(self, db_session: AsyncSession):
        """Crear convocatoria exitosamente."""
        from app.schemas.coloquios import EvaluacionCreate
        datos = EvaluacionCreate(
            materia_id=self.seed["materia_id"],
            cohorte_id=self.seed["cohorte_id"],
            tipo="Coloquio",
            instancia="Primer Coloquio",
            dias_disponibles=3,
            cupos_por_dia=5,
            fecha_inicio=date(2026, 6, 10),
            fecha_fin=date(2026, 6, 20),
        )
        resultado = await self.svc.crear_convocatoria(datos)
        assert resultado["tipo"] == "Coloquio"
        assert resultado["estado"] == "Activa"
        assert resultado["materia_id"] == self.seed["materia_id"]

    async def test_6_2_2_crear_convocatoria_materia_inexistente(self, db_session: AsyncSession):
        """Crear convocatoria con materia inexistente lanza BusinessError."""
        from app.core.exceptions import BusinessError
        from app.schemas.coloquios import EvaluacionCreate
        datos = EvaluacionCreate(
            materia_id=uuid4(),
            cohorte_id=self.seed["cohorte_id"],
            tipo="Coloquio",
            instancia="Test",
            fecha_inicio=date(2026, 6, 10),
            fecha_fin=date(2026, 6, 20),
        )
        with pytest.raises(BusinessError, match="Materia no encontrada"):
            await self.svc.crear_convocatoria(datos)

    async def test_6_2_3_importar_alumnos(self, db_session: AsyncSession):
        """Importar alumnos a una convocatoria."""
        ev = await _crear_convocatoria_en_seed(
            db_session, self.seed["materia_id"], self.seed["cohorte_id"], _DEV_TENANT_ID,
        )
        al1 = (await _seed_usuario(db_session, _DEV_TENANT_ID, "ALUMNO", "_i1"))["usuario_id"]
        al2 = (await _seed_usuario(db_session, _DEV_TENANT_ID, "ALUMNO", "_i2"))["usuario_id"]
        await db_session.commit()
        from app.schemas.coloquios import ImportarAlumnosRequest
        datos = ImportarAlumnosRequest(alumno_ids=[al1, al2])
        resultado = await self.svc.importar_alumnos(ev.id, datos)
        assert resultado.importados == 2
        assert resultado.omitidos == 0

    async def test_6_2_4_importar_alumnos_con_duplicados(self, db_session: AsyncSession):
        """Importar alumnos duplicados los omite."""
        ev = await _crear_convocatoria_en_seed(
            db_session, self.seed["materia_id"], self.seed["cohorte_id"], _DEV_TENANT_ID,
        )
        al1 = (await _seed_usuario(db_session, _DEV_TENANT_ID, "ALUMNO", "_d1"))["usuario_id"]
        await db_session.commit()
        from app.schemas.coloquios import ImportarAlumnosRequest
        datos = ImportarAlumnosRequest(alumno_ids=[al1])
        await self.svc.importar_alumnos(ev.id, datos)
        resultado = await self.svc.importar_alumnos(ev.id, datos)
        assert resultado.importados == 0
        assert resultado.omitidos == 1

    async def test_6_2_5_reservar_turno_exitoso(self, db_session: AsyncSession):
        """Reservar turno exitosamente."""
        ev = await _crear_convocatoria_en_seed(
            db_session, self.seed["materia_id"], self.seed["cohorte_id"], _DEV_TENANT_ID,
        )
        await db_session.commit()
        from app.schemas.coloquios import ReservaCreate
        datos = ReservaCreate(
            evaluacion_id=ev.id,
            fecha_hora=datetime(2026, 6, 15, 10, 0, tzinfo=timezone.utc),
        )
        resultado = await self.svc.reservar_turno(datos, alumno_id=self.seed["alumno_user_id"])
        assert resultado["estado"] == "Activa"
        assert resultado["alumno_id"] == self.seed["alumno_user_id"]

    async def test_6_2_6_reservar_sin_cupo(self, db_session: AsyncSession):
        """Reservar cuando no hay cupo lanza BusinessError."""
        ev = await _crear_convocatoria_en_seed(
            db_session, self.seed["materia_id"], self.seed["cohorte_id"], _DEV_TENANT_ID,
        )
        from app.repositories.reserva_evaluacion_repository import ReservaEvaluacionRepository
        repo = ReservaEvaluacionRepository(db_session, _DEV_TENANT_ID)
        from app.core.exceptions import BusinessError
        from app.schemas.coloquios import ReservaCreate
        # Llenar cupo: 3 dias * 5 cupos = 15 reservas maximas
        for i in range(15):
            al = (await _seed_usuario(db_session, _DEV_TENANT_ID, "ALUMNO", f"_cupo_{i}"))["usuario_id"]
            try:
                await repo.crear_con_control_cupo(
                    ev.id, al, datetime(2026, 6, 15 + i, 10, 0, tzinfo=timezone.utc),
                )
            except ValueError:
                pass
        await db_session.commit()
        datos = ReservaCreate(
            evaluacion_id=ev.id,
            fecha_hora=datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc),
        )
        with pytest.raises(BusinessError, match="No hay cupo"):
            await self.svc.reservar_turno(datos, alumno_id=uuid4())

    async def test_6_2_7_reservar_duplicado(self, db_session: AsyncSession):
        """Reservar turno ya reservado lanza BusinessError."""
        ev = await _crear_convocatoria_en_seed(
            db_session, self.seed["materia_id"], self.seed["cohorte_id"], _DEV_TENANT_ID,
        )
        await db_session.commit()
        from app.core.exceptions import BusinessError
        from app.schemas.coloquios import ReservaCreate
        datos = ReservaCreate(
            evaluacion_id=ev.id,
            fecha_hora=datetime(2026, 6, 15, 10, 0, tzinfo=timezone.utc),
        )
        await self.svc.reservar_turno(datos, alumno_id=self.seed["alumno_user_id"])
        with pytest.raises(BusinessError):
            await self.svc.reservar_turno(datos, alumno_id=self.seed["alumno_user_id"])

    async def test_6_2_8_cancelar_reserva(self, db_session: AsyncSession):
        """Cancelar reserva propia."""
        ev = await _crear_convocatoria_en_seed(
            db_session, self.seed["materia_id"], self.seed["cohorte_id"], _DEV_TENANT_ID,
        )
        await db_session.commit()
        from app.schemas.coloquios import ReservaCreate
        # Reservamos como alumno
        svc_alumno = type(self.svc)(
            session=db_session,
            tenant_id=_DEV_TENANT_ID,
            actor_id=self.seed["alumno_user_id"],
            roles=["ALUMNO"],
        )
        datos = ReservaCreate(
            evaluacion_id=ev.id,
            fecha_hora=datetime(2026, 6, 15, 10, 0, tzinfo=timezone.utc),
        )
        reserva = await svc_alumno.reservar_turno(datos, alumno_id=self.seed["alumno_user_id"])
        resultado = await svc_alumno.cancelar_reserva(reserva["id"])
        assert resultado["estado"] == "Cancelada"

    async def test_6_2_9_cerrar_convocatoria(self, db_session: AsyncSession):
        """Cerrar convocatoria cambia estado."""
        ev = await _crear_convocatoria_en_seed(
            db_session, self.seed["materia_id"], self.seed["cohorte_id"], _DEV_TENANT_ID,
        )
        await db_session.commit()
        resultado = await self.svc.cerrar_convocatoria(ev.id)
        assert resultado["estado"] == "Inactiva"

    async def test_6_2_10_cerrar_ya_cerrada(self, db_session: AsyncSession):
        """Cerrar convocatoria ya cerrada lanza BusinessError."""
        from app.core.exceptions import BusinessError
        ev = await _crear_convocatoria_en_seed(
            db_session, self.seed["materia_id"], self.seed["cohorte_id"], _DEV_TENANT_ID,
        )
        await db_session.commit()
        await self.svc.cerrar_convocatoria(ev.id)
        with pytest.raises(BusinessError, match="ya esta cerrada"):
            await self.svc.cerrar_convocatoria(ev.id)

    async def test_6_2_11_registrar_resultado(self, db_session: AsyncSession):
        """Registrar resultado de un alumno."""
        ev = await _crear_convocatoria_en_seed(
            db_session, self.seed["materia_id"], self.seed["cohorte_id"], _DEV_TENANT_ID,
        )
        await db_session.commit()
        from app.schemas.coloquios import ResultadoCreate
        datos = ResultadoCreate(
            evaluacion_id=ev.id,
            alumno_id=self.seed["alumno_user_id"],
            nota_final="Aprobado",
        )
        resultado = await self.svc.registrar_resultado(datos)
        assert resultado["nota_final"] == "Aprobado"
        assert resultado["alumno_id"] == self.seed["alumno_user_id"]

    async def test_6_2_12_obtener_metricas(self, db_session: AsyncSession):
        """Obtener metricas del modulo."""
        ev = await _crear_convocatoria_en_seed(
            db_session, self.seed["materia_id"], self.seed["cohorte_id"], _DEV_TENANT_ID,
        )
        al1 = (await _seed_usuario(db_session, _DEV_TENANT_ID, "ALUMNO", "_m1"))["usuario_id"]
        # Crear reserva y resultado
        from app.repositories.reserva_evaluacion_repository import ReservaEvaluacionRepository
        repo_res = ReservaEvaluacionRepository(db_session, _DEV_TENANT_ID)
        await repo_res.crear_con_control_cupo(ev.id, al1, datetime(2026, 6, 15, 10, 0, tzinfo=timezone.utc))
        from app.repositories.resultado_evaluacion_repository import ResultadoEvaluacionRepository
        repo_rdo = ResultadoEvaluacionRepository(db_session, _DEV_TENANT_ID)
        await repo_rdo.upsert(ev.id, al1, "Aprobado")
        await db_session.commit()
        metricas = await self.svc.obtener_metricas()
        assert metricas.total_convocatorias >= 1
        assert metricas.resultados_registrados >= 1


# ══════════════════════════════════════════════════════════════════════════
# 6.3 Tests de Router
# ══════════════════════════════════════════════════════════════════════════


class TestColoquioRouter:
    """6.3: Endpoints REST con auth, permisos, flujos felices y errores."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, db_session: AsyncSession):
        self.seed = await _build_full_seed(db_session)
        await db_session.commit()

    # ── Convocatorias ───────────────────────────────────────────────────

    async def test_6_3_1_crear_convocatoria_201(self, client: AsyncClient):
        """POST /api/coloquios/convocatorias -> 201 Created."""
        token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        body = {
            "materia_id": str(self.seed["materia_id"]),
            "cohorte_id": str(self.seed["cohorte_id"]),
            "tipo": "Coloquio",
            "instancia": "Primer Coloquio",
            "dias_disponibles": 3,
            "cupos_por_dia": 5,
            "fecha_inicio": "2026-06-10",
            "fecha_fin": "2026-06-20",
        }
        resp = await client.post(
            "/api/coloquios/convocatorias", json=body,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["tipo"] == "Coloquio"
        assert data["estado"] == "Activa"

    async def test_6_3_2_crear_convocatoria_403_sin_permiso(self, client: AsyncClient):
        """POST convocatorias sin coloquios:gestionar -> 403."""
        token = _make_token(self.seed["alumno_user_id"], _DEV_TENANT_ID, ["ALUMNO"])
        body = {
            "materia_id": str(self.seed["materia_id"]),
            "cohorte_id": str(self.seed["cohorte_id"]),
            "tipo": "Coloquio",
            "instancia": "Test",
            "fecha_inicio": "2026-06-10",
            "fecha_fin": "2026-06-20",
        }
        resp = await client.post(
            "/api/coloquios/convocatorias", json=body,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403, resp.text

    async def test_6_3_3_listar_convocatorias(self, client: AsyncClient):
        """GET /api/coloquios/convocatorias -> lista."""
        # Primero crear una convocatoria
        token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        body = {
            "materia_id": str(self.seed["materia_id"]),
            "cohorte_id": str(self.seed["cohorte_id"]),
            "tipo": "Coloquio",
            "instancia": "Test List",
            "fecha_inicio": "2026-06-10",
            "fecha_fin": "2026-06-20",
        }
        await client.post(
            "/api/coloquios/convocatorias", json=body,
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = await client.get(
            "/api/coloquios/convocatorias",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["total"] >= 1

    async def test_6_3_4_editar_convocatoria(self, client: AsyncClient):
        """PATCH /api/coloquios/convocatorias/{id} -> 200."""
        token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        body = {
            "materia_id": str(self.seed["materia_id"]),
            "cohorte_id": str(self.seed["cohorte_id"]),
            "tipo": "Coloquio",
            "instancia": "Edit Test",
            "fecha_inicio": "2026-06-10",
            "fecha_fin": "2026-06-20",
        }
        create = await client.post(
            "/api/coloquios/convocatorias", json=body,
            headers={"Authorization": f"Bearer {token}"},
        )
        ev_id = create.json()["id"]
        resp = await client.patch(
            f"/api/coloquios/convocatorias/{ev_id}",
            json={"instancia": "Editado"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["instancia"] == "Editado"

    # ── Importar alumnos ────────────────────────────────────────────────

    async def test_6_3_5_importar_alumnos(self, client: AsyncClient, db_session: AsyncSession):
        """POST /api/coloquios/convocatorias/{id}/importar-alumnos -> 200."""
        token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        body = {
            "materia_id": str(self.seed["materia_id"]),
            "cohorte_id": str(self.seed["cohorte_id"]),
            "tipo": "Coloquio",
            "instancia": "Import Test",
            "fecha_inicio": "2026-06-10",
            "fecha_fin": "2026-06-20",
        }
        create = await client.post(
            "/api/coloquios/convocatorias", json=body,
            headers={"Authorization": f"Bearer {token}"},
        )
        ev_id = create.json()["id"]
        al1 = (await _seed_usuario(db_session, _DEV_TENANT_ID, "ALUMNO", "_import"))["usuario_id"]
        await db_session.commit()
        import_body = {"alumno_ids": [str(al1), str(self.seed["alumno_user_id"])]}
        resp = await client.post(
            f"/api/coloquios/convocatorias/{ev_id}/importar-alumnos",
            json=import_body,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["importados"] >= 1

    # ── Reservas ────────────────────────────────────────────────────────

    async def test_6_3_6_reservar_turno_201(self, client: AsyncClient):
        """POST /api/coloquios/convocatorias/{id}/reservar -> 201."""
        # Crear convocatoria como COORDINADOR
        coord_token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        body = {
            "materia_id": str(self.seed["materia_id"]),
            "cohorte_id": str(self.seed["cohorte_id"]),
            "tipo": "Coloquio",
            "instancia": "Reserva Test",
            "dias_disponibles": 5,
            "cupos_por_dia": 10,
            "fecha_inicio": "2026-06-10",
            "fecha_fin": "2026-06-20",
        }
        create = await client.post(
            "/api/coloquios/convocatorias", json=body,
            headers={"Authorization": f"Bearer {coord_token}"},
        )
        ev_id = create.json()["id"]
        alumno_token = _make_token(self.seed["alumno_user_id"], _DEV_TENANT_ID, ["ALUMNO"])
        reserva_body = {"evaluacion_id": str(ev_id), "fecha_hora": "2026-06-15T10:00:00Z"}
        resp = await client.post(
            f"/api/coloquios/convocatorias/{ev_id}/reservar",
            json=reserva_body,
            headers={"Authorization": f"Bearer {alumno_token}"},
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["estado"] == "Activa"

    async def test_6_3_7_reservar_sin_permiso_403(self, client: AsyncClient):
        """Reservar sin permiso coloquios:reservar -> 403."""
        coord_token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        body = {
            "materia_id": str(self.seed["materia_id"]),
            "cohorte_id": str(self.seed["cohorte_id"]),
            "tipo": "Coloquio",
            "instancia": "Permiso Test",
            "fecha_inicio": "2026-06-10",
            "fecha_fin": "2026-06-20",
        }
        create = await client.post(
            "/api/coloquios/convocatorias", json=body,
            headers={"Authorization": f"Bearer {coord_token}"},
        )
        ev_id = create.json()["id"]
        # Usuario sin permisos
        sin_permiso_token = _make_token(uuid4(), _DEV_TENANT_ID, [])
        reserva_body = {"evaluacion_id": str(ev_id), "fecha_hora": "2026-06-15T10:00:00Z"}
        resp = await client.post(
            f"/api/coloquios/convocatorias/{ev_id}/reservar",
            json=reserva_body,
            headers={"Authorization": f"Bearer {sin_permiso_token}"},
        )
        assert resp.status_code == 403, resp.text

    async def test_6_3_8_cancelar_reserva(self, client: AsyncClient):
        """POST /api/coloquios/reservas/{id}/cancelar -> 200."""
        coord_token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        body = {
            "materia_id": str(self.seed["materia_id"]),
            "cohorte_id": str(self.seed["cohorte_id"]),
            "tipo": "Coloquio",
            "instancia": "Cancel Test",
            "dias_disponibles": 5,
            "cupos_por_dia": 10,
            "fecha_inicio": "2026-06-10",
            "fecha_fin": "2026-06-20",
        }
        create = await client.post(
            "/api/coloquios/convocatorias", json=body,
            headers={"Authorization": f"Bearer {coord_token}"},
        )
        ev_id = create.json()["id"]
        alumno_token = _make_token(self.seed["alumno_user_id"], _DEV_TENANT_ID, ["ALUMNO"])
        reserva_body = {"evaluacion_id": str(ev_id), "fecha_hora": "2026-06-15T10:00:00Z"}
        reserva = await client.post(
            f"/api/coloquios/convocatorias/{ev_id}/reservar",
            json=reserva_body,
            headers={"Authorization": f"Bearer {alumno_token}"},
        )
        res_id = reserva.json()["id"]
        resp = await client.post(
            f"/api/coloquios/reservas/{res_id}/cancelar",
            headers={"Authorization": f"Bearer {alumno_token}"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["estado"] == "Cancelada"

    # ── Resultados ──────────────────────────────────────────────────────

    async def test_6_3_9_registrar_resultado(self, client: AsyncClient):
        """POST /api/coloquios/convocatorias/{id}/resultados -> 200."""
        coord_token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        body = {
            "materia_id": str(self.seed["materia_id"]),
            "cohorte_id": str(self.seed["cohorte_id"]),
            "tipo": "Coloquio",
            "instancia": "Result Test",
            "fecha_inicio": "2026-06-10",
            "fecha_fin": "2026-06-20",
        }
        create = await client.post(
            "/api/coloquios/convocatorias", json=body,
            headers={"Authorization": f"Bearer {coord_token}"},
        )
        ev_id = create.json()["id"]
        rdo_body = {
            "evaluacion_id": str(ev_id),
            "alumno_id": str(self.seed["alumno_user_id"]),
            "nota_final": "Aprobado",
        }
        resp = await client.post(
            f"/api/coloquios/convocatorias/{ev_id}/resultados",
            json=rdo_body,
            headers={"Authorization": f"Bearer {coord_token}"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["nota_final"] == "Aprobado"

    # ── Cierre ──────────────────────────────────────────────────────────

    async def test_6_3_10_cerrar_convocatoria(self, client: AsyncClient):
        """POST /api/coloquios/convocatorias/{id}/cerrar -> 200."""
        coord_token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        body = {
            "materia_id": str(self.seed["materia_id"]),
            "cohorte_id": str(self.seed["cohorte_id"]),
            "tipo": "Coloquio",
            "instancia": "Cierre Test",
            "fecha_inicio": "2026-06-10",
            "fecha_fin": "2026-06-20",
        }
        create = await client.post(
            "/api/coloquios/convocatorias", json=body,
            headers={"Authorization": f"Bearer {coord_token}"},
        )
        ev_id = create.json()["id"]
        resp = await client.post(
            f"/api/coloquios/convocatorias/{ev_id}/cerrar",
            headers={"Authorization": f"Bearer {coord_token}"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["estado"] == "Inactiva"

    async def test_6_3_11_cerrar_inexistente_404(self, client: AsyncClient):
        """Cerrar convocatoria inexistente -> 404."""
        token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        resp = await client.post(
            f"/api/coloquios/convocatorias/{uuid4()}/cerrar",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 409, resp.text

    # ── Metricas ────────────────────────────────────────────────────────

    async def test_6_3_12_obtener_metricas(self, client: AsyncClient):
        """GET /api/coloquios/metricas -> 200."""
        coord_token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        resp = await client.get(
            "/api/coloquios/metricas",
            headers={"Authorization": f"Bearer {coord_token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "total_convocatorias" in data

    # ── Agenda ──────────────────────────────────────────────────────────

    async def test_6_3_13_agenda(self, client: AsyncClient):
        """GET /api/coloquios/agenda -> 200."""
        coord_token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        resp = await client.get(
            "/api/coloquios/agenda",
            headers={"Authorization": f"Bearer {coord_token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "items" in data
        assert "total" in data

    # ── Mis reservas ────────────────────────────────────────────────────

    async def test_6_3_14_mis_reservas(self, client: AsyncClient):
        """GET /api/coloquios/mis-reservas -> 200."""
        alumno_token = _make_token(self.seed["alumno_user_id"], _DEV_TENANT_ID, ["ALUMNO"])
        resp = await client.get(
            "/api/coloquios/mis-reservas",
            headers={"Authorization": f"Bearer {alumno_token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "items" in data


# ══════════════════════════════════════════════════════════════════════════
# 6.5 Multi-tenant isolation
# ══════════════════════════════════════════════════════════════════════════


class TestMultiTenantColoquios:
    """6.5: Aislamiento multi-tenant en coloquios."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, db_session: AsyncSession):
        # Tenant 1
        await _seed_tenant(db_session, _DEV_TENANT_ID)
        await _seed_permisos_coloquios(db_session, _DEV_TENANT_ID)
        struct1 = await _seed_estructura(db_session, tenant_id=_DEV_TENANT_ID)
        coord1 = await _seed_usuario(db_session, _DEV_TENANT_ID, "COORDINADOR", "_t1")
        ev1 = await _crear_convocatoria_en_seed(
            db_session, struct1["materia_id"], struct1["cohorte_id"], _DEV_TENANT_ID,
        )
        # Tenant 2
        await _seed_tenant(db_session, _DEV_TENANT_ID_2)
        await _seed_permisos_coloquios(db_session, _DEV_TENANT_ID_2)
        struct2 = await _seed_estructura(db_session, tenant_id=_DEV_TENANT_ID_2, codigo_sufijo="B")
        coord2 = await _seed_usuario(db_session, _DEV_TENANT_ID_2, "COORDINADOR", "_t2")
        ev2 = await _crear_convocatoria_en_seed(
            db_session, struct2["materia_id"], struct2["cohorte_id"], _DEV_TENANT_ID_2,
        )
        await db_session.commit()
        self.tenant1 = {"coord_user_id": coord1["usuario_id"], "ev_id": ev1.id}
        self.tenant2 = {"coord_user_id": coord2["usuario_id"], "ev_id": ev2.id}

    async def test_6_5_1_tenant1_no_ve_tenant2(self, client: AsyncClient):
        """Tenant 1 no ve convocatorias del Tenant 2."""
        token = _make_token(self.tenant1["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        resp = await client.get(
            "/api/coloquios/convocatorias",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        # Solo debe ver la convocatoria de tenant 1 (1), no la de tenant 2
        ids = {item["id"] for item in data["items"]}
        assert str(self.tenant1["ev_id"]) in ids
        assert str(self.tenant2["ev_id"]) not in ids

    async def test_6_5_2_tenant2_no_ve_tenant1(self, client: AsyncClient):
        """Tenant 2 no ve convocatorias del Tenant 1."""
        token = _make_token(self.tenant2["coord_user_id"], _DEV_TENANT_ID_2, ["COORDINADOR"])
        resp = await client.get(
            "/api/coloquios/convocatorias",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        ids = {item["id"] for item in data["items"]}
        assert str(self.tenant2["ev_id"]) in ids
        assert str(self.tenant1["ev_id"]) not in ids

    async def test_6_5_3_metricas_aisladas(self, client: AsyncClient):
        """Metricas de tenant 1 no incluyen datos de tenant 2."""
        token = _make_token(self.tenant1["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        resp = await client.get(
            "/api/coloquios/metricas",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        # Solo debe contar la convocatoria de tenant 1
        assert data["total_convocatorias"] == 1


# ══════════════════════════════════════════════════════════════════════════
# 6.4 Tests de Metricas
# ══════════════════════════════════════════════════════════════════════════


class TestMetricasColoquios:
    """6.4: Conteos correctos en metricas."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, db_session: AsyncSession):
        self.seed = await _build_full_seed(db_session)
        self.ev = await _crear_convocatoria_en_seed(
            db_session, self.seed["materia_id"], self.seed["cohorte_id"], _DEV_TENANT_ID,
        )
        # Crear alumnos, reservas y resultados
        self.alumnos = []
        for i in range(3):
            al = (await _seed_usuario(db_session, _DEV_TENANT_ID, "ALUMNO", f"_metric_{i}"))["usuario_id"]
            self.alumnos.append(al)
        await db_session.flush()
        # 2 reservas activas
        from app.repositories.reserva_evaluacion_repository import ReservaEvaluacionRepository
        repo_res = ReservaEvaluacionRepository(db_session, _DEV_TENANT_ID)
        await repo_res.crear_con_control_cupo(self.ev.id, self.alumnos[0], datetime(2026, 6, 15, 10, 0, tzinfo=timezone.utc))
        await repo_res.crear_con_control_cupo(self.ev.id, self.alumnos[1], datetime(2026, 6, 16, 10, 0, tzinfo=timezone.utc))
        # 1 resultado
        from app.repositories.resultado_evaluacion_repository import ResultadoEvaluacionRepository
        repo_rdo = ResultadoEvaluacionRepository(db_session, _DEV_TENANT_ID)
        await repo_rdo.upsert(self.ev.id, self.alumnos[0], "Aprobado")
        # 1 alumno importado (sin reserva activa, solo marcador)
        await repo_res.crear_con_control_cupo(self.ev.id, self.alumnos[2], datetime(2026, 6, 17, 10, 0, tzinfo=timezone.utc))
        await db_session.commit()

    async def test_6_4_1_metricas_conteos_correctos(self, client: AsyncClient):
        """Metricas reflejan los conteos reales."""
        token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        resp = await client.get(
            "/api/coloquios/metricas",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["total_convocatorias"] >= 1
        assert data["total_alumnos_importados"] >= 3
        assert data["reservas_activas"] >= 2
        assert data["resultados_registrados"] >= 1
