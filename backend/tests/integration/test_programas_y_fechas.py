"""Tests E2E de Programas de Materia y Fechas Academicas (C-17).

Cubre:
  CRUD de programas de materia (subir, listar, obtener, eliminar),
  CRUD de fechas academicas (crear, listar, obtener, actualizar, eliminar),
  validacion de unicidad, hard/soft delete, exportacion LMS,
  aislamiento multi-tenant, permisos (estructura:gestionar).

Requiere PostgreSQL real (DATABASE_URL_TEST en el entorno).
"""

from __future__ import annotations

from datetime import date, datetime, timezone
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
_DEV_TENANT_ID_2 = UUID("00000000-0000-0000-0000-000000000002")
_SECRET_KEY = "a" * 64

# ── Models ───────────────────────────────────────────────────────────────

from app.models.tenant import Tenant  # noqa: E402
from app.models.permiso import Permiso  # noqa: E402
from app.models.rol import Rol  # noqa: E402
from app.models.rol_permiso import RolPermiso  # noqa: E402
from app.models.materia import Materia  # noqa: E402
from app.models.carrera import Carrera  # noqa: E402
from app.models.cohorte import Cohorte  # noqa: E402
from app.models.usuario import Usuario  # noqa: E402
from app.models.programa_materia import ProgramaMateria  # noqa: E402
from app.models.fecha_academica import FechaAcademica  # noqa: E402
from app.models.enums import TipoFechaAcademica  # noqa: E402
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


async def _seed_permisos_estructura(db_session: AsyncSession, tenant_id: UUID | None = None) -> None:
    tid = tenant_id or _DEV_TENANT_ID
    from sqlalchemy import select as sa_select

    permiso_rows = {
        "estructura:gestionar": "Gestionar estructura academica",
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
        ("COORDINADOR", "Coordinador", "Coordinador"),
        ("ADMIN", "Administrador", "Administrador"),
        ("TUTOR", "Tutor", "Tutor"),
    ]
    rol_ids = {}
    for codigo, nombre, desc in roles_data:
        r = Rol(id=uuid4(), codigo=codigo, nombre=nombre, descripcion=desc, tenant_id=tid)
        db_session.add(r)
        rol_ids[codigo] = r.id

    role_perms = {
        "COORDINADOR": ["estructura:gestionar"],
        "ADMIN": ["estructura:gestionar"],
        "TUTOR": [],
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

    materia = Materia(
        tenant_id=tid, codigo=f"TEST-MAT{suf}", nombre=f"Materia Test{suf}", estado="Activo",
    )
    db_session.add(materia)

    carrera = Carrera(
        tenant_id=tid, codigo=f"TEST-CAR{suf}", nombre=f"Carrera Test{suf}", estado="Activa",
    )
    db_session.add(carrera)
    await db_session.flush()

    cohorte = Cohorte(
        tenant_id=tid, carrera_id=carrera.id, nombre=f"Cohorte{suf}",
        anio=2026, vig_desde=date(2026, 1, 1), estado="Activa",
    )
    db_session.add(cohorte)
    await db_session.flush()

    return {"materia_id": materia.id, "carrera_id": carrera.id, "cohorte_id": cohorte.id}


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
    await _seed_permisos_estructura(db_session, tid)
    struct = await _seed_estructura(db_session, tenant_id=tid)
    coord = await _seed_usuario(db_session, tid, "COORDINADOR", "_coord")
    tutor = await _seed_usuario(db_session, tid, "TUTOR", "_tutor")
    struct["coord_user_id"] = coord["usuario_id"]
    struct["tutor_user_id"] = tutor["usuario_id"]
    return struct


async def _seed_programa(
    db_session: AsyncSession,
    tenant_id: UUID,
    materia_id: UUID,
    carrera_id: UUID,
    cohorte_id: UUID,
    titulo: str = "Programa de prueba",
) -> ProgramaMateria:
    ahora = datetime.now(timezone.utc)
    programa = ProgramaMateria(
        tenant_id=tenant_id,
        materia_id=materia_id,
        carrera_id=carrera_id,
        cohorte_id=cohorte_id,
        titulo=titulo,
        referencia_archivo=uuid4(),
        cargado_at=ahora,
    )
    db_session.add(programa)
    await db_session.flush()
    return programa


async def _seed_fecha(
    db_session: AsyncSession,
    tenant_id: UUID,
    materia_id: UUID,
    cohorte_id: UUID,
    tipo: TipoFechaAcademica = TipoFechaAcademica.PARCIAL,
    numero: int = 1,
    periodo: str = "2026-1",
    titulo: str = "Fecha de prueba",
    days_offset: int = 30,
) -> FechaAcademica:
    from datetime import timedelta

    fecha = FechaAcademica(
        tenant_id=tenant_id,
        materia_id=materia_id,
        cohorte_id=cohorte_id,
        tipo=tipo,
        numero=numero,
        periodo=periodo,
        fecha=date(2026, 4, days_offset),
        titulo=titulo,
    )
    db_session.add(fecha)
    await db_session.flush()
    return fecha


# ══════════════════════════════════════════════════════════════════════════
# 6.1 Tests de Repositorio — ProgramaMateria
# ══════════════════════════════════════════════════════════════════════════


class TestProgramaMateriaRepository:
    """6.1: CRUD ProgramaMateria, unique constraint, filtros, hard delete, tenant scope."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, db_session: AsyncSession):
        self.seed = await _build_full_seed(db_session)
        self.programa = await _seed_programa(
            db_session, _DEV_TENANT_ID,
            self.seed["materia_id"], self.seed["carrera_id"], self.seed["cohorte_id"],
        )
        await db_session.commit()
        from app.repositories.programa_repository import ProgramaMateriaRepository
        self.repo = ProgramaMateriaRepository(db_session, _DEV_TENANT_ID)

    async def test_6_1_1_get_by_id(self, db_session: AsyncSession):
        """Obtener programa por ID."""
        programa = await self.repo.get_by_id(self.programa.id)
        assert programa is not None
        assert programa.id == self.programa.id
        assert programa.titulo == "Programa de prueba"

    async def test_6_1_2_get_by_id_not_found(self, db_session: AsyncSession):
        """get_by_id con ID inexistente retorna None."""
        programa = await self.repo.get_by_id(uuid4())
        assert programa is None

    async def test_6_1_3_create(self, db_session: AsyncSession):
        """Crear programa exitosamente."""
        nuevo = await _seed_programa(
            db_session, _DEV_TENANT_ID,
            self.seed["materia_id"], self.seed["carrera_id"], self.seed["cohorte_id"],
            titulo="Nuevo programa",
        )
        await db_session.commit()
        programa = await self.repo.get_by_id(nuevo.id)
        assert programa is not None
        assert programa.titulo == "Nuevo programa"

    async def test_6_1_4_list_sin_filtros(self, db_session: AsyncSession):
        """Listar programas sin filtros."""
        items = await self.repo.list()
        assert len(items) >= 1

    async def test_6_1_5_list_filtro_materia(self, db_session: AsyncSession):
        """Listar programas filtrado por materia."""
        items = await self.repo.list(materia_id=self.seed["materia_id"])
        assert len(items) >= 1
        assert items[0].materia_id == self.seed["materia_id"]

    async def test_6_1_6_list_filtro_carrera(self, db_session: AsyncSession):
        """Listar programas filtrado por carrera."""
        items = await self.repo.list(carrera_id=self.seed["carrera_id"])
        assert len(items) >= 1
        assert items[0].carrera_id == self.seed["carrera_id"]

    async def test_6_1_7_list_filtro_cohorte(self, db_session: AsyncSession):
        """Listar programas filtrado por cohorte."""
        items = await self.repo.list(cohorte_id=self.seed["cohorte_id"])
        assert len(items) >= 1
        assert items[0].cohorte_id == self.seed["cohorte_id"]

    async def test_6_1_8_list_filtros_combinados(self, db_session: AsyncSession):
        """Listar programas con filtros combinados."""
        items = await self.repo.list(
            materia_id=self.seed["materia_id"],
            carrera_id=self.seed["carrera_id"],
            cohorte_id=self.seed["cohorte_id"],
        )
        assert len(items) >= 1

    async def test_6_1_9_list_sin_resultados(self, db_session: AsyncSession):
        """Listar programas con filtros sin resultados retorna vacio."""
        items = await self.repo.list(materia_id=uuid4())
        assert len(items) == 0

    async def test_6_1_10_hard_delete(self, db_session: AsyncSession):
        """Hard delete elimina fisicamente."""
        programa_id = self.programa.id
        eliminado = await self.repo.delete(programa_id)
        assert eliminado is True

        # Verificar que no existe
        programa = await self.repo.get_by_id(programa_id)
        assert programa is None

    async def test_6_1_11_delete_not_found(self, db_session: AsyncSession):
        """Delete de programa inexistente retorna False."""
        eliminado = await self.repo.delete(uuid4())
        assert eliminado is False

    async def test_6_1_12_tenant_scope(self, db_session: AsyncSession):
        """Repo filtra por tenant automaticamente."""
        otro_tenant = _DEV_TENANT_ID_2
        await _seed_tenant(db_session, otro_tenant)
        await db_session.commit()
        repo_otro = type(self.repo)(db_session, otro_tenant)
        items = await repo_otro.list()
        assert len(items) == 0


# ══════════════════════════════════════════════════════════════════════════
# 6.2 Tests de Repositorio — FechaAcademica
# ══════════════════════════════════════════════════════════════════════════


class TestFechaAcademicaRepository:
    """6.2: CRUD FechaAcademica, unique constraint, soft delete, filtros."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, db_session: AsyncSession):
        self.seed = await _build_full_seed(db_session)
        self.fecha = await _seed_fecha(
            db_session, _DEV_TENANT_ID,
            self.seed["materia_id"], self.seed["cohorte_id"],
        )
        await db_session.commit()
        from app.repositories.fecha_academica_repository import FechaAcademicaRepository
        self.repo = FechaAcademicaRepository(db_session, _DEV_TENANT_ID)

    async def test_6_2_1_get_by_id(self, db_session: AsyncSession):
        """Obtener fecha por ID."""
        fecha = await self.repo.get_by_id(self.fecha.id)
        assert fecha is not None
        assert fecha.id == self.fecha.id
        assert fecha.tipo == TipoFechaAcademica.PARCIAL
        assert fecha.numero == 1

    async def test_6_2_2_get_by_id_not_found(self, db_session: AsyncSession):
        """get_by_id con ID inexistente retorna None."""
        fecha = await self.repo.get_by_id(uuid4())
        assert fecha is None

    async def test_6_2_3_create(self, db_session: AsyncSession):
        """Crear fecha exitosamente."""
        nueva = await _seed_fecha(
            db_session, _DEV_TENANT_ID,
            self.seed["materia_id"], self.seed["cohorte_id"],
            tipo=TipoFechaAcademica.TP, numero=1, titulo="TP de prueba",
        )
        await db_session.commit()
        fecha = await self.repo.get_by_id(nueva.id)
        assert fecha is not None
        assert fecha.tipo == TipoFechaAcademica.TP

    async def test_6_2_4_list_sin_filtros(self, db_session: AsyncSession):
        """Listar fechas sin filtros."""
        items = await self.repo.list()
        assert len(items) >= 1

    async def test_6_2_5_list_filtro_materia(self, db_session: AsyncSession):
        """Listar fechas filtrado por materia."""
        items = await self.repo.list(materia_id=self.seed["materia_id"])
        assert len(items) >= 1
        assert items[0].materia_id == self.seed["materia_id"]

    async def test_6_2_6_list_filtro_cohorte(self, db_session: AsyncSession):
        """Listar fechas filtrado por cohorte."""
        items = await self.repo.list(cohorte_id=self.seed["cohorte_id"])
        assert len(items) >= 1

    async def test_6_2_7_list_filtro_tipo(self, db_session: AsyncSession):
        """Listar fechas filtrado por tipo."""
        items = await self.repo.list(tipo=TipoFechaAcademica.PARCIAL)
        assert len(items) >= 1

    async def test_6_2_8_list_filtro_periodo(self, db_session: AsyncSession):
        """Listar fechas filtrado por periodo."""
        items = await self.repo.list(periodo="2026-1")
        assert len(items) >= 1

    async def test_6_2_9_list_filtros_combinados(self, db_session: AsyncSession):
        """Listar fechas con filtros combinados."""
        items = await self.repo.list(
            materia_id=self.seed["materia_id"],
            cohorte_id=self.seed["cohorte_id"],
            tipo=TipoFechaAcademica.PARCIAL,
            periodo="2026-1",
        )
        assert len(items) >= 1

    async def test_6_2_10_list_sin_resultados(self, db_session: AsyncSession):
        """Listar fechas con filtros sin resultados retorna vacio."""
        items = await self.repo.list(materia_id=uuid4())
        assert len(items) == 0

    async def test_6_2_11_list_orden_fecha_asc(self, db_session: AsyncSession):
        """Fechas ordenadas por fecha ASC."""
        # Crear segunda fecha con fecha anterior
        from datetime import timedelta
        fecha_anterior = await _seed_fecha(
            db_session, _DEV_TENANT_ID,
            self.seed["materia_id"], self.seed["cohorte_id"],
            tipo=TipoFechaAcademica.RECUPERATORIO, numero=1,
            days_offset=15,
        )
        await db_session.commit()
        items = await self.repo.list()
        assert len(items) >= 2
        # Verificar orden ascendente
        for i in range(len(items) - 1):
            assert items[i].fecha <= items[i + 1].fecha

    async def test_6_2_12_soft_delete(self, db_session: AsyncSession):
        """Soft delete marca deleted_at y no aparece en listados."""
        fecha_id = self.fecha.id
        await self.repo.soft_delete(self.fecha)
        await db_session.commit()

        # No aparece en get_by_id (scope query filtra soft-delete)
        fecha = await self.repo.get_by_id(fecha_id)
        assert fecha is None

        # No aparece en listados
        items = await self.repo.list()
        ids = {f.id for f in items}
        assert fecha_id not in ids

    async def test_6_2_13_update(self, db_session: AsyncSession):
        """Actualizar campos de una fecha."""
        actualizada = await self.repo.update(
            self.fecha.id, {"titulo": "Titulo actualizado"},
        )
        assert actualizada is not None
        assert actualizada.titulo == "Titulo actualizado"

    async def test_6_2_14_update_not_found(self, db_session: AsyncSession):
        """Actualizar fecha inexistente retorna None."""
        result = await self.repo.update(uuid4(), {"titulo": "Nope"})
        assert result is None

    async def test_6_2_15_tenant_scope(self, db_session: AsyncSession):
        """Repo filtra por tenant automaticamente."""
        otro_tenant = _DEV_TENANT_ID_2
        await _seed_tenant(db_session, otro_tenant)
        await db_session.commit()
        repo_otro = type(self.repo)(db_session, otro_tenant)
        items = await repo_otro.list()
        assert len(items) == 0


# ══════════════════════════════════════════════════════════════════════════
# 6.3 Tests de Servicio — ProgramaMateria
# ══════════════════════════════════════════════════════════════════════════


class TestProgramaService:
    """6.3: Logica de negocio de programas."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, db_session: AsyncSession):
        self.seed = await _build_full_seed(db_session)
        await db_session.commit()
        from app.services.programa_service import ProgramaService, PERMISO_ESTRUCTURA_GESTIONAR
        self.svc = ProgramaService(
            session=db_session,
            tenant_id=_DEV_TENANT_ID,
            actor_id=self.seed["coord_user_id"],
            roles=[PERMISO_ESTRUCTURA_GESTIONAR],
        )

    async def test_6_3_1_subir_programa(self, db_session: AsyncSession):
        """Subir programa exitosamente."""
        from app.schemas.programas import ProgramaMateriaCreate
        datos = ProgramaMateriaCreate(
            materia_id=self.seed["materia_id"],
            carrera_id=self.seed["carrera_id"],
            cohorte_id=self.seed["cohorte_id"],
            titulo="Programa 2026",
            referencia_archivo=uuid4(),
        )
        resultado = await self.svc.subir_programa(datos)
        assert resultado["titulo"] == "Programa 2026"
        assert resultado["materia_id"] == self.seed["materia_id"]
        assert resultado["carrera_id"] == self.seed["carrera_id"]
        assert resultado["cohorte_id"] == self.seed["cohorte_id"]
        assert "referencia_archivo" in resultado

    async def test_6_3_2_subir_programa_duplicado(self, db_session: AsyncSession):
        """Subir programa duplicado lanza BusinessError."""
        from app.core.exceptions import BusinessError
        from app.schemas.programas import ProgramaMateriaCreate
        datos = ProgramaMateriaCreate(
            materia_id=self.seed["materia_id"],
            carrera_id=self.seed["carrera_id"],
            cohorte_id=self.seed["cohorte_id"],
            titulo="Original",
            referencia_archivo=uuid4(),
        )
        await self.svc.subir_programa(datos)
        with pytest.raises(BusinessError, match="ya existe"):
            await self.svc.subir_programa(datos)

    async def test_6_3_3_subir_programa_materia_inexistente(self, db_session: AsyncSession):
        """Subir programa con materia inexistente lanza BusinessError."""
        from app.core.exceptions import BusinessError
        from app.schemas.programas import ProgramaMateriaCreate
        datos = ProgramaMateriaCreate(
            materia_id=uuid4(),
            carrera_id=self.seed["carrera_id"],
            cohorte_id=self.seed["cohorte_id"],
            titulo="Materia invalida",
            referencia_archivo=uuid4(),
        )
        with pytest.raises(BusinessError, match="no encontrada"):
            await self.svc.subir_programa(datos)

    async def test_6_3_4_subir_programa_carrera_inexistente(self, db_session: AsyncSession):
        """Subir programa con carrera inexistente lanza BusinessError."""
        from app.core.exceptions import BusinessError
        from app.schemas.programas import ProgramaMateriaCreate
        datos = ProgramaMateriaCreate(
            materia_id=self.seed["materia_id"],
            carrera_id=uuid4(),
            cohorte_id=self.seed["cohorte_id"],
            titulo="Carrera invalida",
            referencia_archivo=uuid4(),
        )
        with pytest.raises(BusinessError, match="no encontrada"):
            await self.svc.subir_programa(datos)

    async def test_6_3_5_subir_programa_cohorte_inexistente(self, db_session: AsyncSession):
        """Subir programa con cohorte inexistente lanza BusinessError."""
        from app.core.exceptions import BusinessError
        from app.schemas.programas import ProgramaMateriaCreate
        datos = ProgramaMateriaCreate(
            materia_id=self.seed["materia_id"],
            carrera_id=self.seed["carrera_id"],
            cohorte_id=uuid4(),
            titulo="Cohorte invalida",
            referencia_archivo=uuid4(),
        )
        with pytest.raises(BusinessError, match="no encontrada"):
            await self.svc.subir_programa(datos)

    async def test_6_3_6_listar_programas(self, db_session: AsyncSession):
        """Listar programas."""
        await _seed_programa(
            db_session, _DEV_TENANT_ID,
            self.seed["materia_id"], self.seed["carrera_id"], self.seed["cohorte_id"],
            titulo="PG-1",
        )
        await db_session.commit()
        resultado = await self.svc.listar_programas()
        assert resultado["total"] >= 1
        assert "items" in resultado

    async def test_6_3_7_listar_programas_filtros(self, db_session: AsyncSession):
        """Listar programas con filtro de materia."""
        await _seed_programa(
            db_session, _DEV_TENANT_ID,
            self.seed["materia_id"], self.seed["carrera_id"], self.seed["cohorte_id"],
        )
        await db_session.commit()
        resultado = await self.svc.listar_programas(
            materia_id=self.seed["materia_id"],
        )
        assert resultado["total"] >= 1

    async def test_6_3_8_obtener_programa(self, db_session: AsyncSession):
        """Obtener detalle de programa."""
        programa = await _seed_programa(
            db_session, _DEV_TENANT_ID,
            self.seed["materia_id"], self.seed["carrera_id"], self.seed["cohorte_id"],
        )
        await db_session.commit()
        resultado = await self.svc.obtener_programa(programa.id)
        assert resultado["id"] == programa.id
        assert "referencia_archivo" in resultado

    async def test_6_3_9_obtener_programa_inexistente(self, db_session: AsyncSession):
        """Obtener programa inexistente lanza BusinessError."""
        from app.core.exceptions import BusinessError
        with pytest.raises(BusinessError, match="no encontrado"):
            await self.svc.obtener_programa(uuid4())

    async def test_6_3_10_eliminar_programa(self, db_session: AsyncSession):
        """Eliminar programa (hard delete)."""
        programa = await _seed_programa(
            db_session, _DEV_TENANT_ID,
            self.seed["materia_id"], self.seed["carrera_id"], self.seed["cohorte_id"],
        )
        await db_session.commit()
        await self.svc.eliminar_programa(programa.id)
        # Verificar que ya no existe
        from app.core.exceptions import BusinessError
        with pytest.raises(BusinessError, match="no encontrado"):
            await self.svc.obtener_programa(programa.id)

    async def test_6_3_11_eliminar_programa_inexistente(self, db_session: AsyncSession):
        """Eliminar programa inexistente lanza BusinessError."""
        from app.core.exceptions import BusinessError
        with pytest.raises(BusinessError, match="no encontrado"):
            await self.svc.eliminar_programa(uuid4())

    async def test_6_3_12_audit_subir(self, db_session: AsyncSession):
        """Subir programa genera audit log PROGRAMA_SUBIR."""
        from sqlalchemy import select as sa_select
        from app.schemas.programas import ProgramaMateriaCreate
        datos = ProgramaMateriaCreate(
            materia_id=self.seed["materia_id"],
            carrera_id=self.seed["carrera_id"],
            cohorte_id=self.seed["cohorte_id"],
            titulo="Programa auditado",
            referencia_archivo=uuid4(),
        )
        await self.svc.subir_programa(datos)

        stmt = sa_select(AuditLog).where(AuditLog.accion == "PROGRAMA_SUBIR")
        logs = (await db_session.scalars(stmt)).all()
        assert len(logs) >= 1

    async def test_6_3_13_audit_eliminar(self, db_session: AsyncSession):
        """Eliminar programa genera audit log PROGRAMA_ELIMINAR."""
        from sqlalchemy import select as sa_select
        programa = await _seed_programa(
            db_session, _DEV_TENANT_ID,
            self.seed["materia_id"], self.seed["carrera_id"], self.seed["cohorte_id"],
        )
        await db_session.commit()
        await self.svc.eliminar_programa(programa.id)

        stmt = sa_select(AuditLog).where(AuditLog.accion == "PROGRAMA_ELIMINAR")
        logs = (await db_session.scalars(stmt)).all()
        assert len(logs) >= 1


# ══════════════════════════════════════════════════════════════════════════
# 6.4 Tests de Servicio — FechaAcademica
# ══════════════════════════════════════════════════════════════════════════


class TestFechaAcademicaService:
    """6.4: Logica de negocio de fechas academicas."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, db_session: AsyncSession):
        self.seed = await _build_full_seed(db_session)
        await db_session.commit()
        from app.services.fecha_academica_service import (
            FechaAcademicaService,
            PERMISO_ESTRUCTURA_GESTIONAR,
        )
        self.svc = FechaAcademicaService(
            session=db_session,
            tenant_id=_DEV_TENANT_ID,
            actor_id=self.seed["coord_user_id"],
            roles=[PERMISO_ESTRUCTURA_GESTIONAR],
        )

    async def test_6_4_1_crear_fecha(self, db_session: AsyncSession):
        """Crear fecha exitosamente."""
        from app.schemas.fechas_academicas import FechaAcademicaCreate
        datos = FechaAcademicaCreate(
            materia_id=self.seed["materia_id"],
            cohorte_id=self.seed["cohorte_id"],
            tipo=TipoFechaAcademica.PARCIAL,
            numero=1,
            periodo="2026-1",
            fecha=date(2026, 4, 15),
            titulo="1er Parcial",
        )
        resultado = await self.svc.crear_fecha(datos)
        assert resultado["titulo"] == "1er Parcial"
        assert resultado["tipo"] == "Parcial"
        assert resultado["numero"] == 1
        assert resultado["materia_id"] == self.seed["materia_id"]

    async def test_6_4_2_crear_fecha_duplicada(self, db_session: AsyncSession):
        """Crear fecha duplicada lanza BusinessError."""
        from app.core.exceptions import BusinessError
        from app.schemas.fechas_academicas import FechaAcademicaCreate
        datos = FechaAcademicaCreate(
            materia_id=self.seed["materia_id"],
            cohorte_id=self.seed["cohorte_id"],
            tipo=TipoFechaAcademica.PARCIAL,
            numero=1,
            periodo="2026-1",
            fecha=date(2026, 4, 15),
            titulo="1er Parcial",
        )
        await self.svc.crear_fecha(datos)
        with pytest.raises(BusinessError, match="ya existe"):
            await self.svc.crear_fecha(datos)

    async def test_6_4_3_crear_fecha_materia_inexistente(self, db_session: AsyncSession):
        """Crear fecha con materia inexistente lanza BusinessError."""
        from app.core.exceptions import BusinessError
        from app.schemas.fechas_academicas import FechaAcademicaCreate
        datos = FechaAcademicaCreate(
            materia_id=uuid4(),
            cohorte_id=self.seed["cohorte_id"],
            tipo=TipoFechaAcademica.PARCIAL,
            numero=1,
            periodo="2026-1",
            fecha=date(2026, 4, 15),
            titulo="Materia invalida",
        )
        with pytest.raises(BusinessError, match="no encontrada"):
            await self.svc.crear_fecha(datos)

    async def test_6_4_4_crear_fecha_cohorte_inexistente(self, db_session: AsyncSession):
        """Crear fecha con cohorte inexistente lanza BusinessError."""
        from app.core.exceptions import BusinessError
        from app.schemas.fechas_academicas import FechaAcademicaCreate
        datos = FechaAcademicaCreate(
            materia_id=self.seed["materia_id"],
            cohorte_id=uuid4(),
            tipo=TipoFechaAcademica.PARCIAL,
            numero=1,
            periodo="2026-1",
            fecha=date(2026, 4, 15),
            titulo="Cohorte invalida",
        )
        with pytest.raises(BusinessError, match="no encontrada"):
            await self.svc.crear_fecha(datos)

    async def test_6_4_5_crear_fecha_mismo_tipo_distinto_numero(self, db_session: AsyncSession):
        """Crear segunda fecha con mismo tipo pero distinto numero es valido."""
        from app.schemas.fechas_academicas import FechaAcademicaCreate
        d1 = FechaAcademicaCreate(
            materia_id=self.seed["materia_id"],
            cohorte_id=self.seed["cohorte_id"],
            tipo=TipoFechaAcademica.PARCIAL,
            numero=1,
            periodo="2026-1",
            fecha=date(2026, 4, 15),
            titulo="1er Parcial",
        )
        d2 = FechaAcademicaCreate(
            materia_id=self.seed["materia_id"],
            cohorte_id=self.seed["cohorte_id"],
            tipo=TipoFechaAcademica.PARCIAL,
            numero=2,
            periodo="2026-1",
            fecha=date(2026, 6, 15),
            titulo="2do Parcial",
        )
        r1 = await self.svc.crear_fecha(d1)
        r2 = await self.svc.crear_fecha(d2)
        assert r1["numero"] == 1
        assert r2["numero"] == 2

    async def test_6_4_6_listar_fechas(self, db_session: AsyncSession):
        """Listar fechas."""
        from app.schemas.fechas_academicas import FechaAcademicaCreate
        datos = FechaAcademicaCreate(
            materia_id=self.seed["materia_id"],
            cohorte_id=self.seed["cohorte_id"],
            tipo=TipoFechaAcademica.PARCIAL,
            numero=1,
            periodo="2026-1",
            fecha=date(2026, 4, 15),
            titulo="1er Parcial",
        )
        await self.svc.crear_fecha(datos)
        resultado = await self.svc.listar_fechas()
        assert resultado["total"] >= 1

    async def test_6_4_7_listar_fechas_filtros(self, db_session: AsyncSession):
        """Listar fechas con filtros."""
        from app.schemas.fechas_academicas import FechaAcademicaCreate
        datos = FechaAcademicaCreate(
            materia_id=self.seed["materia_id"],
            cohorte_id=self.seed["cohorte_id"],
            tipo=TipoFechaAcademica.PARCIAL,
            numero=1,
            periodo="2026-1",
            fecha=date(2026, 4, 15),
            titulo="1er Parcial",
        )
        await self.svc.crear_fecha(datos)
        resultado = await self.svc.listar_fechas(
            materia_id=self.seed["materia_id"],
            periodo="2026-1",
        )
        assert resultado["total"] >= 1

    async def test_6_4_8_obtener_fecha(self, db_session: AsyncSession):
        """Obtener detalle de fecha."""
        from app.schemas.fechas_academicas import FechaAcademicaCreate
        datos = FechaAcademicaCreate(
            materia_id=self.seed["materia_id"],
            cohorte_id=self.seed["cohorte_id"],
            tipo=TipoFechaAcademica.PARCIAL,
            numero=1,
            periodo="2026-1",
            fecha=date(2026, 4, 15),
            titulo="1er Parcial",
        )
        creada = await self.svc.crear_fecha(datos)
        resultado = await self.svc.obtener_fecha(creada["id"])
        assert resultado["id"] == creada["id"]

    async def test_6_4_9_obtener_fecha_inexistente(self, db_session: AsyncSession):
        """Obtener fecha inexistente lanza BusinessError."""
        from app.core.exceptions import BusinessError
        with pytest.raises(BusinessError, match="no encontrada"):
            await self.svc.obtener_fecha(uuid4())

    async def test_6_4_10_actualizar_fecha(self, db_session: AsyncSession):
        """Actualizar fecha exitosamente."""
        from app.schemas.fechas_academicas import (
            FechaAcademicaCreate,
            FechaAcademicaUpdate,
        )
        datos = FechaAcademicaCreate(
            materia_id=self.seed["materia_id"],
            cohorte_id=self.seed["cohorte_id"],
            tipo=TipoFechaAcademica.PARCIAL,
            numero=1,
            periodo="2026-1",
            fecha=date(2026, 4, 15),
            titulo="1er Parcial",
        )
        creada = await self.svc.crear_fecha(datos)
        update = FechaAcademicaUpdate(titulo="1er Parcial - Modificado")
        resultado = await self.svc.actualizar_fecha(creada["id"], update)
        assert resultado["titulo"] == "1er Parcial - Modificado"

    async def test_6_4_11_actualizar_fecha_con_duplicado(self, db_session: AsyncSession):
        """Actualizar fecha a combinacion duplicada lanza BusinessError."""
        from app.core.exceptions import BusinessError
        from app.schemas.fechas_academicas import (
            FechaAcademicaCreate,
            FechaAcademicaUpdate,
        )
        d1 = FechaAcademicaCreate(
            materia_id=self.seed["materia_id"],
            cohorte_id=self.seed["cohorte_id"],
            tipo=TipoFechaAcademica.PARCIAL,
            numero=1,
            periodo="2026-1",
            fecha=date(2026, 4, 15),
            titulo="1er Parcial",
        )
        d2 = FechaAcademicaCreate(
            materia_id=self.seed["materia_id"],
            cohorte_id=self.seed["cohorte_id"],
            tipo=TipoFechaAcademica.TP,
            numero=1,
            periodo="2026-1",
            fecha=date(2026, 5, 15),
            titulo="TP 1",
        )
        c1 = await self.svc.crear_fecha(d1)
        await self.svc.crear_fecha(d2)

        # Intentar cambiar el tipo de c1 a TP que ya existe
        update = FechaAcademicaUpdate(tipo=TipoFechaAcademica.TP)
        with pytest.raises(BusinessError, match="ya existe"):
            await self.svc.actualizar_fecha(c1["id"], update)

    async def test_6_4_12_actualizar_fecha_inexistente(self, db_session: AsyncSession):
        """Actualizar fecha inexistente lanza BusinessError."""
        from app.core.exceptions import BusinessError
        from app.schemas.fechas_academicas import FechaAcademicaUpdate
        update = FechaAcademicaUpdate(titulo="No existe")
        with pytest.raises(BusinessError, match="no encontrada"):
            await self.svc.actualizar_fecha(uuid4(), update)

    async def test_6_4_13_eliminar_fecha_soft_delete(self, db_session: AsyncSession):
        """Eliminar fecha (soft delete) la oculta de listados."""
        from app.schemas.fechas_academicas import FechaAcademicaCreate
        datos = FechaAcademicaCreate(
            materia_id=self.seed["materia_id"],
            cohorte_id=self.seed["cohorte_id"],
            tipo=TipoFechaAcademica.PARCIAL,
            numero=1,
            periodo="2026-1",
            fecha=date(2026, 4, 15),
            titulo="1er Parcial",
        )
        creada = await self.svc.crear_fecha(datos)
        await self.svc.eliminar_fecha(creada["id"])

        # No aparece en listado
        resultado = await self.svc.listar_fechas()
        ids = {item["id"] for item in resultado["items"]}
        assert creada["id"] not in ids

        # No se puede obtener por detalle
        from app.core.exceptions import BusinessError
        with pytest.raises(BusinessError, match="no encontrada"):
            await self.svc.obtener_fecha(creada["id"])

    async def test_6_4_14_eliminar_fecha_inexistente(self, db_session: AsyncSession):
        """Eliminar fecha inexistente lanza BusinessError."""
        from app.core.exceptions import BusinessError
        with pytest.raises(BusinessError, match="no encontrada"):
            await self.svc.eliminar_fecha(uuid4())

    async def test_6_4_15_export_lms_con_fechas(self, db_session: AsyncSession):
        """Export LMS genera HTML con tabla de fechas."""
        from app.schemas.fechas_academicas import FechaAcademicaCreate
        datos = FechaAcademicaCreate(
            materia_id=self.seed["materia_id"],
            cohorte_id=self.seed["cohorte_id"],
            tipo=TipoFechaAcademica.PARCIAL,
            numero=1,
            periodo="2026-1",
            fecha=date(2026, 4, 15),
            titulo="1er Parcial",
        )
        await self.svc.crear_fecha(datos)
        resultado = await self.svc.generar_lms_export(
            self.seed["materia_id"],
            self.seed["cohorte_id"],
        )
        html = resultado["contenido_html"]
        assert "<table" in html
        assert "Parcial" in html
        assert "1er Parcial" in html
        assert "2026-04-15" in html

    async def test_6_4_16_export_lms_sin_fechas(self, db_session: AsyncSession):
        """Export LMS sin fechas registradas."""
        resultado = await self.svc.generar_lms_export(
            self.seed["materia_id"],
            self.seed["cohorte_id"],
        )
        html = resultado["contenido_html"]
        assert "No hay fechas registradas" in html

    async def test_6_4_17_audit_crear(self, db_session: AsyncSession):
        """Crear fecha genera audit log FECHA_ACADEMICA_CREAR."""
        from sqlalchemy import select as sa_select
        from app.schemas.fechas_academicas import FechaAcademicaCreate
        datos = FechaAcademicaCreate(
            materia_id=self.seed["materia_id"],
            cohorte_id=self.seed["cohorte_id"],
            tipo=TipoFechaAcademica.PARCIAL,
            numero=1,
            periodo="2026-1",
            fecha=date(2026, 4, 15),
            titulo="Fecha auditada",
        )
        await self.svc.crear_fecha(datos)

        stmt = sa_select(AuditLog).where(AuditLog.accion == "FECHA_ACADEMICA_CREAR")
        logs = (await db_session.scalars(stmt)).all()
        assert len(logs) >= 1

    async def test_6_4_18_audit_modificar(self, db_session: AsyncSession):
        """Actualizar fecha genera audit log FECHA_ACADEMICA_MODIFICAR."""
        from sqlalchemy import select as sa_select
        from app.schemas.fechas_academicas import (
            FechaAcademicaCreate,
            FechaAcademicaUpdate,
        )
        datos = FechaAcademicaCreate(
            materia_id=self.seed["materia_id"],
            cohorte_id=self.seed["cohorte_id"],
            tipo=TipoFechaAcademica.PARCIAL,
            numero=1,
            periodo="2026-1",
            fecha=date(2026, 4, 15),
            titulo="Original",
        )
        creada = await self.svc.crear_fecha(datos)
        update = FechaAcademicaUpdate(titulo="Modificada")
        await self.svc.actualizar_fecha(creada["id"], update)

        stmt = sa_select(AuditLog).where(AuditLog.accion == "FECHA_ACADEMICA_MODIFICAR")
        logs = (await db_session.scalars(stmt)).all()
        assert len(logs) >= 1

    async def test_6_4_19_audit_eliminar(self, db_session: AsyncSession):
        """Eliminar fecha genera audit log FECHA_ACADEMICA_ELIMINAR."""
        from sqlalchemy import select as sa_select
        from app.schemas.fechas_academicas import FechaAcademicaCreate
        datos = FechaAcademicaCreate(
            materia_id=self.seed["materia_id"],
            cohorte_id=self.seed["cohorte_id"],
            tipo=TipoFechaAcademica.PARCIAL,
            numero=1,
            periodo="2026-1",
            fecha=date(2026, 4, 15),
            titulo="AEliminar",
        )
        creada = await self.svc.crear_fecha(datos)
        await self.svc.eliminar_fecha(creada["id"])

        stmt = sa_select(AuditLog).where(AuditLog.accion == "FECHA_ACADEMICA_ELIMINAR")
        logs = (await db_session.scalars(stmt)).all()
        assert len(logs) >= 1


# ══════════════════════════════════════════════════════════════════════════
# 6.5 Tests de Router
# ══════════════════════════════════════════════════════════════════════════


class TestProgramasRouter:
    """6.5: Endpoints REST de programas con auth, permisos."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, db_session: AsyncSession):
        self.seed = await _build_full_seed(db_session)
        await db_session.commit()

    # ── POST /api/programas ──────────────────────────────────────────────

    async def test_6_5_1_subir_programa_201(self, client: AsyncClient):
        """POST /api/programas -> 201 Created."""
        token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        body = {
            "materia_id": str(self.seed["materia_id"]),
            "carrera_id": str(self.seed["carrera_id"]),
            "cohorte_id": str(self.seed["cohorte_id"]),
            "titulo": "Programa HTTP test",
            "referencia_archivo": str(uuid4()),
        }
        resp = await client.post(
            "/api/programas", json=body,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["titulo"] == "Programa HTTP test"
        assert data["materia_id"] == str(self.seed["materia_id"])

    async def test_6_5_2_subir_programa_409_duplicado(self, client: AsyncClient):
        """POST /api/programas duplicado -> 409 Conflict."""
        token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        body = {
            "materia_id": str(self.seed["materia_id"]),
            "carrera_id": str(self.seed["carrera_id"]),
            "cohorte_id": str(self.seed["cohorte_id"]),
            "titulo": "Programa HTTP test",
            "referencia_archivo": str(uuid4()),
        }
        resp1 = await client.post(
            "/api/programas", json=body,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp1.status_code == 201, resp1.text
        resp2 = await client.post(
            "/api/programas", json=body,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp2.status_code == 409, resp2.text

    async def test_6_5_3_subir_programa_403_sin_permiso(self, client: AsyncClient):
        """POST /api/programas sin estructura:gestionar -> 403."""
        token = _make_token(self.seed["tutor_user_id"], _DEV_TENANT_ID, ["TUTOR"])
        body = {
            "materia_id": str(self.seed["materia_id"]),
            "carrera_id": str(self.seed["carrera_id"]),
            "cohorte_id": str(self.seed["cohorte_id"]),
            "titulo": "Sin permiso",
            "referencia_archivo": str(uuid4()),
        }
        resp = await client.post(
            "/api/programas", json=body,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403, resp.text

    # ── GET /api/programas ───────────────────────────────────────────────

    async def test_6_5_4_listar_programas(self, client: AsyncClient):
        """GET /api/programas -> lista."""
        token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        resp = await client.get(
            "/api/programas",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "items" in data
        assert "total" in data

    async def test_6_5_5_listar_programas_filtros(self, client: AsyncClient):
        """GET /api/programas?materia_id=... -> filtrado."""
        token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        resp = await client.get(
            f"/api/programas?materia_id={self.seed['materia_id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "items" in data

    # ── GET /api/programas/{id} ──────────────────────────────────────────

    async def test_6_5_6_obtener_programa(self, client: AsyncClient):
        """GET /api/programas/{id} -> detalle con referencia_archivo."""
        token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        created = (await client.post(
            "/api/programas",
            json={
                "materia_id": str(self.seed["materia_id"]),
                "carrera_id": str(self.seed["carrera_id"]),
                "cohorte_id": str(self.seed["cohorte_id"]),
                "titulo": "Detalle test",
                "referencia_archivo": str(uuid4()),
            },
            headers={"Authorization": f"Bearer {token}"},
        )).json()
        resp = await client.get(
            f"/api/programas/{created['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["id"] == created["id"]
        assert "referencia_archivo" in data

    async def test_6_5_7_obtener_programa_404(self, client: AsyncClient):
        """GET /api/programas/{id} inexistente -> 404."""
        token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        resp = await client.get(
            f"/api/programas/{uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404, resp.text

    # ── DELETE /api/programas/{id} ───────────────────────────────────────

    async def test_6_5_8_eliminar_programa_204(self, client: AsyncClient):
        """DELETE /api/programas/{id} -> 204 No Content."""
        token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        created = (await client.post(
            "/api/programas",
            json={
                "materia_id": str(self.seed["materia_id"]),
                "carrera_id": str(self.seed["carrera_id"]),
                "cohorte_id": str(self.seed["cohorte_id"]),
                "titulo": "AEliminar",
                "referencia_archivo": str(uuid4()),
            },
            headers={"Authorization": f"Bearer {token}"},
        )).json()
        resp = await client.delete(
            f"/api/programas/{created['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 204, resp.text

    async def test_6_5_9_eliminar_programa_404(self, client: AsyncClient):
        """DELETE /api/programas/{id} inexistente -> 404."""
        token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        resp = await client.delete(
            f"/api/programas/{uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404, resp.text


class TestFechasAcademicasRouter:
    """6.5: Endpoints REST de fechas academicas con auth, permisos."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, db_session: AsyncSession):
        self.seed = await _build_full_seed(db_session)
        await db_session.commit()

    # ── POST /api/fechas-academicas ──────────────────────────────────────

    async def test_6_5_10_crear_fecha_201(self, client: AsyncClient):
        """POST /api/fechas-academicas -> 201 Created."""
        token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        body = {
            "materia_id": str(self.seed["materia_id"]),
            "cohorte_id": str(self.seed["cohorte_id"]),
            "tipo": "Parcial",
            "numero": 1,
            "periodo": "2026-1",
            "fecha": "2026-04-15",
            "titulo": "1er Parcial HTTP",
        }
        resp = await client.post(
            "/api/fechas-academicas", json=body,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["titulo"] == "1er Parcial HTTP"
        assert data["tipo"] == "Parcial"

    async def test_6_5_11_crear_fecha_409_duplicado(self, client: AsyncClient):
        """POST /api/fechas-academicas duplicado -> 409."""
        token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        body = {
            "materia_id": str(self.seed["materia_id"]),
            "cohorte_id": str(self.seed["cohorte_id"]),
            "tipo": "Parcial",
            "numero": 1,
            "periodo": "2026-1",
            "fecha": "2026-04-15",
            "titulo": "1er Parcial HTTP",
        }
        resp1 = await client.post(
            "/api/fechas-academicas", json=body,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp1.status_code == 201, resp1.text
        resp2 = await client.post(
            "/api/fechas-academicas", json=body,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp2.status_code == 409, resp2.text

    async def test_6_5_12_crear_fecha_403_sin_permiso(self, client: AsyncClient):
        """POST /api/fechas-academicas sin permiso -> 403."""
        token = _make_token(self.seed["tutor_user_id"], _DEV_TENANT_ID, ["TUTOR"])
        body = {
            "materia_id": str(self.seed["materia_id"]),
            "cohorte_id": str(self.seed["cohorte_id"]),
            "tipo": "Parcial",
            "numero": 1,
            "periodo": "2026-1",
            "fecha": "2026-04-15",
            "titulo": "Sin permiso",
        }
        resp = await client.post(
            "/api/fechas-academicas", json=body,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403, resp.text

    # ── GET /api/fechas-academicas ───────────────────────────────────────

    async def test_6_5_13_listar_fechas(self, client: AsyncClient):
        """GET /api/fechas-academicas -> lista."""
        token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        resp = await client.get(
            "/api/fechas-academicas",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "items" in data
        assert "total" in data

    async def test_6_5_14_listar_fechas_filtro_materia_cohorte(self, client: AsyncClient):
        """GET /api/fechas-academicas?materia_id=X&cohorte_id=Y -> filtrado."""
        token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        # Crear una fecha primero
        await client.post(
            "/api/fechas-academicas",
            json={
                "materia_id": str(self.seed["materia_id"]),
                "cohorte_id": str(self.seed["cohorte_id"]),
                "tipo": "Parcial",
                "numero": 1,
                "periodo": "2026-1",
                "fecha": "2026-04-15",
                "titulo": "Filtro test",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = await client.get(
            f"/api/fechas-academicas?materia_id={self.seed['materia_id']}&cohorte_id={self.seed['cohorte_id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["total"] >= 1

    # ── GET /api/fechas-academicas/{id} ──────────────────────────────────

    async def test_6_5_15_obtener_fecha(self, client: AsyncClient):
        """GET /api/fechas-academicas/{id} -> detalle."""
        token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        created = (await client.post(
            "/api/fechas-academicas",
            json={
                "materia_id": str(self.seed["materia_id"]),
                "cohorte_id": str(self.seed["cohorte_id"]),
                "tipo": "Parcial",
                "numero": 1,
                "periodo": "2026-1",
                "fecha": "2026-04-15",
                "titulo": "Detalle test",
            },
            headers={"Authorization": f"Bearer {token}"},
        )).json()
        resp = await client.get(
            f"/api/fechas-academicas/{created['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["id"] == created["id"]

    async def test_6_5_16_obtener_fecha_404(self, client: AsyncClient):
        """GET /api/fechas-academicas/{id} inexistente -> 404."""
        token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        resp = await client.get(
            f"/api/fechas-academicas/{uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404, resp.text

    # ── PATCH /api/fechas-academicas/{id} ────────────────────────────────

    async def test_6_5_17_actualizar_fecha(self, client: AsyncClient):
        """PATCH /api/fechas-academicas/{id} -> 200."""
        token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        created = (await client.post(
            "/api/fechas-academicas",
            json={
                "materia_id": str(self.seed["materia_id"]),
                "cohorte_id": str(self.seed["cohorte_id"]),
                "tipo": "Parcial",
                "numero": 1,
                "periodo": "2026-1",
                "fecha": "2026-04-15",
                "titulo": "Original",
            },
            headers={"Authorization": f"Bearer {token}"},
        )).json()
        resp = await client.patch(
            f"/api/fechas-academicas/{created['id']}",
            json={"titulo": "Actualizado"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["titulo"] == "Actualizado"

    async def test_6_5_18_actualizar_fecha_409_duplicado(self, client: AsyncClient):
        """PATCH a combinacion duplicada -> 409."""
        token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        # Crear dos fechas: Parcial 1 y TP 1
        c1 = (await client.post(
            "/api/fechas-academicas",
            json={
                "materia_id": str(self.seed["materia_id"]),
                "cohorte_id": str(self.seed["cohorte_id"]),
                "tipo": "Parcial",
                "numero": 1,
                "periodo": "2026-1",
                "fecha": "2026-04-15",
                "titulo": "P1",
            },
            headers={"Authorization": f"Bearer {token}"},
        )).json()
        await client.post(
            "/api/fechas-academicas",
            json={
                "materia_id": str(self.seed["materia_id"]),
                "cohorte_id": str(self.seed["cohorte_id"]),
                "tipo": "TP",
                "numero": 1,
                "periodo": "2026-1",
                "fecha": "2026-05-15",
                "titulo": "TP1",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        # Intentar cambiar P1 a TP -> deberia ser 409
        resp = await client.patch(
            f"/api/fechas-academicas/{c1['id']}",
            json={"tipo": "TP"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 409, resp.text

    async def test_6_5_19_actualizar_fecha_404(self, client: AsyncClient):
        """PATCH fecha inexistente -> 404."""
        token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        resp = await client.patch(
            f"/api/fechas-academicas/{uuid4()}",
            json={"titulo": "Nope"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404, resp.text

    # ── DELETE /api/fechas-academicas/{id} ───────────────────────────────

    async def test_6_5_20_eliminar_fecha_204(self, client: AsyncClient):
        """DELETE /api/fechas-academicas/{id} -> 204 (soft delete)."""
        token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        created = (await client.post(
            "/api/fechas-academicas",
            json={
                "materia_id": str(self.seed["materia_id"]),
                "cohorte_id": str(self.seed["cohorte_id"]),
                "tipo": "Parcial",
                "numero": 1,
                "periodo": "2026-1",
                "fecha": "2026-04-15",
                "titulo": "AEliminar",
            },
            headers={"Authorization": f"Bearer {token}"},
        )).json()
        resp = await client.delete(
            f"/api/fechas-academicas/{created['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 204, resp.text

        # Verificar que no aparece en listado
        resp_list = await client.get(
            "/api/fechas-academicas",
            headers={"Authorization": f"Bearer {token}"},
        )
        ids = {item["id"] for item in resp_list.json()["items"]}
        assert created["id"] not in ids

    async def test_6_5_21_eliminar_fecha_404(self, client: AsyncClient):
        """DELETE fecha inexistente -> 404."""
        token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        resp = await client.delete(
            f"/api/fechas-academicas/{uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404, resp.text

    # ── GET /api/fechas-academicas/lms-export ────────────────────────────

    async def test_6_5_22_lms_export_con_fechas(self, client: AsyncClient):
        """GET /api/fechas-academicas/lms-export -> HTML con fechas."""
        token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        # Crear una fecha
        await client.post(
            "/api/fechas-academicas",
            json={
                "materia_id": str(self.seed["materia_id"]),
                "cohorte_id": str(self.seed["cohorte_id"]),
                "tipo": "Parcial",
                "numero": 1,
                "periodo": "2026-1",
                "fecha": "2026-04-15",
                "titulo": "1er Parcial",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = await client.get(
            f"/api/fechas-academicas/lms-export?materia_id={self.seed['materia_id']}&cohorte_id={self.seed['cohorte_id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        html = data["contenido_html"]
        assert "<table" in html
        assert "1er Parcial" in html

    async def test_6_5_23_lms_export_sin_fechas(self, client: AsyncClient):
        """GET /api/fechas-academicas/lms-export -> HTML sin fechas."""
        token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        resp = await client.get(
            f"/api/fechas-academicas/lms-export?materia_id={self.seed['materia_id']}&cohorte_id={self.seed['cohorte_id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "No hay fechas registradas" in data["contenido_html"]

    async def test_6_5_24_lms_export_403_sin_permiso(self, client: AsyncClient):
        """GET /api/fechas-academicas/lms-export sin permiso -> 403."""
        token = _make_token(self.seed["tutor_user_id"], _DEV_TENANT_ID, ["TUTOR"])
        resp = await client.get(
            f"/api/fechas-academicas/lms-export?materia_id={self.seed['materia_id']}&cohorte_id={self.seed['cohorte_id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403, resp.text


# ══════════════════════════════════════════════════════════════════════════
# 6.7 Multi-tenant isolation
# ══════════════════════════════════════════════════════════════════════════


class TestMultiTenantProgramasYFechas:
    """6.7: Aislamiento multi-tenant en programas y fechas."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, db_session: AsyncSession):
        # Tenant 1
        await _seed_tenant(db_session, _DEV_TENANT_ID)
        await _seed_permisos_estructura(db_session, _DEV_TENANT_ID)
        struct1 = await _seed_estructura(db_session, tenant_id=_DEV_TENANT_ID)
        coord1 = await _seed_usuario(db_session, _DEV_TENANT_ID, "COORDINADOR", "_t1")
        # Tenant 2
        await _seed_tenant(db_session, _DEV_TENANT_ID_2)
        await _seed_permisos_estructura(db_session, _DEV_TENANT_ID_2)
        struct2 = await _seed_estructura(db_session, tenant_id=_DEV_TENANT_ID_2, codigo_sufijo="B")
        coord2 = await _seed_usuario(db_session, _DEV_TENANT_ID_2, "COORDINADOR", "_t2")

        # Crear programa en tenant 1
        prog1 = await _seed_programa(
            db_session, _DEV_TENANT_ID,
            struct1["materia_id"], struct1["carrera_id"], struct1["cohorte_id"],
            titulo="Programa T1",
        )
        # Crear programa en tenant 2
        prog2 = await _seed_programa(
            db_session, _DEV_TENANT_ID_2,
            struct2["materia_id"], struct2["carrera_id"], struct2["cohorte_id"],
            titulo="Programa T2",
        )
        # Crear fecha en tenant 1
        fecha1 = await _seed_fecha(
            db_session, _DEV_TENANT_ID,
            struct1["materia_id"], struct1["cohorte_id"],
            titulo="Fecha T1",
        )
        # Crear fecha en tenant 2
        fecha2 = await _seed_fecha(
            db_session, _DEV_TENANT_ID_2,
            struct2["materia_id"], struct2["cohorte_id"],
            titulo="Fecha T2",
        )
        await db_session.commit()
        self.tenant1 = {
            "coord_user_id": coord1["usuario_id"],
            "programa_id": prog1.id,
            "fecha_id": fecha1.id,
        }
        self.tenant2 = {
            "coord_user_id": coord2["usuario_id"],
            "programa_id": prog2.id,
            "fecha_id": fecha2.id,
        }

    async def test_6_7_1_tenant1_no_ve_programas_tenant2(self, client: AsyncClient):
        """Tenant 1 no ve programas del Tenant 2."""
        token = _make_token(self.tenant1["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        resp = await client.get(
            "/api/programas",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        ids = {item["id"] for item in data["items"]}
        assert str(self.tenant1["programa_id"]) in ids
        assert str(self.tenant2["programa_id"]) not in ids

    async def test_6_7_2_tenant2_no_ve_programas_tenant1(self, client: AsyncClient):
        """Tenant 2 no ve programas del Tenant 1."""
        token = _make_token(self.tenant2["coord_user_id"], _DEV_TENANT_ID_2, ["COORDINADOR"])
        resp = await client.get(
            "/api/programas",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        ids = {item["id"] for item in data["items"]}
        assert str(self.tenant2["programa_id"]) in ids
        assert str(self.tenant1["programa_id"]) not in ids

    async def test_6_7_3_tenant1_no_ve_fechas_tenant2(self, client: AsyncClient):
        """Tenant 1 no ve fechas del Tenant 2."""
        token = _make_token(self.tenant1["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        resp = await client.get(
            "/api/fechas-academicas",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        ids = {item["id"] for item in data["items"]}
        assert str(self.tenant1["fecha_id"]) in ids
        assert str(self.tenant2["fecha_id"]) not in ids

    async def test_6_7_4_tenant2_no_ve_fechas_tenant1(self, client: AsyncClient):
        """Tenant 2 no ve fechas del Tenant 1."""
        token = _make_token(self.tenant2["coord_user_id"], _DEV_TENANT_ID_2, ["COORDINADOR"])
        resp = await client.get(
            "/api/fechas-academicas",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        ids = {item["id"] for item in data["items"]}
        assert str(self.tenant2["fecha_id"]) in ids
        assert str(self.tenant1["fecha_id"]) not in ids

    async def test_6_7_5_acceso_cross_tenant_programa_404(self, client: AsyncClient):
        """Acceder a programa de otro tenant retorna 404."""
        token = _make_token(self.tenant1["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        resp = await client.get(
            f"/api/programas/{self.tenant2['programa_id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404, resp.text

    async def test_6_7_6_acceso_cross_tenant_fecha_404(self, client: AsyncClient):
        """Acceder a fecha de otro tenant retorna 404."""
        token = _make_token(self.tenant1["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        resp = await client.get(
            f"/api/fechas-academicas/{self.tenant2['fecha_id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404, resp.text
