"""Tests de integración para el modelo UmbralMateria (C-10).

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
    t = Tenant(id=tid, tenant_id=tid, nombre="UmbralTest")
    db_session.add(t)
    await db_session.flush()
    return t


@pytest_asyncio.fixture
async def materia(tenant: Tenant, db_session: AsyncSession) -> object:
    from app.models.materia import Materia

    m = Materia(tenant_id=tenant.id, codigo="MAT-999", nombre="Test Materia")
    db_session.add(m)
    await db_session.flush()
    return m


@pytest_asyncio.fixture
async def usuario(tenant: Tenant, db_session: AsyncSession) -> object:
    from app.models.usuario import Usuario

    u = Usuario(
        tenant_id=tenant.id,
        nombre="Coord",
        apellidos="Test",
        email="coord.umbral@test.com",
        dni="11111111",
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest_asyncio.fixture
async def asignacion(tenant: Tenant, usuario: object, db_session: AsyncSession) -> object:
    from app.models.asignacion import Asignacion

    a = Asignacion(
        tenant_id=tenant.id,
        usuario_id=usuario.id,
        rol="PROFESOR",
        desde=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    db_session.add(a)
    await db_session.flush()
    return a


class TestUmbralMateriaModel:
    """Tests for UmbralMateria model creation and constraints."""

    async def test_crear_con_valores_default(
        self, db_session: AsyncSession, tenant: Tenant, materia, asignacion
    ) -> None:
        """Crear umbral con valores por defecto → umbral_pct=60."""
        from app.models.umbral_materia import UmbralMateria

        u = UmbralMateria(
            tenant_id=tenant.id,
            asignacion_id=asignacion.id,
            materia_id=materia.id,
        )
        db_session.add(u)
        await db_session.flush()

        assert u.id is not None
        assert u.umbral_pct == 60
        assert u.valores_aprobatorios is None
        assert u.deleted_at is None
        assert isinstance(u.created_at, datetime)

    async def test_crear_con_valores_personalizados(
        self, db_session: AsyncSession, tenant: Tenant, materia, asignacion
    ) -> None:
        """Crear umbral con valores personalizados."""
        from app.models.umbral_materia import UmbralMateria

        u = UmbralMateria(
            tenant_id=tenant.id,
            asignacion_id=asignacion.id,
            materia_id=materia.id,
            umbral_pct=75,
            valores_aprobatorios=["Aprobado", "Promocionado"],
        )
        db_session.add(u)
        await db_session.flush()

        assert u.umbral_pct == 75
        assert u.valores_aprobatorios == ["Aprobado", "Promocionado"]

    async def test_unique_index_soft_delete(
        self, db_session: AsyncSession, tenant: Tenant, materia, asignacion
    ) -> None:
        """Soft-delete primero, crear segundo con misma asignacion+materia → OK."""
        from app.models.umbral_materia import UmbralMateria

        u1 = UmbralMateria(
            tenant_id=tenant.id,
            asignacion_id=asignacion.id,
            materia_id=materia.id,
            umbral_pct=60,
        )
        db_session.add(u1)
        await db_session.flush()

        # Soft-delete u1
        u1.deleted_at = datetime.now(timezone.utc)
        await db_session.flush()

        # Crear u2 con misma asignacion+materia
        u2 = UmbralMateria(
            tenant_id=tenant.id,
            asignacion_id=asignacion.id,
            materia_id=materia.id,
            umbral_pct=80,
        )
        db_session.add(u2)
        await db_session.flush()

        assert u2.id != u1.id
        assert u2.umbral_pct == 80

    async def test_unique_index_activo_duplicado_falla(
        self, db_session: AsyncSession, tenant: Tenant, materia, asignacion
    ) -> None:
        """Dos umbrales activos con misma asignacion+materia → error."""
        from app.models.umbral_materia import UmbralMateria

        u1 = UmbralMateria(
            tenant_id=tenant.id,
            asignacion_id=asignacion.id,
            materia_id=materia.id,
            umbral_pct=60,
        )
        db_session.add(u1)
        await db_session.flush()

        u2 = UmbralMateria(
            tenant_id=tenant.id,
            asignacion_id=asignacion.id,
            materia_id=materia.id,
            umbral_pct=70,
        )
        db_session.add(u2)
        with pytest.raises(Exception) as excinfo:
            await db_session.flush()
        err = str(excinfo.value).lower()
        assert "unique" in err or "duplicate" in err or "already exists" in err
