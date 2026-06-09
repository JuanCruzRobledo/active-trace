"""Tests de integración para repositorios de estructura académica (C-06).

Requiere PostgreSQL real (DATABASE_URL_TEST en el entorno).
"""

from __future__ import annotations

import uuid
from datetime import date

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.carrera import Carrera
from app.repositories.carrera_repository import CarreraRepository
from app.repositories.materia_repository import MateriaRepository
from app.repositories.cohorte_repository import CohorteRepository
from app.models.cohorte import Cohorte
from app.models.materia import Materia
from app.models.tenant import Tenant
from tests.conftest import db_available

pytestmark = [
    pytest.mark.skipif(
        not db_available(),
        reason="Requiere PostgreSQL: definir DATABASE_URL_TEST en el entorno",
    ),
]


@pytest_asyncio.fixture
async def tenant(db_session) -> Tenant:
    tid = uuid.uuid4()
    t = Tenant(id=tid, tenant_id=tid, nombre="EstructuraTest")
    db_session.add(t)
    await db_session.flush()
    return t


@pytest_asyncio.fixture
async def tenant_b(db_session) -> Tenant:
    tid = uuid.uuid4()
    t = Tenant(id=tid, tenant_id=tid, nombre="EstructuraTestB")
    db_session.add(t)
    await db_session.flush()
    return t


@pytest_asyncio.fixture
async def seed_carrera(db_session, tenant: Tenant) -> Carrera:
    c = Carrera(
        id=uuid.uuid4(), tenant_id=tenant.id,
        codigo="LIC", nombre="Licenciatura",
    )
    db_session.add(c)
    await db_session.flush()
    return c


# ===========================================================================
# CarreraRepository
# ===========================================================================


class TestCarreraRepository:
    async def test_save_and_get_by_id(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        repo = CarreraRepository(db_session, Carrera, tenant.id)
        c = Carrera(tenant_id=tenant.id, codigo="ING", nombre="Ingenieria")
        await repo.save(c)
        await db_session.flush()

        found = await repo.get_by_id(c.id)
        assert found is not None
        assert found.codigo == "ING"
        assert found.nombre == "Ingenieria"

    async def test_get_by_codigo(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        repo = CarreraRepository(db_session, Carrera, tenant.id)
        c = Carrera(tenant_id=tenant.id, codigo="MED", nombre="Medicina")
        await repo.save(c)
        await db_session.flush()

        found = await repo.get_by_codigo("MED")
        assert found is not None
        assert found.nombre == "Medicina"

    async def test_get_by_codigo_not_found(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        repo = CarreraRepository(db_session, Carrera, tenant.id)
        found = await repo.get_by_codigo("NONEXIST")
        assert found is None

    async def test_list_all(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        repo = CarreraRepository(db_session, Carrera, tenant.id)
        c1 = Carrera(tenant_id=tenant.id, codigo="A", nombre="Alpha")
        c2 = Carrera(tenant_id=tenant.id, codigo="B", nombre="Beta")
        await repo.save(c1)
        await repo.save(c2)
        await db_session.flush()

        results = await repo.list_all()
        assert len(results) == 2

    async def test_soft_delete(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        repo = CarreraRepository(db_session, Carrera, tenant.id)
        c = Carrera(tenant_id=tenant.id, codigo="DEL", nombre="ToDelete")
        await repo.save(c)
        await db_session.flush()

        await repo.soft_delete(c)
        await db_session.flush()

        # Should not appear in list_all
        results = await repo.list_all()
        ids = [r.id for r in results]
        assert c.id not in ids

    async def test_tenant_isolation(
        self, db_session: AsyncSession, tenant: Tenant, tenant_b: Tenant
    ) -> None:
        """GIVEN carreras in tenant and tenant_b WHEN list_all THEN only own."""
        repo_a = CarreraRepository(db_session, Carrera, tenant.id)
        repo_b = CarreraRepository(db_session, Carrera, tenant_b.id)

        c_a = Carrera(tenant_id=tenant.id, codigo="T1", nombre="Tenant1")
        await repo_a.save(c_a)
        c_b = Carrera(tenant_id=tenant_b.id, codigo="T2", nombre="Tenant2")
        await repo_b.save(c_b)
        await db_session.flush()

        results_a = await repo_a.list_all()
        assert len(results_a) == 1
        assert results_a[0].codigo == "T1"

        results_b = await repo_b.list_all()
        assert len(results_b) == 1
        assert results_b[0].codigo == "T2"


# ===========================================================================
# MateriaRepository
# ===========================================================================


class TestMateriaRepository:
    async def test_save_and_get_by_codigo(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        repo = MateriaRepository(db_session, Materia, tenant.id)
        m = Materia(tenant_id=tenant.id, codigo="M01", nombre="Matematicas")
        await repo.save(m)
        await db_session.flush()

        found = await repo.get_by_codigo("M01")
        assert found is not None
        assert found.nombre == "Matematicas"

    async def test_list_all(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        repo = MateriaRepository(db_session, Materia, tenant.id)
        m1 = Materia(tenant_id=tenant.id, codigo="M01", nombre="Matematicas")
        m2 = Materia(tenant_id=tenant.id, codigo="M02", nombre="Lengua")
        await repo.save(m1)
        await repo.save(m2)
        await db_session.flush()

        results = await repo.list_all()
        assert len(results) == 2

    async def test_tenant_isolation(
        self, db_session: AsyncSession, tenant: Tenant, tenant_b: Tenant
    ) -> None:
        repo_a = MateriaRepository(db_session, Materia, tenant.id)
        repo_b = MateriaRepository(db_session, Materia, tenant_b.id)

        m_a = Materia(tenant_id=tenant.id, codigo="TA", nombre="TenantA")
        await repo_a.save(m_a)
        m_b = Materia(tenant_id=tenant_b.id, codigo="TB", nombre="TenantB")
        await repo_b.save(m_b)
        await db_session.flush()

        assert len(await repo_a.list_all()) == 1
        assert len(await repo_b.list_all()) == 1


# ===========================================================================
# CohorteRepository
# ===========================================================================


class TestCohorteRepository:
    async def test_save_and_get_by_nombre_and_carrera(
        self, db_session: AsyncSession, tenant: Tenant, seed_carrera: Carrera
    ) -> None:
        repo = CohorteRepository(db_session, Cohorte, tenant.id)
        coh = Cohorte(
            tenant_id=tenant.id, carrera_id=seed_carrera.id,
            nombre="2024A", anio=2024, vig_desde=date(2024, 3, 1),
        )
        await repo.save(coh)
        await db_session.flush()

        found = await repo.get_by_nombre_and_carrera("2024A", str(seed_carrera.id))
        assert found is not None
        assert found.anio == 2024

    async def test_list_all(
        self, db_session: AsyncSession, tenant: Tenant, seed_carrera: Carrera
    ) -> None:
        repo = CohorteRepository(db_session, Cohorte, tenant.id)
        c1 = Cohorte(
            tenant_id=tenant.id, carrera_id=seed_carrera.id,
            nombre="2024A", anio=2024, vig_desde=date(2024, 3, 1),
        )
        c2 = Cohorte(
            tenant_id=tenant.id, carrera_id=seed_carrera.id,
            nombre="2024B", anio=2024, vig_desde=date(2024, 8, 1),
        )
        await repo.save(c1)
        await repo.save(c2)
        await db_session.flush()

        assert len(await repo.list_all()) == 2

    async def test_tenant_isolation(
        self, db_session: AsyncSession, tenant: Tenant, tenant_b: Tenant
    ) -> None:
        # Create carrera in both tenants
        repo_carrera = CarreraRepository(db_session, Carrera, tenant.id)
        ca = Carrera(tenant_id=tenant.id, codigo="C1", nombre="Carrera1")
        await repo_carrera.save(ca)

        repo_carrera_b = CarreraRepository(db_session, Carrera, tenant_b.id)
        cb = Carrera(tenant_id=tenant_b.id, codigo="C2", nombre="Carrera2")
        await repo_carrera_b.save(cb)
        await db_session.flush()

        repo_a = CohorteRepository(db_session, Cohorte, tenant.id)
        repo_b = CohorteRepository(db_session, Cohorte, tenant_b.id)

        coh_a = Cohorte(
            tenant_id=tenant.id, carrera_id=ca.id,
            nombre="2024A", anio=2024, vig_desde=date(2024, 3, 1),
        )
        await repo_a.save(coh_a)
        coh_b = Cohorte(
            tenant_id=tenant_b.id, carrera_id=cb.id,
            nombre="2024B", anio=2024, vig_desde=date(2024, 3, 1),
        )
        await repo_b.save(coh_b)
        await db_session.flush()

        assert len(await repo_a.list_all()) == 1
        assert len(await repo_b.list_all()) == 1
