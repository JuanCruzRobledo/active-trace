"""Tests de integración para UsuarioRepository y AsignacionRepository (C-07).

Verifica:
- Scoping por tenant_id
- Soft-delete
- Find by email
- List por contexto
- Find vigentes
- Aislamiento multi-tenant

Requiere PostgreSQL real (DATABASE_URL_TEST en el entorno).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

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
async def tenant(db_session: AsyncSession) -> Tenant:
    tid = uuid.uuid4()
    t = Tenant(id=tid, tenant_id=tid, nombre="RepoTest")
    db_session.add(t)
    await db_session.flush()
    return t


@pytest_asyncio.fixture
async def tenant_b(db_session: AsyncSession) -> Tenant:
    tid = uuid.uuid4()
    t = Tenant(id=tid, tenant_id=tid, nombre="RepoTestB")
    db_session.add(t)
    await db_session.flush()
    return t


# ===========================================================================
# UsuarioRepository Tests
# ===========================================================================


class TestUsuarioRepository:
    """Tests for UsuarioRepository."""

    async def test_save_and_get_by_id(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        from app.models.usuario import Usuario
        from app.repositories.usuario_repository import UsuarioRepository

        repo = UsuarioRepository(db_session, Usuario, tenant.id)

        user = Usuario(
            tenant_id=tenant.id,
            nombre="Repo",
            apellidos="Test",
            email="repo@test.com",
            dni="12345678",
        )
        saved = await repo.save(user)
        assert saved.id is not None

        found = await repo.get_by_id(saved.id)
        assert found is not None
        assert found.nombre == "Repo"
        assert found.email == "repo@test.com"

    async def test_list_all_by_tenant(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        from app.models.usuario import Usuario
        from app.repositories.usuario_repository import UsuarioRepository

        repo = UsuarioRepository(db_session, Usuario, tenant.id)
        for i in range(3):
            await repo.save(Usuario(
                tenant_id=tenant.id,
                nombre=f"User{i}",
                apellidos="Test",
                email=f"user{i}@test.com",
                dni=f"{i:0>8}",
            ))

        results = await repo.list_all()
        assert len(results) == 3

    async def test_find_by_email(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        from app.models.usuario import Usuario
        from app.repositories.usuario_repository import UsuarioRepository

        repo = UsuarioRepository(db_session, Usuario, tenant.id)
        await repo.save(Usuario(
            tenant_id=tenant.id,
            nombre="Find",
            apellidos="Me",
            email="findme@test.com",
            dni="11111111",
        ))

        found = await repo.find_by_email(tenant.id, "findme@test.com")
        assert found is not None
        assert found.nombre == "Find"

    async def test_find_by_email_not_found(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        from app.models.usuario import Usuario
        from app.repositories.usuario_repository import UsuarioRepository

        repo = UsuarioRepository(db_session, Usuario, tenant.id)
        found = await repo.find_by_email(tenant.id, "noexiste@test.com")
        assert found is None

    async def test_find_by_email_other_tenant(
        self, db_session: AsyncSession, tenant: Tenant, tenant_b: Tenant
    ) -> None:
        from app.models.usuario import Usuario
        from app.repositories.usuario_repository import UsuarioRepository

        repo_a = UsuarioRepository(db_session, Usuario, tenant.id)
        await repo_a.save(Usuario(
            tenant_id=tenant.id,
            nombre="UserA",
            apellidos="Test",
            email="same@test.com",
            dni="11111111",
        ))

        repo_b = UsuarioRepository(db_session, Usuario, tenant_b.id)
        found = await repo_b.find_by_email(tenant_b.id, "same@test.com")
        assert found is None

    async def test_soft_delete(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        from app.models.usuario import Usuario
        from app.repositories.usuario_repository import UsuarioRepository

        repo = UsuarioRepository(db_session, Usuario, tenant.id)
        user = await repo.save(Usuario(
            tenant_id=tenant.id,
            nombre="Delete",
            apellidos="Me",
            email="delete@test.com",
            dni="22222222",
        ))

        await repo.soft_delete(user)

        # Should not be findable after soft delete
        found = await repo.get_by_id(user.id)
        assert found is None

        # But should be in all_with_deleted
        all_users = await repo.list_all()  # excludes soft-deleted
        assert len(all_users) == 0

    async def test_list_with_filters(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        from app.models.usuario import Usuario
        from app.repositories.usuario_repository import UsuarioRepository

        repo = UsuarioRepository(db_session, Usuario, tenant.id)
        await repo.save(Usuario(
            tenant_id=tenant.id,
            nombre="Activo",
            apellidos="User",
            email="activo@test.com",
            dni="33333333",
            estado="Activo",
        ))
        await repo.save(Usuario(
            tenant_id=tenant.id,
            nombre="Inactivo",
            apellidos="User",
            email="inactivo@test.com",
            dni="44444444",
            estado="Inactivo",
        ))

        results = await repo.list_by_tenant(estado="Inactivo")
        assert len(results) == 1
        assert results[0].nombre == "Inactivo"


# ===========================================================================
# AsignacionRepository Tests
# ===========================================================================


class TestAsignacionRepository:
    """Tests for AsignacionRepository."""

    async def _seed_usuario(
        self, db_session: AsyncSession, tenant: Tenant, email: str
    ):
        from app.models.usuario import Usuario

        u = Usuario(
            tenant_id=tenant.id,
            nombre="Base",
            apellidos="User",
            email=email,
            dni="00000000",
        )
        db_session.add(u)
        await db_session.flush()
        return u

    async def test_save_and_list(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        from app.models.asignacion import Asignacion
        from app.repositories.asignacion_repository import AsignacionRepository

        usuario = await self._seed_usuario(db_session, tenant, "asig1@test.com")
        repo = AsignacionRepository(db_session, Asignacion, tenant.id)

        a = Asignacion(
            tenant_id=tenant.id,
            usuario_id=usuario.id,
            rol="PROFESOR",
            desde=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        saved = await repo.save(a)
        assert saved.id is not None

        results = await repo.list_all()
        assert len(results) == 1
        assert results[0].rol == "PROFESOR"

    async def test_list_by_usuario(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        from app.models.asignacion import Asignacion
        from app.repositories.asignacion_repository import AsignacionRepository

        u1 = await self._seed_usuario(db_session, tenant, "u1@test.com")
        u2 = await self._seed_usuario(db_session, tenant, "u2@test.com")
        repo = AsignacionRepository(db_session, Asignacion, tenant.id)

        for u in [u1, u2]:
            await repo.save(Asignacion(
                tenant_id=tenant.id,
                usuario_id=u.id,
                rol="PROFESOR",
                desde=datetime(2024, 1, 1, tzinfo=timezone.utc),
            ))

        u1_asigs = await repo.list_by_usuario(u1.id)
        assert len(u1_asigs) == 1

    async def test_find_vigentes(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        from app.models.asignacion import Asignacion
        from app.repositories.asignacion_repository import AsignacionRepository

        usuario = await self._seed_usuario(db_session, tenant, "vig@test.com")
        repo = AsignacionRepository(db_session, Asignacion, tenant.id)

        # Vigente (sin hasta)
        await repo.save(Asignacion(
            tenant_id=tenant.id,
            usuario_id=usuario.id,
            rol="PROFESOR",
            desde=datetime(2024, 1, 1, tzinfo=timezone.utc),
        ))
        # Vencida
        await repo.save(Asignacion(
            tenant_id=tenant.id,
            usuario_id=usuario.id,
            rol="TUTOR",
            desde=datetime(2020, 1, 1, tzinfo=timezone.utc),
            hasta=datetime(2020, 6, 1, tzinfo=timezone.utc),
        ))

        vigentes = await repo.find_vigentes()
        assert len(vigentes) == 1
        assert vigentes[0].rol == "PROFESOR"

    async def test_soft_delete_asignacion(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        from app.models.asignacion import Asignacion
        from app.repositories.asignacion_repository import AsignacionRepository

        usuario = await self._seed_usuario(db_session, tenant, "sdel@test.com")
        repo = AsignacionRepository(db_session, Asignacion, tenant.id)

        a = await repo.save(Asignacion(
            tenant_id=tenant.id,
            usuario_id=usuario.id,
            rol="PROFESOR",
            desde=datetime(2024, 1, 1, tzinfo=timezone.utc),
        ))
        await repo.soft_delete(a)

        found = await repo.get_by_id(a.id)
        assert found is None

    async def test_list_by_context(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        from app.models.asignacion import Asignacion
        from app.models.materia import Materia
        from app.repositories.asignacion_repository import AsignacionRepository

        usuario = await self._seed_usuario(db_session, tenant, "ctx@test.com")
        repo = AsignacionRepository(db_session, Asignacion, tenant.id)

        # Seed a real materia for FK constraint
        materia = Materia(
            tenant_id=tenant.id, codigo="MAT-C07",
            nombre="Materia Test C07",
        )
        db_session.add(materia)
        await db_session.flush()

        # With materia
        await repo.save(Asignacion(
            tenant_id=tenant.id, usuario_id=usuario.id,
            rol="PROFESOR", desde=datetime(2024, 1, 1, tzinfo=timezone.utc),
            materia_id=materia.id,
        ))
        # Without materia
        await repo.save(Asignacion(
            tenant_id=tenant.id, usuario_id=usuario.id,
            rol="COORDINADOR", desde=datetime(2024, 1, 1, tzinfo=timezone.utc),
        ))

        filtered = await repo.list_by_context(materia_id=materia.id)
        assert len(filtered) == 1
        assert filtered[0].rol == "PROFESOR"

        # Filter by non-existent materia returns empty
        fake_id = uuid.uuid4()
        filtered2 = await repo.list_by_context(materia_id=fake_id)
        assert len(filtered2) == 0
