"""Tests de integración para modelos Usuario y Asignacion (C-07).

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
from app.core.exceptions import BusinessError
from tests.conftest import db_available

pytestmark = [
    pytest.mark.skipif(
        not db_available(),
        reason="Requiere PostgreSQL: definir DATABASE_URL_TEST en el entorno",
    ),
]


@pytest_asyncio.fixture
async def tenant(db_session: AsyncSession) -> Tenant:
    """Creates a tenant for testing."""
    tid = uuid.uuid4()
    t = Tenant(id=tid, tenant_id=tid, nombre="UsuarioTest")
    db_session.add(t)
    await db_session.flush()
    return t


@pytest_asyncio.fixture
async def tenant_b(db_session: AsyncSession) -> Tenant:
    """Second tenant for isolation tests."""
    tid = uuid.uuid4()
    t = Tenant(id=tid, tenant_id=tid, nombre="UsuarioTestB")
    db_session.add(t)
    await db_session.flush()
    return t


# ===========================================================================
# Usuario Model Tests
# ===========================================================================


class TestUsuarioModel:
    """Tests for Usuario model creation and constraints."""

    async def test_crear_usuario_basico(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        """Happy path: crear un usuario con campos mínimos."""
        from app.models.usuario import Usuario

        user = Usuario(
            tenant_id=tenant.id,
            nombre="Juan",
            apellidos="Pérez",
            email="juan@example.com",
            dni="12345678",
            cuil="20-12345678-9",
            estado="Activo",
        )
        db_session.add(user)
        await db_session.flush()

        assert user.id is not None
        assert user.tenant_id == tenant.id
        assert user.nombre == "Juan"
        assert user.apellidos == "Pérez"
        assert user.email == "juan@example.com"
        assert user.estado == "Activo"
        assert user.deleted_at is None
        assert isinstance(user.created_at, datetime)

    async def test_crear_usuario_con_datos_completos(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        """Crear usuario con todos los campos opcionales."""
        from app.models.usuario import Usuario

        user = Usuario(
            tenant_id=tenant.id,
            nombre="María",
            apellidos="González",
            email="maria@example.com",
            dni="87654321",
            cuil="27-87654321-8",
            cbu="0000003100012345678901",
            alias_cbu="maria.banco",
            banco="Banco Nación",
            regional="Centro",
            legajo="LEG-001",
            legajo_profesional="LP-001",
            facturador="Facturador A",
            estado="Activo",
        )
        db_session.add(user)
        await db_session.flush()

        assert user.email == "maria@example.com"
        assert user.dni == "87654321"
        assert user.cuil == "27-87654321-8"
        assert user.cbu == "0000003100012345678901"
        assert user.alias_cbu == "maria.banco"
        assert user.banco == "Banco Nación"
        assert user.legajo == "LEG-001"
        assert user.legajo_profesional == "LP-001"
        assert user.facturador == "Facturador A"

    async def test_crear_usuario_legajo_opcional(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        """Legajo es opcional — crear usuario sin legajo."""
        from app.models.usuario import Usuario

        user = Usuario(
            tenant_id=tenant.id,
            nombre="Sin",
            apellidos="Legajo",
            email="sinlegajo@example.com",
            dni="11111111",
        )
        db_session.add(user)
        await db_session.flush()

        assert user.legajo is None
        assert user.legajo_profesional is None


# ===========================================================================
# Asignacion Model Tests
# ===========================================================================


class TestAsignacionModel:
    """Tests for Asignacion model creation and constraints."""

    async def test_crear_asignacion_basica(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        """Happy path: crear asignación con campos mínimos."""
        from app.models.usuario import Usuario
        from app.models.asignacion import Asignacion

        usuario = Usuario(
            tenant_id=tenant.id,
            nombre="Juan",
            apellidos="Pérez",
            email="juan.asig@example.com",
            dni="99999999",
        )
        db_session.add(usuario)
        await db_session.flush()

        asignacion = Asignacion(
            tenant_id=tenant.id,
            usuario_id=usuario.id,
            rol="PROFESOR",
            desde=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        db_session.add(asignacion)
        await db_session.flush()

        assert asignacion.id is not None
        assert asignacion.usuario_id == usuario.id
        assert asignacion.rol == "PROFESOR"
        assert asignacion.desde is not None
        assert asignacion.hasta is None
        assert asignacion.deleted_at is None

    async def test_crear_asignacion_global(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        """Asignación global sin contexto académico (solo rol global)."""
        from app.models.usuario import Usuario
        from app.models.asignacion import Asignacion

        usuario = Usuario(
            tenant_id=tenant.id,
            nombre="Admin",
            apellidos="Global",
            email="global@example.com",
            dni="88888888",
        )
        db_session.add(usuario)
        await db_session.flush()

        asignacion = Asignacion(
            tenant_id=tenant.id,
            usuario_id=usuario.id,
            rol="FINANZAS",
            desde=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        db_session.add(asignacion)
        await db_session.flush()

        assert asignacion.rol == "FINANZAS"
        assert asignacion.materia_id is None
        assert asignacion.carrera_id is None
        assert asignacion.cohorte_id is None

    async def test_crear_asignacion_con_responsable(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        """Asignación con responsable (jerarquía)."""
        from app.models.usuario import Usuario
        from app.models.asignacion import Asignacion

        responsable = Usuario(
            tenant_id=tenant.id,
            nombre="Coord",
            apellidos="Responsable",
            email="coord@example.com",
            dni="77777777",
        )
        db_session.add(responsable)
        await db_session.flush()

        tutor = Usuario(
            tenant_id=tenant.id,
            nombre="Tutor",
            apellidos="Asignado",
            email="tutor@example.com",
            dni="66666666",
        )
        db_session.add(tutor)
        await db_session.flush()

        asignacion = Asignacion(
            tenant_id=tenant.id,
            usuario_id=tutor.id,
            rol="TUTOR",
            responsable_id=responsable.id,
            desde=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        db_session.add(asignacion)
        await db_session.flush()

        assert asignacion.responsable_id == responsable.id

    async def test_asignacion_con_vigencia_acotada(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        """Asignación con fecha hasta."""
        from app.models.usuario import Usuario
        from app.models.asignacion import Asignacion

        usuario = Usuario(
            tenant_id=tenant.id,
            nombre="Temp",
            apellidos="Employee",
            email="temp@example.com",
            dni="55555555",
        )
        db_session.add(usuario)
        await db_session.flush()

        desde = datetime(2024, 1, 1, tzinfo=timezone.utc)
        hasta = datetime(2024, 12, 31, tzinfo=timezone.utc)
        asignacion = Asignacion(
            tenant_id=tenant.id,
            usuario_id=usuario.id,
            rol="PROFESOR",
            desde=desde,
            hasta=hasta,
        )
        db_session.add(asignacion)
        await db_session.flush()

        assert asignacion.desde == desde
        assert asignacion.hasta == hasta
