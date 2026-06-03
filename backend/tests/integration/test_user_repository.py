"""Tests de integración para UserRepository contra PostgreSQL real.

Ejercita creación, lookup por email, password update, TOTP enable/disable,
soft delete, unique constraint y multi-tenant isolation.
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.core.security import hash_password, verify_password
from app.models.tenant import Tenant
from app.models.user import User
from app.repositories.user_repository import UserRepository
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
    tenant = Tenant(id=tid, tenant_id=tid, nombre="UserRepoTest")
    db_session.add(tenant)
    await db_session.flush()
    return tenant


@pytest_asyncio.fixture
async def tenant_b(db_session) -> Tenant:
    tid = uuid.uuid4()
    tenant = Tenant(id=tid, tenant_id=tid, nombre="UserRepoTestB")
    db_session.add(tenant)
    await db_session.flush()
    return tenant


def _make_repo(db_session, tenant: Tenant) -> UserRepository:
    return UserRepository(session=db_session, tenant_id=tenant.id)


class TestUserRepositoryCreateAndRead:
    """Tests de creación y lectura básica."""

    async def test_create_user_persists_fields(
        self, db_session, tenant: Tenant,
    ) -> None:
        """GIVEN repositorio WHEN create THEN todos los campos se persisten."""
        repo = _make_repo(db_session, tenant)
        pw_hash = hash_password("secure123")

        user = await repo.create(
            email="alice@example.com",
            password_hash=pw_hash,
            is_active=True,
        )

        assert user.email == "alice@example.com"
        assert user.password_hash == pw_hash
        assert user.is_active is True
        assert user.tenant_id == tenant.id
        assert user.id is not None
        assert user.created_at is not None
        assert user.deleted_at is None

    async def test_create_user_inactive(
        self, db_session, tenant: Tenant,
    ) -> None:
        """GIVEN create con is_active=False WHEN leer THEN is_active es False."""
        repo = _make_repo(db_session, tenant)
        user = await repo.create(
            email="bob@example.com",
            password_hash=hash_password("p4ss"),
            is_active=False,
        )
        assert user.is_active is False

    async def test_get_by_id_returns_user(
        self, db_session, tenant: Tenant,
    ) -> None:
        """GIVEN usuario persistido WHEN get_by_id THEN retorna el usuario."""
        repo = _make_repo(db_session, tenant)
        created = await repo.create(
            email="carol@example.com",
            password_hash=hash_password("p4ss"),
        )
        loaded = await repo.get_by_id(created.id)
        assert loaded is not None
        assert loaded.email == "carol@example.com"


class TestUserRepositoryEmailLookup:
    """Tests de get_by_email con y sin multi-tenant isolation."""

    async def test_get_by_email_finds_user(
        self, db_session, tenant: Tenant,
    ) -> None:
        """GIVEN usuario en tenant WHEN get_by_email THEN lo encuentra."""
        repo = _make_repo(db_session, tenant)
        await repo.create(
            email="dave@example.com",
            password_hash=hash_password("p4ss"),
        )
        found = await repo.get_by_email("dave@example.com")
        assert found is not None
        assert found.email == "dave@example.com"

    async def test_get_by_email_other_tenant_returns_none(
        self, db_session, tenant: Tenant, tenant_b: Tenant,
    ) -> None:
        """GIVEN usuario en T2 WHEN get_by_email desde T1 THEN None."""
        repo_t1 = _make_repo(db_session, tenant)
        repo_t2 = _make_repo(db_session, tenant_b)
        await repo_t2.create(
            email="eve@example.com",
            password_hash=hash_password("p4ss"),
        )
        found = await repo_t1.get_by_email("eve@example.com")
        assert found is None, "T1 NO debe encontrar email de T2"

    async def test_get_by_email_nonexistent_returns_none(
        self, db_session, tenant: Tenant,
    ) -> None:
        """GIVEN tenant sin usuarios WHEN get_by_email THEN None."""
        repo = _make_repo(db_session, tenant)
        found = await repo.get_by_email("ghost@example.com")
        assert found is None


class TestUserRepositoryPasswordUpdate:
    """Tests de update_password."""

    async def test_update_password_works(
        self, db_session, tenant: Tenant,
    ) -> None:
        """GIVEN usuario con password WHEN update_password THEN nuevo hash
        verifica correctamente y el anterior no."""
        repo = _make_repo(db_session, tenant)
        user = await repo.create(
            email="frank@example.com",
            password_hash=hash_password("old_pass"),
        )

        new_hash = hash_password("new_pass")
        await repo.update_password(user_id=user.id, new_hash=new_hash)

        loaded = await repo.get_by_id(user.id)
        assert loaded is not None
        assert verify_password("new_pass", loaded.password_hash) is True
        assert verify_password("old_pass", loaded.password_hash) is False


class TestUserRepositoryTOTP:
    """Tests de enable_totp / disable_totp."""

    async def test_enable_totp_sets_fields(
        self, db_session, tenant: Tenant,
    ) -> None:
        """GIVEN usuario sin 2FA WHEN enable_totp THEN totp_secret no es nulo
        y totp_enabled es True."""
        repo = _make_repo(db_session, tenant)
        user = await repo.create(
            email="grace@example.com",
            password_hash=hash_password("p4ss"),
        )

        await repo.enable_totp(
            user_id=user.id,
            encrypted_secret="JBSWY3DPEHPK3PXP",
        )

        loaded = await repo.get_by_id(user.id)
        assert loaded is not None
        assert loaded.totp_secret is not None
        assert loaded.totp_secret == "JBSWY3DPEHPK3PXP"
        assert loaded.totp_enabled is True

    async def test_disable_totp_clears_fields(
        self, db_session, tenant: Tenant,
    ) -> None:
        """GIVEN usuario con TOTP activo WHEN disable_totp THEN totp_enabled
        es False y totp_secret es None."""
        repo = _make_repo(db_session, tenant)
        user = await repo.create(
            email="heidi@example.com",
            password_hash=hash_password("p4ss"),
        )
        await repo.enable_totp(
            user_id=user.id,
            encrypted_secret="JBSWY3DPEHPK3PXP",
        )

        await repo.disable_totp(user_id=user.id)

        loaded = await repo.get_by_id(user.id)
        assert loaded is not None
        assert loaded.totp_enabled is False
        assert loaded.totp_secret is None

    async def test_enable_totp_on_nonexistent_user_does_not_raise(
        self, db_session, tenant: Tenant,
    ) -> None:
        """GIVEN usuario inexistente WHEN enable_totp THEN no levanta
        (update con 0 filas afectadas es válido)."""
        repo = _make_repo(db_session, tenant)
        await repo.enable_totp(
            user_id=uuid.uuid4(),
            encrypted_secret="JBSWY3DPEHPK3PXP",
        )


class TestUserRepositorySoftDelete:
    """Tests de soft delete en UserRepository."""

    async def test_soft_delete_hides_from_get_by_id(
        self, db_session, tenant: Tenant,
    ) -> None:
        """GIVEN usuario activo WHEN soft_delete THEN get_by_id retorna None."""
        repo = _make_repo(db_session, tenant)
        user = await repo.create(
            email="ivan@example.com",
            password_hash=hash_password("p4ss"),
        )

        await repo.soft_delete(user)

        loaded = await repo.get_by_id(user.id)
        assert loaded is None

    async def test_soft_delete_excludes_from_list_all(
        self, db_session, tenant: Tenant,
    ) -> None:
        """GIVEN usuario soft-deleteado WHEN list_all THEN no aparece."""
        repo = _make_repo(db_session, tenant)
        await repo.create(
            email="judy@example.com",
            password_hash=hash_password("p4ss"),
        )
        to_delete = await repo.create(
            email="karl@example.com",
            password_hash=hash_password("p4ss"),
        )

        await repo.soft_delete(to_delete)

        results = await repo.list_all()
        emails = {u.email for u in results}
        assert "judy@example.com" in emails
        assert "karl@example.com" not in emails

    async def test_soft_delete_is_append_only(
        self, db_session, tenant: Tenant,
    ) -> None:
        """GIVEN usuario soft-deleteado WHEN query directa sin scope THEN
        el registro existe (no eliminación física)."""
        repo = _make_repo(db_session, tenant)
        user = await repo.create(
            email="leo@example.com",
            password_hash=hash_password("p4ss"),
        )
        await repo.soft_delete(user)

        stmt = select(User).where(User.id == user.id)
        result = await db_session.execute(stmt)
        loaded = result.scalar_one_or_none()
        assert loaded is not None
        assert loaded.deleted_at is not None


class TestUserRepositoryConstraints:
    """Tests de constraints y casos borde."""

    async def test_unique_email_per_tenant_violation(
        self, db_session, tenant: Tenant,
    ) -> None:
        """GIVEN email existente en tenant WHEN create mismo email THEN
        levanta excepción de integridad."""
        repo = _make_repo(db_session, tenant)
        await repo.create(
            email="mia@example.com",
            password_hash=hash_password("p4ss"),
        )
        import sqlalchemy.exc

        with pytest.raises(sqlalchemy.exc.IntegrityError):
            await repo.create(
                email="mia@example.com",
                password_hash=hash_password("other_p4ss"),
            )

    async def test_same_email_different_tenants_allowed(
        self, db_session, tenant: Tenant, tenant_b: Tenant,
    ) -> None:
        """GIVEN mismo email en T1 y T2 WHEN crear en ambos THEN no
        viola unique constraint (el unique es por tenant)."""
        repo_t1 = _make_repo(db_session, tenant)
        repo_t2 = _make_repo(db_session, tenant_b)

        u1 = await repo_t1.create(
            email="shared@example.com",
            password_hash=hash_password("p4ss"),
        )
        u2 = await repo_t2.create(
            email="shared@example.com",
            password_hash=hash_password("p4ss"),
        )
        assert u1.id != u2.id
        assert u1.tenant_id != u2.tenant_id
