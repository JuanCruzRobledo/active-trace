"""Tests de integración para Services de estructura académica (C-06).

Requiere PostgreSQL real (DATABASE_URL_TEST en el entorno).
"""

from __future__ import annotations

import uuid
from datetime import date

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError
from app.models.tenant import Tenant
from app.models.carrera import Carrera
from app.services.carrera_service import CarreraService
from app.services.materia_service import MateriaService
from app.services.cohorte_service import CohorteService
from app.schemas.carrera import CarreraCreate, CarreraUpdate
from app.schemas.materia import MateriaCreate, MateriaUpdate
from app.schemas.cohorte import CohorteCreate, CohorteUpdate
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
    t = Tenant(id=tid, tenant_id=tid, nombre="ServiceTest")
    db_session.add(t)
    await db_session.flush()
    return t


@pytest_asyncio.fixture
async def tenant_b(db_session) -> Tenant:
    tid = uuid.uuid4()
    t = Tenant(id=tid, tenant_id=tid, nombre="ServiceTestB")
    db_session.add(t)
    await db_session.flush()
    return t


# ===========================================================================
# CarreraService
# ===========================================================================


class TestCarreraService:
    async def test_crear_carrera(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        svc = CarreraService(db_session, tenant.id)
        data = CarreraCreate(codigo="LIC", nombre="Licenciatura en Sistemas")
        c = await svc.crear(data)

        assert c.codigo == "LIC"
        assert c.nombre == "Licenciatura en Sistemas"
        assert c.estado == "Activa"

    async def test_crear_duplicado_raise_business_error(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        svc = CarreraService(db_session, tenant.id)
        data = CarreraCreate(codigo="LIC", nombre="Licenciatura")
        await svc.crear(data)

        with pytest.raises(BusinessError) as exc:
            await svc.crear(data)
        assert "codigo" in str(exc.value.message).lower()

    async def test_crear_mismo_codigo_distinto_tenant_ok(
        self, db_session: AsyncSession, tenant: Tenant, tenant_b: Tenant
    ) -> None:
        """Mismo codigo en distintos tenants NO debe levantar BusinessError."""
        svc_a = CarreraService(db_session, tenant.id)
        svc_b = CarreraService(db_session, tenant_b.id)
        data = CarreraCreate(codigo="LIC", nombre="Licenciatura")

        await svc_a.crear(data)
        c = await svc_b.crear(data)  # No debe fallar

        assert c.codigo == "LIC"

    async def test_listar_carreras(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        svc = CarreraService(db_session, tenant.id)
        await svc.crear(CarreraCreate(codigo="A", nombre="Alpha"))
        await svc.crear(CarreraCreate(codigo="B", nombre="Beta"))

        results = await svc.listar()
        assert len(results) == 2

    async def test_obtener_carrera(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        svc = CarreraService(db_session, tenant.id)
        c = await svc.crear(CarreraCreate(codigo="MED", nombre="Medicina"))

        found = await svc.obtener(c.id)
        assert found is not None
        assert found.nombre == "Medicina"

    async def test_obtener_nonexistent_returns_none(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        svc = CarreraService(db_session, tenant.id)
        found = await svc.obtener(uuid.uuid4())
        assert found is None

    async def test_actualizar_carrera(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        svc = CarreraService(db_session, tenant.id)
        c = await svc.crear(CarreraCreate(codigo="ING", nombre="Ingenieria"))

        updated = await svc.actualizar(
            c.id, CarreraUpdate(nombre="Ingenieria en Sistemas")
        )
        assert updated is not None
        assert updated.nombre == "Ingenieria en Sistemas"

    async def test_actualizar_nonexistent_returns_none(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        svc = CarreraService(db_session, tenant.id)
        result = await svc.actualizar(uuid.uuid4(), CarreraUpdate(nombre="X"))
        assert result is None


# ===========================================================================
# MateriaService
# ===========================================================================


class TestMateriaService:
    async def test_crear_materia(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        svc = MateriaService(db_session, tenant.id)
        data = MateriaCreate(codigo="M01", nombre="Matematicas I")
        m = await svc.crear(data)

        assert m.codigo == "M01"
        assert m.nombre == "Matematicas I"
        assert m.estado == "Activa"

    async def test_crear_duplicado_raise_business_error(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        svc = MateriaService(db_session, tenant.id)
        data = MateriaCreate(codigo="M01", nombre="Matematicas")
        await svc.crear(data)

        with pytest.raises(BusinessError) as exc:
            await svc.crear(data)
        assert "codigo" in str(exc.value.message).lower()

    async def test_listar_materias(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        svc = MateriaService(db_session, tenant.id)
        await svc.crear(MateriaCreate(codigo="M01", nombre="Matematicas"))
        await svc.crear(MateriaCreate(codigo="M02", nombre="Lengua"))

        results = await svc.listar()
        assert len(results) == 2

    async def test_actualizar_materia(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        svc = MateriaService(db_session, tenant.id)
        m = await svc.crear(MateriaCreate(codigo="M01", nombre="Matematicas"))

        updated = await svc.actualizar(
            m.id, MateriaUpdate(nombre="Matematicas Avanzadas")
        )
        assert updated is not None
        assert updated.nombre == "Matematicas Avanzadas"


# ===========================================================================
# CohorteService
# ===========================================================================


class TestCohorteService:
    async def test_crear_cohorte(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        # Primero crear una carrera activa
        carrera_svc = CarreraService(db_session, tenant.id)
        carrera = await carrera_svc.crear(
            CarreraCreate(codigo="LIC", nombre="Licenciatura")
        )

        cohorte_svc = CohorteService(db_session, tenant.id)
        data = CohorteCreate(
            carrera_id=str(carrera.id),
            nombre="2024A",
            anio=2024,
            vig_desde=date(2024, 3, 1),
        )
        coh = await cohorte_svc.crear(data)

        assert coh.nombre == "2024A"
        assert coh.anio == 2024
        assert coh.estado == "Activa"

    async def test_crear_cohorte_en_carrera_inactiva_raise_business_error(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        carrera_svc = CarreraService(db_session, tenant.id)
        carrera = await carrera_svc.crear(
            CarreraCreate(codigo="LIC", nombre="Lic.", estado="Inactiva")
        )

        cohorte_svc = CohorteService(db_session, tenant.id)
        data = CohorteCreate(
            carrera_id=str(carrera.id),
            nombre="2024A", anio=2024,
            vig_desde=date(2024, 3, 1),
        )

        with pytest.raises(BusinessError) as exc:
            await cohorte_svc.crear(data)
        assert "inactiva" in str(exc.value.message).lower()

    async def test_crear_cohorte_carrera_inexistente_raise_business_error(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        cohorte_svc = CohorteService(db_session, tenant.id)
        data = CohorteCreate(
            carrera_id=str(uuid.uuid4()),
            nombre="2024A", anio=2024,
            vig_desde=date(2024, 3, 1),
        )

        with pytest.raises(BusinessError) as exc:
            await cohorte_svc.crear(data)
        assert "no existe" in str(exc.value.message).lower()

    async def test_crear_cohorte_duplicada_misma_carrera_raise_error(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        carrera_svc = CarreraService(db_session, tenant.id)
        carrera = await carrera_svc.crear(
            CarreraCreate(codigo="LIC", nombre="Licenciatura")
        )

        cohorte_svc = CohorteService(db_session, tenant.id)
        data = CohorteCreate(
            carrera_id=str(carrera.id),
            nombre="2024A", anio=2024,
            vig_desde=date(2024, 3, 1),
        )
        await cohorte_svc.crear(data)

        with pytest.raises(BusinessError) as exc:
            await cohorte_svc.crear(data)
        assert "ya existe" in str(exc.value.message).lower()

    async def test_listar_cohortes(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        carrera_svc = CarreraService(db_session, tenant.id)
        carrera = await carrera_svc.crear(
            CarreraCreate(codigo="LIC", nombre="Licenciatura")
        )

        cohorte_svc = CohorteService(db_session, tenant.id)
        await cohorte_svc.crear(CohorteCreate(
            carrera_id=str(carrera.id), nombre="2024A",
            anio=2024, vig_desde=date(2024, 3, 1),
        ))
        await cohorte_svc.crear(CohorteCreate(
            carrera_id=str(carrera.id), nombre="2024B",
            anio=2024, vig_desde=date(2024, 8, 1),
        ))

        results = await cohorte_svc.listar()
        assert len(results) == 2

    async def test_actualizar_cohorte(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        carrera_svc = CarreraService(db_session, tenant.id)
        carrera = await carrera_svc.crear(
            CarreraCreate(codigo="LIC", nombre="Licenciatura")
        )

        cohorte_svc = CohorteService(db_session, tenant.id)
        coh = await cohorte_svc.crear(CohorteCreate(
            carrera_id=str(carrera.id), nombre="2024A",
            anio=2024, vig_desde=date(2024, 3, 1),
        ))

        updated = await cohorte_svc.actualizar(
            coh.id, CohorteUpdate(estado="Inactiva")
        )
        assert updated is not None
        assert updated.estado == "Inactiva"
