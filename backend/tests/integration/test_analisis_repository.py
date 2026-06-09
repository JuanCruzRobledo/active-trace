"""Tests de integración para AnalisisRepository (C-11).

Requiere PostgreSQL real (DATABASE_URL_TEST en el entorno).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.models.enums import OrigenCalificacion
from app.repositories.analisis_repository import AnalisisRepository
from tests.conftest import db_available

pytestmark = [
    pytest.mark.skipif(
        not db_available(),
        reason="Requiere PostgreSQL: definir DATABASE_URL_TEST en el entorno",
    ),
]


# ── Seeds ────────────────────────────────────────────────────────────


async def _seed_estructura(db_session: AsyncSession, tenant_id: uuid.UUID) -> dict:
    """Crea carrera, cohorte, materia para testing."""
    from app.models.carrera import Carrera
    from app.models.cohorte import Cohorte
    from app.models.materia import Materia

    carrera = Carrera(tenant_id=tenant_id, codigo="C-ANALISIS", nombre="Carrera Test")
    db_session.add(carrera)
    await db_session.flush()

    cohorte = Cohorte(
        tenant_id=tenant_id,
        carrera_id=carrera.id,
        nombre="2026-A",
        anio=2026,
        vig_desde=datetime(2026, 1, 1, tzinfo=timezone.utc).date(),
        estado="Activa",
    )
    db_session.add(cohorte)
    await db_session.flush()

    materia = Materia(tenant_id=tenant_id, codigo="MAT-ANALISIS", nombre="Materia Test")
    db_session.add(materia)
    await db_session.flush()

    return {"carrera": carrera, "cohorte": cohorte, "materia": materia}


async def _seed_alumno(
    db_session: AsyncSession, tenant_id: uuid.UUID, materia_id: uuid.UUID, cohorte_id: uuid.UUID
) -> uuid.UUID:
    """Crea un usuario y un alumno en el padron. Retorna entrada_padron_id."""
    from app.models.version_padron import VersionPadron
    from app.models.entrada_padron import EntradaPadron
    from app.models.usuario import Usuario

    uid = uuid.uuid4()
    user = Usuario(
        id=uid,
        tenant_id=tenant_id,
        email=f"juan{uuid.uuid4().hex[:4]}@test.com",
        nombre="Juan",
        apellidos="Perez",
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
        nombre="Juan",
        apellidos="Perez",
        email=f"juan{uuid.uuid4().hex[:4]}@test.com",
        comision="A",
    )
    db_session.add(ep)
    await db_session.flush()
    return ep.id


async def _seed_calificacion(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
    entrada_padron_id: uuid.UUID,
    materia_id: uuid.UUID,
    actividad: str,
    nota_numerica: Decimal | None = None,
    nota_textual: str | None = None,
    aprobado: bool | None = None,
) -> None:
    """Crea una calificacion."""
    from app.models.calificacion import Calificacion

    c = Calificacion(
        tenant_id=tenant_id,
        entrada_padron_id=entrada_padron_id,
        materia_id=materia_id,
        actividad=actividad,
        nota_numerica=nota_numerica,
        nota_textual=nota_textual,
        aprobado=aprobado,
        origen=OrigenCalificacion.IMPORTADO.value,
        importado_at=datetime.now(timezone.utc),
    )
    db_session.add(c)
    await db_session.flush()


async def _seed_umbral(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
    materia_id: uuid.UUID,
    asignacion_id: uuid.UUID | None = None,
    umbral_pct: int = 60,
) -> None:
    """Crea un umbral de materia con su asignacion."""
    from app.models.umbral_materia import UmbralMateria
    from app.models.asignacion import Asignacion
    from app.models.usuario import Usuario

    if asignacion_id is None:
        asignacion_id = uuid.uuid4()
        user_id = uuid.uuid4()
        user = Usuario(
            id=user_id,
            tenant_id=tenant_id,
            email=f"prof{uuid.uuid4().hex[:4]}@test.com",
            nombre="Profe",
            apellidos="Umbral",
            estado="Activo",
        )
        db_session.add(user)
        await db_session.flush()
        asig = Asignacion(
            id=asignacion_id,
            tenant_id=tenant_id,
            usuario_id=user_id,
            rol="PROFESOR",
            materia_id=materia_id,
            desde=datetime.now(timezone.utc),
        )
        db_session.add(asig)
        await db_session.flush()

    umbral = UmbralMateria(
        tenant_id=tenant_id,
        asignacion_id=asignacion_id,
        materia_id=materia_id,
        umbral_pct=umbral_pct,
        valores_aprobatorios=["Aprobado", "Satisfactorio", "Supera lo esperado"],
    )
    db_session.add(umbral)
    await db_session.flush()


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def tenant(db_session: AsyncSession) -> Tenant:
    tid = uuid.uuid4()
    t = Tenant(id=tid, tenant_id=tid, nombre="AnalisisRepoTest")
    db_session.add(t)
    await db_session.flush()
    return t


@pytest_asyncio.fixture
async def estructura(tenant: Tenant, db_session: AsyncSession) -> dict:
    return await _seed_estructura(db_session, tenant.id)


@pytest_asyncio.fixture
async def alumno1(
    tenant: Tenant, estructura: dict, db_session: AsyncSession
) -> uuid.UUID:
    return await _seed_alumno(
        db_session, tenant.id, estructura["materia"].id, estructura["cohorte"].id
    )


@pytest_asyncio.fixture
async def alumno2(
    tenant: Tenant, estructura: dict, db_session: AsyncSession
) -> uuid.UUID:
    uid = uuid.uuid4()
    from app.models.version_padron import VersionPadron
    from app.models.entrada_padron import EntradaPadron
    from app.models.usuario import Usuario

    user = Usuario(
        id=uid,
        tenant_id=tenant.id,
        email=f"maria{uuid.uuid4().hex[:4]}@test.com",
        nombre="Maria",
        apellidos="Garcia",
        estado="Activo",
    )
    db_session.add(user)
    await db_session.flush()

    vp = VersionPadron(
        tenant_id=tenant.id,
        materia_id=estructura["materia"].id,
        cohorte_id=estructura["cohorte"].id,
        cargado_por=uid,
        cargado_at=datetime.now(timezone.utc),
        activa=True,
    )
    db_session.add(vp)
    await db_session.flush()

    ep = EntradaPadron(
        tenant_id=tenant.id,
        version_id=vp.id,
        usuario_id=uid,
        nombre="Maria",
        apellidos="Garcia",
        email=f"maria{uuid.uuid4().hex[:4]}@test.com",
        comision="B",
    )
    db_session.add(ep)
    await db_session.flush()
    return ep.id


@pytest_asyncio.fixture
async def repo(tenant: Tenant, db_session: AsyncSession) -> AnalisisRepository:
    return AnalisisRepository(db_session, tenant.id)


# ── Tests: listar_calificaciones_por_materia ─────────────────────────


class TestListarCalificacionesPorMateria:
    async def test_listar_devuelve_calificaciones_de_materia(
        self,
        tenant: Tenant,
        estructura: dict,
        alumno1: uuid.UUID,
        repo: AnalisisRepository,
        db_session: AsyncSession,
    ) -> None:
        await _seed_calificacion(
            db_session, tenant.id, alumno1, estructura["materia"].id, "Parcial 1",
            nota_numerica=Decimal("80"), aprobado=True,
        )
        await db_session.commit()

        result = await repo.listar_calificaciones_por_materia(
            estructura["materia"].id
        )
        assert len(result) == 1
        assert result[0].actividad == "Parcial 1"

    async def test_listar_vacia_si_otra_materia(
        self,
        tenant: Tenant,
        estructura: dict,
        alumno1: uuid.UUID,
        repo: AnalisisRepository,
        db_session: AsyncSession,
    ) -> None:
        from app.models.materia import Materia
        otra_materia = Materia(tenant_id=tenant.id, codigo="OTRA", nombre="Otra")
        db_session.add(otra_materia)
        await db_session.flush()

        await _seed_calificacion(
            db_session, tenant.id, alumno1, estructura["materia"].id, "Parcial 1",
            nota_numerica=Decimal("80"), aprobado=True,
        )
        await db_session.commit()

        result = await repo.listar_calificaciones_por_materia(otra_materia.id)
        assert len(result) == 0


# ── Tests: obtener_umbral_materia ────────────────────────────────────


class TestObtenerUmbralMateria:
    async def test_devuelve_umbral_si_existe(
        self,
        tenant: Tenant,
        estructura: dict,
        repo: AnalisisRepository,
        db_session: AsyncSession,
    ) -> None:
        await _seed_umbral(db_session, tenant.id, estructura["materia"].id)
        await db_session.commit()

        umbral = await repo.obtener_umbral_materia(estructura["materia"].id)
        assert umbral is not None
        assert umbral.umbral_pct == 60

    async def test_devuelve_none_si_no_existe(
        self,
        estructura: dict,
        repo: AnalisisRepository,
    ) -> None:
        umbral = await repo.obtener_umbral_materia(estructura["materia"].id)
        assert umbral is None


# ── Tests: reporte_rapido ────────────────────────────────────────────


class TestReporteRapido:
    async def test_reporte_con_datos(
        self,
        tenant: Tenant,
        estructura: dict,
        alumno1: uuid.UUID,
        alumno2: uuid.UUID,
        repo: AnalisisRepository,
        db_session: AsyncSession,
    ) -> None:
        await _seed_calificacion(
            db_session, tenant.id, alumno1, estructura["materia"].id, "Parcial 1",
            nota_numerica=Decimal("80"), aprobado=True,
        )
        await _seed_calificacion(
            db_session, tenant.id, alumno2, estructura["materia"].id, "Parcial 1",
            nota_numerica=Decimal("40"), aprobado=False,
        )
        await db_session.commit()

        reporte = await repo.reporte_rapido(estructura["materia"].id)
        assert reporte["total_alumnos"] == 2
        assert reporte["aprobados"] == 1
        assert reporte["atrasados"] == 1
        assert reporte["cantidad_actividades"] == 1

    async def test_reporte_sin_datos(
        self,
        estructura: dict,
        repo: AnalisisRepository,
    ) -> None:
        reporte = await repo.reporte_rapido(estructura["materia"].id)
        assert reporte["total_alumnos"] == 0
        assert reporte["porcentaje_aprobacion"] == 0.0


# ── Tests: total_actividades_materia ─────────────────────────────────


class TestTotalActividadesMateria:
    async def test_cuenta_actividades_distintas(
        self,
        tenant: Tenant,
        estructura: dict,
        alumno1: uuid.UUID,
        repo: AnalisisRepository,
        db_session: AsyncSession,
    ) -> None:
        await _seed_calificacion(
            db_session, tenant.id, alumno1, estructura["materia"].id, "Parcial 1",
            nota_numerica=Decimal("80"), aprobado=True,
        )
        await _seed_calificacion(
            db_session, tenant.id, alumno1, estructura["materia"].id, "TP 1",
            nota_numerica=Decimal("90"), aprobado=True,
        )
        await db_session.commit()

        total = await repo.total_actividades_materia(estructura["materia"].id)
        assert total == 2


# ── Tests: actividades_textuales_materia ─────────────────────────────


class TestActividadesTextuales:
    async def test_lista_solo_textuales(
        self,
        tenant: Tenant,
        estructura: dict,
        alumno1: uuid.UUID,
        repo: AnalisisRepository,
        db_session: AsyncSession,
    ) -> None:
        await _seed_calificacion(
            db_session, tenant.id, alumno1, estructura["materia"].id, "Parcial 1",
            nota_numerica=Decimal("80"), aprobado=True,
        )
        await _seed_calificacion(
            db_session, tenant.id, alumno1, estructura["materia"].id, "TP Escrito",
            nota_textual="Aprobado", aprobado=True,
        )
        await db_session.commit()

        textuales = await repo.actividades_textuales_materia(estructura["materia"].id)
        assert "TP Escrito" in textuales
        assert "Parcial 1" not in textuales


# ── Tests: monitor_general ───────────────────────────────────────────


class TestMonitorGeneral:
    async def test_monitor_filtra_por_materia(
        self,
        tenant: Tenant,
        estructura: dict,
        alumno1: uuid.UUID,
        repo: AnalisisRepository,
        db_session: AsyncSession,
    ) -> None:
        await db_session.commit()
        result = await repo.monitor_general(materia_id=estructura["materia"].id)
        assert len(result) == 1
        assert result[0]["nombre"] == "Juan"

    async def test_monitor_sin_filtro_devuelve_todos(
        self,
        tenant: Tenant,
        estructura: dict,
        alumno1: uuid.UUID,
        alumno2: uuid.UUID,
        repo: AnalisisRepository,
        db_session: AsyncSession,
    ) -> None:
        await db_session.commit()
        result = await repo.monitor_general()
        assert len(result) == 2


# ── Tests: obtener_alumnos_por_asignacion ────────────────────────────


class TestObtenerAlumnosPorAsignacion:
    async def test_devuelve_alumnos_de_usuario(
        self,
        tenant: Tenant,
        estructura: dict,
        alumno1: uuid.UUID,
        repo: AnalisisRepository,
        db_session: AsyncSession,
    ) -> None:
        from app.models.usuario import Usuario
        from app.models.asignacion import Asignacion

        user_id = uuid.uuid4()
        user = Usuario(
            id=user_id,
            tenant_id=tenant.id,
            email=f"prof{uuid.uuid4().hex[:4]}@test.com",
            nombre="Profe",
            apellidos="Uno",
            estado="Activo",
        )
        db_session.add(user)
        await db_session.flush()

        asignacion = Asignacion(
            tenant_id=tenant.id,
            usuario_id=user_id,
            rol="PROFESOR",
            materia_id=estructura["materia"].id,
            desde=datetime.now(timezone.utc),
        )
        db_session.add(asignacion)
        await db_session.commit()

        alumnos = await repo.obtener_alumnos_por_asignacion(user_id)
        assert len(alumnos) > 0
