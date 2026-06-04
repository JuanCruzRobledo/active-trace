"""Tests de integración para el modelo Calificacion (C-10).

Requiere PostgreSQL real (DATABASE_URL_TEST en el entorno).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import text
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
    t = Tenant(id=tid, tenant_id=tid, nombre="CalifTest")
    db_session.add(t)
    await db_session.flush()
    return t


@pytest_asyncio.fixture
async def materia(tenant: Tenant, db_session: AsyncSession) -> object:
    from app.models.materia import Materia

    m = Materia(
        tenant_id=tenant.id, codigo="MAT-101", nombre="Matematicas"
    )
    db_session.add(m)
    await db_session.flush()
    return m


@pytest_asyncio.fixture
async def entrada_padron(tenant: Tenant, materia, db_session: AsyncSession) -> object:
    from app.models.carrera import Carrera
    from app.models.version_padron import VersionPadron
    from app.models.entrada_padron import EntradaPadron
    from app.models.cohorte import Cohorte

    carrera = Carrera(
        tenant_id=tenant.id,
        codigo="ING-01",
        nombre="Ingenieria",
    )
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
        nombre="Juan",
        apellidos="Perez",
        email="juan@test.com",
    )
    db_session.add(ep)
    await db_session.flush()
    return ep


class TestCalificacionModel:
    """Tests for Calificacion model creation and constraints."""

    async def test_crear_con_nota_numerica(
        self, db_session: AsyncSession, tenant: Tenant, materia, entrada_padron
    ) -> None:
        """Crear calificación con nota numérica."""
        from app.models.calificacion import Calificacion

        c = Calificacion(
            tenant_id=tenant.id,
            entrada_padron_id=entrada_padron.id,
            materia_id=materia.id,
            actividad="Parcial 1",
            nota_numerica=8.50,
            aprobado=True,
            origen=OrigenCalificacion.IMPORTADO,
        )
        db_session.add(c)
        await db_session.flush()

        assert c.id is not None
        assert c.nota_numerica == 8.50
        assert c.nota_textual is None
        assert c.aprobado is True
        assert c.origen == OrigenCalificacion.IMPORTADO
        assert c.deleted_at is None
        assert isinstance(c.created_at, datetime)
        assert isinstance(c.importado_at, datetime)

    async def test_crear_con_nota_textual(
        self, db_session: AsyncSession, tenant: Tenant, materia, entrada_padron
    ) -> None:
        """Crear calificación con nota textual."""
        from app.models.calificacion import Calificacion

        c = Calificacion(
            tenant_id=tenant.id,
            entrada_padron_id=entrada_padron.id,
            materia_id=materia.id,
            actividad="Trabajo Practico",
            nota_textual="Aprobado",
            origen=OrigenCalificacion.MANUAL,
        )
        db_session.add(c)
        await db_session.flush()

        assert c.id is not None
        assert c.nota_textual == "Aprobado"
        assert c.nota_numerica is None
        assert c.aprobado is None
        assert c.origen == OrigenCalificacion.MANUAL

    async def test_crear_sin_nota_raise_error(
        self, db_session: AsyncSession, tenant: Tenant, materia, entrada_padron
    ) -> None:
        """Crear calificación sin nota numérica ni textual debe fallar."""
        from app.models.calificacion import Calificacion

        c = Calificacion(
            tenant_id=tenant.id,
            entrada_padron_id=entrada_padron.id,
            materia_id=materia.id,
            actividad="Sin nota",
            origen=OrigenCalificacion.MANUAL,
        )
        db_session.add(c)
        with pytest.raises(Exception, match="nota_numerica|nota_textual|al menos una nota"):
            await db_session.flush()

    async def test_soft_delete(
        self, db_session: AsyncSession, tenant: Tenant, materia, entrada_padron
    ) -> None:
        """Soft-delete setea deleted_at."""
        from app.models.calificacion import Calificacion

        c = Calificacion(
            tenant_id=tenant.id,
            entrada_padron_id=entrada_padron.id,
            materia_id=materia.id,
            actividad="Parcial 2",
            nota_numerica=7.00,
            origen=OrigenCalificacion.IMPORTADO,
        )
        db_session.add(c)
        await db_session.flush()

        assert c.deleted_at is None

        c.deleted_at = datetime.now(timezone.utc)
        await db_session.flush()

        assert c.deleted_at is not None

    async def test_fk_entrada_padron(
        self, db_session: AsyncSession, tenant: Tenant, materia
    ) -> None:
        """FK a entrada_padron inválida debe fallar."""
        from app.models.calificacion import Calificacion

        fake_id = uuid.uuid4()
        c = Calificacion(
            tenant_id=tenant.id,
            entrada_padron_id=fake_id,
            materia_id=materia.id,
            actividad="Test FK",
            nota_numerica=5.00,
            origen=OrigenCalificacion.IMPORTADO,
        )
        db_session.add(c)
        with pytest.raises(Exception) as excinfo:
            await db_session.flush()
        err = str(excinfo.value)
        assert (
            "foreign key" in err.lower()
            or "violates" in err.lower()
            or "entrada_padron" in err
        )

    async def test_fk_materia(
        self, db_session: AsyncSession, tenant: Tenant, entrada_padron
    ) -> None:
        """FK a materia inválida debe fallar."""
        from app.models.calificacion import Calificacion

        fake_id = uuid.uuid4()
        c = Calificacion(
            tenant_id=tenant.id,
            entrada_padron_id=entrada_padron.id,
            materia_id=fake_id,
            actividad="Test FK Materia",
            nota_numerica=5.00,
            origen=OrigenCalificacion.IMPORTADO,
        )
        db_session.add(c)
        with pytest.raises(Exception) as excinfo:
            await db_session.flush()
        err = str(excinfo.value)
        assert (
            "foreign key" in err.lower()
            or "violates" in err.lower()
            or "materia" in err
        )

    async def test_indice_compuesto(
        self, db_session: AsyncSession, tenant: Tenant, materia, entrada_padron
    ) -> None:
        """Índice compuesto (entrada_padron_id, materia_id, actividad) no debe ser unique,
        solo indexed — dos registros iguales son válidos."""
        from app.models.calificacion import Calificacion

        c1 = Calificacion(
            tenant_id=tenant.id,
            entrada_padron_id=entrada_padron.id,
            materia_id=materia.id,
            actividad="Recuperatorio",
            nota_numerica=4.00,
            origen=OrigenCalificacion.IMPORTADO,
        )
        db_session.add(c1)
        await db_session.flush()

        c2 = Calificacion(
            tenant_id=tenant.id,
            entrada_padron_id=entrada_padron.id,
            materia_id=materia.id,
            actividad="Recuperatorio",
            nota_numerica=6.00,
            origen=OrigenCalificacion.MANUAL,
        )
        db_session.add(c2)
        await db_session.flush()

        assert c1.id != c2.id
