"""Tests de integración para UsuarioService y AsignacionService (C-07).

Requiere PostgreSQL real (DATABASE_URL_TEST en el entorno).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError
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
    t = Tenant(id=tid, tenant_id=tid, nombre="SvcTest")
    db_session.add(t)
    await db_session.flush()
    return t


@pytest_asyncio.fixture
async def tenant_b(db_session: AsyncSession) -> Tenant:
    tid = uuid.uuid4()
    t = Tenant(id=tid, tenant_id=tid, nombre="SvcTestB")
    db_session.add(t)
    await db_session.flush()
    return t


# ===========================================================================
# UsuarioService Tests
# ===========================================================================


class TestUsuarioService:
    """Tests for UsuarioService."""

    async def _build_svc(self, db_session: AsyncSession, tenant: Tenant):
        from app.services.usuario_service import UsuarioService
        return UsuarioService(session=db_session, tenant_id=tenant.id)

    async def test_create_usuario_exitoso(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        """Happy path: crear usuario con datos mínimos."""
        from app.schemas.usuario import UsuarioCreate

        svc = await self._build_svc(db_session, tenant)
        data = UsuarioCreate(
            nombre="Juan",
            apellidos="Pérez",
            email="juan@example.com",
        )
        usuario = await svc.create(data)

        assert usuario.nombre == "Juan"
        assert usuario.apellidos == "Pérez"
        assert usuario.email == "juan@example.com"
        assert usuario.estado == "Activo"
        assert usuario.tenant_id == tenant.id

    async def test_create_usuario_con_pii(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        """Crear usuario con todos los campos PII."""
        from app.schemas.usuario import UsuarioCreate

        svc = await self._build_svc(db_session, tenant)
        data = UsuarioCreate(
            nombre="María",
            apellidos="González",
            email="maria@example.com",
            dni="12345678",
            cuil="20-12345678-9",
            cbu="0000003100012345678901",
            alias_cbu="maria.banco",
            banco="Banco Nación",
            legajo="LEG-001",
        )
        usuario = await svc.create(data)

        assert usuario.dni == "12345678"
        assert usuario.cuil == "20-12345678-9"
        assert usuario.legajo == "LEG-001"

    async def test_create_email_duplicado_mismo_tenant_raise(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        """Email duplicado en mismo tenant → BusinessError."""
        from app.schemas.usuario import UsuarioCreate

        svc = await self._build_svc(db_session, tenant)
        data = UsuarioCreate(
            nombre="Juan", apellidos="Pérez",
            email="dupe@example.com",
        )
        await svc.create(data)

        with pytest.raises(BusinessError) as exc:
            await svc.create(data)
        assert "email" in str(exc.value.message).lower()

    async def test_create_mismo_email_distinto_tenant_ok(
        self, db_session: AsyncSession, tenant: Tenant, tenant_b: Tenant
    ) -> None:
        """Mismo email en distinto tenant NO debe fallar."""
        from app.schemas.usuario import UsuarioCreate

        svc_a = await self._build_svc(db_session, tenant)
        svc_b = await self._build_svc(db_session, tenant_b)
        data = UsuarioCreate(
            nombre="A", apellidos="B", email="same@example.com",
        )

        await svc_a.create(data)
        usuario = await svc_b.create(data)
        assert usuario.email == "same@example.com"

    async def test_soft_delete_no_reusar_email(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        """Soft-delete NO permite re-uso del email (auth User lo bloquea).

        La tabla ``users`` tiene un ``UniqueConstraint(tenant_id, email)``
        sin filtro de soft-delete, por lo que el email no puede re-usarse
        aunque el ``Usuario`` esté soft-deleted.
        """
        from app.schemas.usuario import UsuarioCreate

        svc = await self._build_svc(db_session, tenant)
        data = UsuarioCreate(
            nombre="Delete", apellidos="Me",
            email="noreuse@example.com",
        )
        usuario = await svc.create(data)

        # Soft delete — usuario ya no aparece en queries normales
        await svc.soft_delete(usuario.id)
        deleted = await svc.obtener(usuario.id)
        assert deleted is None

        # Re-crear con mismo email falla por UniqueConstraint en users
        with pytest.raises(BusinessError) as exc:
            await svc.create(data)
        assert "email" in str(exc.value.message).lower()

    async def test_obtener_usuario(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        """Obtener usuario por ID."""
        from app.schemas.usuario import UsuarioCreate

        svc = await self._build_svc(db_session, tenant)
        data = UsuarioCreate(
            nombre="Find", apellidos="Me",
            email="find.service@example.com",
        )
        creado = await svc.create(data)

        encontrado = await svc.obtener(creado.id)
        assert encontrado is not None
        assert encontrado.nombre == "Find"

    async def test_obtener_usuario_inexistente(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        """Obtener usuario que no existe retorna None."""
        svc = await self._build_svc(db_session, tenant)
        encontrado = await svc.obtener(uuid.uuid4())
        assert encontrado is None

    async def test_listar_usuarios(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        """Listar usuarios del tenant."""
        from app.schemas.usuario import UsuarioCreate

        svc = await self._build_svc(db_session, tenant)
        for i in range(3):
            await svc.create(UsuarioCreate(
                nombre=f"User{i}", apellidos="Test",
                email=f"svc.user{i}@example.com",
            ))

        results = await svc.listar()
        assert len(results) == 3

    async def test_update_usuario(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        """Actualizar datos de un usuario."""
        from app.schemas.usuario import UsuarioCreate, UsuarioUpdate

        svc = await self._build_svc(db_session, tenant)
        creado = await svc.create(UsuarioCreate(
            nombre="Original", apellidos="Name",
            email="update@example.com",
        ))

        actualizado = await svc.actualizar(
            creado.id, UsuarioUpdate(nombre="Modificado")
        )
        assert actualizado is not None
        assert actualizado.nombre == "Modificado"

    async def test_update_usuario_inexistente(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        """Actualizar usuario inexistente retorna None."""
        from app.schemas.usuario import UsuarioUpdate

        svc = await self._build_svc(db_session, tenant)
        result = await svc.actualizar(
            uuid.uuid4(), UsuarioUpdate(nombre="X")
        )
        assert result is None


# ===========================================================================
# AsignacionService Tests
# ===========================================================================


class TestAsignacionService:
    """Tests for AsignacionService."""

    async def _seed_usuario(self, db_session, tenant, email="base@test.com"):
        from app.models.usuario import Usuario

        u = Usuario(
            tenant_id=tenant.id, nombre="Base", apellidos="User",
            email=email, dni="00000000",
        )
        db_session.add(u)
        await db_session.flush()
        return u

    async def _build_svc(self, db_session: AsyncSession, tenant: Tenant):
        from app.services.asignacion_service import AsignacionService
        return AsignacionService(session=db_session, tenant_id=tenant.id)

    async def test_create_asignacion_exitosa(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        """Happy path: crear asignación."""
        from app.schemas.asignacion import AsignacionCreate

        usuario = await self._seed_usuario(db_session, tenant)
        svc = await self._build_svc(db_session, tenant)

        data = AsignacionCreate(
            usuario_id=str(usuario.id),
            rol="PROFESOR",
            desde=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        asignacion = await svc.create(data)

        assert asignacion.usuario_id == usuario.id
        assert asignacion.rol == "PROFESOR"
        assert asignacion.tenant_id == tenant.id

    async def test_create_asignacion_usuario_inexistente(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        """Asignación con usuario que no existe → BusinessError."""
        from app.schemas.asignacion import AsignacionCreate

        svc = await self._build_svc(db_session, tenant)
        data = AsignacionCreate(
            usuario_id=str(uuid.uuid4()),
            rol="PROFESOR",
            desde=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )

        with pytest.raises(BusinessError) as exc:
            await svc.create(data)
        assert "usuario" in str(exc.value.message).lower()

    async def test_asignacion_multi_rol(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        """Un usuario puede tener múltiples roles."""
        from app.schemas.asignacion import AsignacionCreate

        usuario = await self._seed_usuario(db_session, tenant)
        svc = await self._build_svc(db_session, tenant)

        await svc.create(AsignacionCreate(
            usuario_id=str(usuario.id), rol="PROFESOR",
            desde=datetime(2024, 1, 1, tzinfo=timezone.utc),
        ))
        await svc.create(AsignacionCreate(
            usuario_id=str(usuario.id), rol="COORDINADOR",
            desde=datetime(2024, 1, 1, tzinfo=timezone.utc),
        ))

        asignaciones = await svc.listar_por_usuario(usuario.id)
        assert len(asignaciones) == 2

    async def test_asignacion_con_jerarquia(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        """Asignación con responsable (jerarquía)."""
        from app.schemas.asignacion import AsignacionCreate

        responsable = await self._seed_usuario(
            db_session, tenant, "responsable@test.com"
        )
        tutor = await self._seed_usuario(
            db_session, tenant, "tutor@test.com"
        )
        svc = await self._build_svc(db_session, tenant)

        data = AsignacionCreate(
            usuario_id=str(tutor.id),
            rol="TUTOR",
            responsable_id=str(responsable.id),
            desde=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        asignacion = await svc.create(data)

        assert asignacion.responsable_id == responsable.id

    async def test_soft_delete_asignacion(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        """Soft-delete preserva histórico."""
        from app.schemas.asignacion import AsignacionCreate

        usuario = await self._seed_usuario(db_session, tenant)
        svc = await self._build_svc(db_session, tenant)

        data = AsignacionCreate(
            usuario_id=str(usuario.id), rol="PROFESOR",
            desde=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        a = await svc.create(data)

        await svc.soft_delete(a.id)

        # Should not be returned by normal list
        asignaciones = await svc.listar_por_usuario(usuario.id)
        assert len(asignaciones) == 0

    async def test_listar_asignaciones_vigentes_y_vencidas(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        """Listado incluye vigentes y vencidas con estado."""
        from app.schemas.asignacion import AsignacionCreate

        usuario = await self._seed_usuario(db_session, tenant)
        svc = await self._build_svc(db_session, tenant)

        now = datetime.now(timezone.utc)

        # Vigente (sin hasta)
        await svc.create(AsignacionCreate(
            usuario_id=str(usuario.id), rol="PROFESOR",
            desde=now - timedelta(days=30),
        ))
        # Vencida
        await svc.create(AsignacionCreate(
            usuario_id=str(usuario.id), rol="TUTOR",
            desde=datetime(2020, 1, 1, tzinfo=timezone.utc),
            hasta=datetime(2020, 6, 1, tzinfo=timezone.utc),
        ))

        todas = await svc.listar_por_usuario(usuario.id)
        assert len(todas) == 2
