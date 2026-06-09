"""Tests de integración para CalificacionRepository (C-10).

Requiere PostgreSQL real (DATABASE_URL_TEST en el entorno).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.models.enums import OrigenCalificacion
from tests.conftest import db_available

pytestmark = [
    pytest.mark.skipif(
        not db_available(),
        reason="Requiere PostgreSQL: definir DATABASE_URL_TEST en el entorno",
    ),
]


@pytest_asyncio.fixture
async def tenant(db_session: AsyncSession) -> Tenant:
    tid = uuid.uuid4()
    t = Tenant(id=tid, tenant_id=tid, nombre="CalifRepoTest")
    db_session.add(t)
    await db_session.flush()
    return t


@pytest_asyncio.fixture
async def materia(tenant: Tenant, db_session: AsyncSession) -> object:
    from app.models.materia import Materia

    m = Materia(tenant_id=tenant.id, codigo="MAT-REPO-1", nombre="Repo Test Materia")
    db_session.add(m)
    await db_session.flush()
    return m


@pytest_asyncio.fixture
async def materia_otra(tenant: Tenant, db_session: AsyncSession) -> object:
    from app.models.materia import Materia

    m = Materia(tenant_id=tenant.id, codigo="MAT-REPO-2", nombre="Otra Materia")
    db_session.add(m)
    await db_session.flush()
    return m


@pytest_asyncio.fixture
async def entrada_padron(
    tenant: Tenant, materia: object, db_session: AsyncSession
) -> object:
    from app.models.carrera import Carrera
    from app.models.cohorte import Cohorte
    from app.models.version_padron import VersionPadron
    from app.models.entrada_padron import EntradaPadron

    carrera = Carrera(tenant_id=tenant.id, codigo="ING-REPO", nombre="Ing Repo")
    db_session.add(carrera)
    await db_session.flush()

    c = Cohorte(
        tenant_id=tenant.id,
        carrera_id=carrera.id,
        nombre="2026-A",
        anio=2026,
        vig_desde=datetime(2026, 1, 1, tzinfo=timezone.utc).date(),
        estado="Activa",
    )
    db_session.add(c)
    await db_session.flush()

    vp = VersionPadron(
        tenant_id=tenant.id,
        materia_id=materia.id,
        cohorte_id=c.id,
        activa=True,
    )
    db_session.add(vp)
    await db_session.flush()

    ep = EntradaPadron(
        tenant_id=tenant.id,
        version_id=vp.id,
        nombre="Ana",
        apellidos="Repo",
        email="ana.repo@test.com",
    )
    db_session.add(ep)
    await db_session.flush()
    return ep


@pytest_asyncio.fixture
async def entrada_padron_2(
    tenant: Tenant, materia: object, db_session: AsyncSession
) -> object:
    from app.models.carrera import Carrera
    from app.models.cohorte import Cohorte
    from app.models.version_padron import VersionPadron
    from app.models.entrada_padron import EntradaPadron

    carrera = Carrera(tenant_id=tenant.id, codigo="ING-REPO-2", nombre="Ing Repo 2")
    db_session.add(carrera)
    await db_session.flush()

    c = Cohorte(
        tenant_id=tenant.id,
        carrera_id=carrera.id,
        nombre="2026-B",
        anio=2026,
        vig_desde=datetime(2026, 6, 1, tzinfo=timezone.utc).date(),
        estado="Activa",
    )
    db_session.add(c)
    await db_session.flush()

    vp = VersionPadron(
        tenant_id=tenant.id,
        materia_id=materia.id,
        cohorte_id=c.id,
        activa=True,
    )
    db_session.add(vp)
    await db_session.flush()

    ep = EntradaPadron(
        tenant_id=tenant.id,
        version_id=vp.id,
        nombre="Luis",
        apellidos="Repo",
        email="luis.repo@test.com",
    )
    db_session.add(ep)
    await db_session.flush()
    return ep


@pytest_asyncio.fixture
async def repo(tenant: Tenant, db_session: AsyncSession) -> object:
    from app.repositories.calificacion_repository import CalificacionRepository

    return CalificacionRepository(session=db_session, tenant_id=tenant.id)


class TestCalificacionRepositoryListByMateria:
    async def test_retorna_solo_las_de_una_materia(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
        materia: object,
        materia_otra: object,
        entrada_padron: object,
        repo: object,
    ) -> None:
        from app.models.calificacion import Calificacion

        c1 = Calificacion(
            tenant_id=tenant.id,
            entrada_padron_id=entrada_padron.id,
            materia_id=materia.id,
            actividad="Parcial",
            nota_numerica=8.0,
            origen=OrigenCalificacion.IMPORTADO,
        )
        c2 = Calificacion(
            tenant_id=tenant.id,
            entrada_padron_id=entrada_padron.id,
            materia_id=materia_otra.id,
            actividad="Parcial",
            nota_numerica=7.0,
            origen=OrigenCalificacion.IMPORTADO,
        )
        db_session.add_all([c1, c2])
        await db_session.flush()

        result = await repo.list_by_materia(materia.id)

        assert len(result) == 1
        assert result[0].id == c1.id

    async def test_excluye_soft_deleted(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
        materia: object,
        entrada_padron: object,
        repo: object,
    ) -> None:
        from app.models.calificacion import Calificacion

        c1 = Calificacion(
            tenant_id=tenant.id,
            entrada_padron_id=entrada_padron.id,
            materia_id=materia.id,
            actividad="Final",
            nota_numerica=9.0,
            origen=OrigenCalificacion.IMPORTADO,
        )
        c2 = Calificacion(
            tenant_id=tenant.id,
            entrada_padron_id=entrada_padron.id,
            materia_id=materia.id,
            actividad="Recuperatorio",
            nota_numerica=6.0,
            origen=OrigenCalificacion.IMPORTADO,
        )
        db_session.add_all([c1, c2])
        await db_session.flush()
        await db_session.refresh(c1)
        await db_session.refresh(c2)

        c1.deleted_at = datetime.now(timezone.utc)
        await db_session.flush()

        result = await repo.list_by_materia(materia.id)

        assert len(result) == 1
        assert result[0].id == c2.id


class TestCalificacionRepositoryListByEntradaPadron:
    async def test_retorna_solo_las_de_un_alumno(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
        materia: object,
        entrada_padron: object,
        entrada_padron_2: object,
        repo: object,
    ) -> None:
        from app.models.calificacion import Calificacion

        c1 = Calificacion(
            tenant_id=tenant.id,
            entrada_padron_id=entrada_padron.id,
            materia_id=materia.id,
            actividad="TP1",
            nota_numerica=10.0,
            origen=OrigenCalificacion.IMPORTADO,
        )
        c2 = Calificacion(
            tenant_id=tenant.id,
            entrada_padron_id=entrada_padron_2.id,
            materia_id=materia.id,
            actividad="TP1",
            nota_numerica=9.0,
            origen=OrigenCalificacion.IMPORTADO,
        )
        db_session.add_all([c1, c2])
        await db_session.flush()

        result = await repo.list_by_entrada_padron(entrada_padron.id)

        assert len(result) == 1
        assert result[0].id == c1.id


class TestCalificacionRepositoryFindByActividad:
    async def test_retorna_solo_las_de_esa_actividad(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
        materia: object,
        entrada_padron: object,
        repo: object,
    ) -> None:
        from app.models.calificacion import Calificacion

        c1 = Calificacion(
            tenant_id=tenant.id,
            entrada_padron_id=entrada_padron.id,
            materia_id=materia.id,
            actividad="Parcial 1",
            nota_numerica=8.0,
            origen=OrigenCalificacion.IMPORTADO,
        )
        c2 = Calificacion(
            tenant_id=tenant.id,
            entrada_padron_id=entrada_padron.id,
            materia_id=materia.id,
            actividad="Parcial 2",
            nota_numerica=7.0,
            origen=OrigenCalificacion.IMPORTADO,
        )
        db_session.add_all([c1, c2])
        await db_session.flush()

        result = await repo.find_by_actividad(materia.id, "Parcial 1")

        assert len(result) == 1
        assert result[0].id == c1.id

    async def test_excluye_otras_materias(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
        materia: object,
        materia_otra: object,
        entrada_padron: object,
        repo: object,
    ) -> None:
        from app.models.calificacion import Calificacion

        c1 = Calificacion(
            tenant_id=tenant.id,
            entrada_padron_id=entrada_padron.id,
            materia_id=materia.id,
            actividad="Parcial",
            nota_numerica=8.0,
            origen=OrigenCalificacion.IMPORTADO,
        )
        c2 = Calificacion(
            tenant_id=tenant.id,
            entrada_padron_id=entrada_padron.id,
            materia_id=materia_otra.id,
            actividad="Parcial",
            nota_numerica=7.0,
            origen=OrigenCalificacion.IMPORTADO,
        )
        db_session.add_all([c1, c2])
        await db_session.flush()

        result = await repo.find_by_actividad(materia.id, "Parcial")

        assert len(result) == 1
        assert result[0].id == c1.id


class TestCalificacionRepositoryBulkCreate:
    async def test_persiste_varias_calificaciones(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
        materia: object,
        entrada_padron: object,
        repo: object,
    ) -> None:
        from app.models.calificacion import Calificacion

        calificaciones = [
            Calificacion(
                tenant_id=tenant.id,
                entrada_padron_id=entrada_padron.id,
                materia_id=materia.id,
                actividad="TP1",
                nota_numerica=9.0,
                origen=OrigenCalificacion.IMPORTADO,
            ),
            Calificacion(
                tenant_id=tenant.id,
                entrada_padron_id=entrada_padron.id,
                materia_id=materia.id,
                actividad="TP2",
                nota_numerica=8.0,
                origen=OrigenCalificacion.IMPORTADO,
            ),
        ]

        result = await repo.bulk_create(calificaciones)

        assert len(result) == 2
        assert result[0].id is not None
        assert result[1].id is not None
        assert result[0].nota_numerica == 9.0
        assert result[1].nota_numerica == 8.0

        from sqlalchemy import select

        stmt = select(Calificacion).where(
            Calificacion.tenant_id == tenant.id,
            Calificacion.deleted_at.is_(None),
        )
        all_califs = (await db_session.scalars(stmt)).all()
        assert len(all_califs) == 2


class TestCalificacionRepositoryDeleteByMateria:
    async def test_marca_soft_delete_en_todas_las_de_una_materia(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
        materia: object,
        materia_otra: object,
        entrada_padron: object,
        repo: object,
    ) -> None:
        from app.models.calificacion import Calificacion

        c1 = Calificacion(
            tenant_id=tenant.id,
            entrada_padron_id=entrada_padron.id,
            materia_id=materia.id,
            actividad="Parcial",
            nota_numerica=8.0,
            origen=OrigenCalificacion.IMPORTADO,
        )
        c2 = Calificacion(
            tenant_id=tenant.id,
            entrada_padron_id=entrada_padron.id,
            materia_id=materia.id,
            actividad="Final",
            nota_numerica=9.0,
            origen=OrigenCalificacion.IMPORTADO,
        )
        c3 = Calificacion(
            tenant_id=tenant.id,
            entrada_padron_id=entrada_padron.id,
            materia_id=materia_otra.id,
            actividad="Parcial",
            nota_numerica=7.0,
            origen=OrigenCalificacion.IMPORTADO,
        )
        db_session.add_all([c1, c2, c3])
        await db_session.flush()
        await db_session.refresh(c1)
        await db_session.refresh(c2)
        await db_session.refresh(c3)

        assert c1.deleted_at is None
        assert c2.deleted_at is None
        assert c3.deleted_at is None

        await repo.delete_by_materia(materia.id)

        await db_session.refresh(c1)
        await db_session.refresh(c2)
        await db_session.refresh(c3)

        assert c1.deleted_at is not None
        assert c2.deleted_at is not None
        assert c3.deleted_at is None

    async def test_no_afecta_si_no_hay_calificaciones(
        self,
        materia: object,
        repo: object,
    ) -> None:
        await repo.delete_by_materia(materia.id)


class TestCalificacionRepositoryRecalcularAprobado:
    async def test_numero_sobre_umbral_es_aprobado(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
        materia: object,
        entrada_padron: object,
        repo: object,
    ) -> None:
        from app.models.calificacion import Calificacion

        c1 = Calificacion(
            tenant_id=tenant.id,
            entrada_padron_id=entrada_padron.id,
            materia_id=materia.id,
            actividad="Parcial",
            nota_numerica=85,
            origen=OrigenCalificacion.IMPORTADO,
        )
        c2 = Calificacion(
            tenant_id=tenant.id,
            entrada_padron_id=entrada_padron.id,
            materia_id=materia.id,
            actividad="Final",
            nota_numerica=40,
            origen=OrigenCalificacion.IMPORTADO,
        )
        db_session.add_all([c1, c2])
        await db_session.flush()

        updated = await repo.recalcular_aprobado(materia.id, 60, None)

        assert updated == 2
        await db_session.refresh(c1)
        await db_session.refresh(c2)
        assert c1.aprobado is True
        assert c2.aprobado is False

    async def test_numero_igual_umbral_es_aprobado(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
        materia: object,
        entrada_padron: object,
        repo: object,
    ) -> None:
        from app.models.calificacion import Calificacion

        c = Calificacion(
            tenant_id=tenant.id,
            entrada_padron_id=entrada_padron.id,
            materia_id=materia.id,
            actividad="TP",
            nota_numerica=75,
            origen=OrigenCalificacion.IMPORTADO,
        )
        db_session.add(c)
        await db_session.flush()

        updated = await repo.recalcular_aprobado(materia.id, 75, None)

        assert updated == 1
        await db_session.refresh(c)
        assert c.aprobado is True

    async def test_textual_en_valores_aprobatorios(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
        materia: object,
        entrada_padron: object,
        repo: object,
    ) -> None:
        from app.models.calificacion import Calificacion

        c1 = Calificacion(
            tenant_id=tenant.id,
            entrada_padron_id=entrada_padron.id,
            materia_id=materia.id,
            actividad="TP1",
            nota_textual="Aprobado",
            origen=OrigenCalificacion.IMPORTADO,
        )
        c2 = Calificacion(
            tenant_id=tenant.id,
            entrada_padron_id=entrada_padron.id,
            materia_id=materia.id,
            actividad="TP2",
            nota_textual="Desaprobado",
            origen=OrigenCalificacion.IMPORTADO,
        )
        db_session.add_all([c1, c2])
        await db_session.flush()

        updated = await repo.recalcular_aprobado(
            materia.id, 60, ["Aprobado", "Promocionado"]
        )

        assert updated == 2
        await db_session.refresh(c1)
        await db_session.refresh(c2)
        assert c1.aprobado is True
        assert c2.aprobado is False

    async def test_mixto_numerica_y_textual(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
        materia: object,
        entrada_padron: object,
        repo: object,
    ) -> None:
        from app.models.calificacion import Calificacion

        c1 = Calificacion(
            tenant_id=tenant.id,
            entrada_padron_id=entrada_padron.id,
            materia_id=materia.id,
            actividad="Parcial",
            nota_numerica=85,
            origen=OrigenCalificacion.IMPORTADO,
        )
        c2 = Calificacion(
            tenant_id=tenant.id,
            entrada_padron_id=entrada_padron.id,
            materia_id=materia.id,
            actividad="TP",
            nota_textual="Aprobado",
            origen=OrigenCalificacion.IMPORTADO,
        )
        db_session.add_all([c1, c2])
        await db_session.flush()

        updated = await repo.recalcular_aprobado(materia.id, 60, ["Aprobado"])

        assert updated == 2
        await db_session.refresh(c1)
        await db_session.refresh(c2)
        assert c1.aprobado is True
        assert c2.aprobado is True
