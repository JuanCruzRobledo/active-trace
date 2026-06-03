"""Tests de integración para RefreshTokenRepository contra PostgreSQL real.

Ejercita creación, lookup por hash, revocación individual y masiva,
reuso-detection con revoke_family, conteo de activos y soft delete.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.core.security import hash_password
from app.models.refresh_token import RefreshToken
from app.models.tenant import Tenant
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
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
    tenant = Tenant(id=tid, tenant_id=tid, nombre="RefreshTokenRepoTest")
    db_session.add(tenant)
    await db_session.flush()
    return tenant


@pytest_asyncio.fixture
async def tenant_b(db_session) -> Tenant:
    tid = uuid.uuid4()
    tenant = Tenant(id=tid, tenant_id=tid, nombre="RefreshTokenRepoTestB")
    db_session.add(tenant)
    await db_session.flush()
    return tenant


@pytest_asyncio.fixture
async def user(db_session, tenant: Tenant) -> User:
    repo = UserRepository(session=db_session, tenant_id=tenant.id)
    return await repo.create(
        email="rt_user@example.com",
        password_hash=hash_password("p4ss"),
    )


def _make_repo(db_session, tenant: Tenant) -> RefreshTokenRepository:
    return RefreshTokenRepository(session=db_session, tenant_id=tenant.id)


def _future(seconds: int = 3600) -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=seconds)


def _past(seconds: int = 60) -> datetime:
    return datetime.now(timezone.utc) - timedelta(seconds=seconds)


class TestRefreshTokenRepositoryCreateAndRead:
    """Tests de creación y lookup."""

    async def test_create_token_persists_fields(
        self, db_session, tenant: Tenant, user: User,
    ) -> None:
        """GIVEN repositorio WHEN create THEN todos los campos se persisten."""
        repo = _make_repo(db_session, tenant)
        expires = _future()

        token = await repo.create(
            user_id=user.id,
            token_hash="abc123def456",
            expires_at=expires,
            user_agent="TestAgent/1.0",
            created_ip="192.168.1.1",
        )

        assert token.user_id == user.id
        assert token.token_hash == "abc123def456"
        assert token.expires_at == expires
        assert token.user_agent == "TestAgent/1.0"
        assert token.created_ip == "192.168.1.1"
        assert token.revoked_at is None
        assert token.tenant_id == tenant.id

    async def test_get_by_token_hash_finds_token(
        self, db_session, tenant: Tenant, user: User,
    ) -> None:
        """GIVEN token persistido WHEN get_by_token_hash THEN lo encuentra."""
        repo = _make_repo(db_session, tenant)
        await repo.create(
            user_id=user.id,
            token_hash="unique_hash_001",
            expires_at=_future(),
        )
        found = await repo.get_by_token_hash("unique_hash_001")
        assert found is not None
        assert found.token_hash == "unique_hash_001"

    async def test_get_by_token_hash_nonexistent_returns_none(
        self, db_session, tenant: Tenant,
    ) -> None:
        """GIVEN hash inexistente WHEN get_by_token_hash THEN None."""
        repo = _make_repo(db_session, tenant)
        found = await repo.get_by_token_hash("nonexistent_hash")
        assert found is None


class TestRefreshTokenRepositoryRevoke:
    """Tests de revocación individual y masiva."""

    async def test_revoke_token(
        self, db_session, tenant: Tenant, user: User,
    ) -> None:
        """GIVEN token activo WHEN revoke THEN revoked_at no es None."""
        repo = _make_repo(db_session, tenant)
        token = await repo.create(
            user_id=user.id,
            token_hash="revoke_me",
            expires_at=_future(),
        )

        await repo.revoke(token.id)

        found = await repo.get_by_token_hash("revoke_me")
        assert found is not None
        assert found.revoked_at is not None

    async def test_revoke_all_for_user(
        self, db_session, tenant: Tenant, user: User,
    ) -> None:
        """GIVEN múltiples tokens activos WHEN revoke_all_for_user THEN
        todos quedan revocados."""
        repo = _make_repo(db_session, tenant)
        for i in range(3):
            await repo.create(
                user_id=user.id,
                token_hash=f"bulk_{i}",
                expires_at=_future(),
            )

        await repo.revoke_all_for_user(user_id=user.id)

        for i in range(3):
            found = await repo.get_by_token_hash(f"bulk_{i}")
            assert found is not None
            assert found.revoked_at is not None, (
                f"Token bulk_{i} debería estar revocado"
            )

    async def test_revoke_all_does_not_affect_other_tenants(
        self, db_session, tenant: Tenant, tenant_b: Tenant, user: User,
    ) -> None:
        """GIVEN tokens en T1 y T2 WHEN revoke_all_for_user en T1 THEN
        tokens de T2 no se ven afectados."""
        repo_t1 = _make_repo(db_session, tenant)
        repo_t2 = _make_repo(db_session, tenant_b)
        user_b = await UserRepository(
            session=db_session, tenant_id=tenant_b.id,
        ).create(email="rt_user_b@example.com", password_hash=hash_password("p4ss"))

        await repo_t1.create(
            user_id=user.id, token_hash="t1_token", expires_at=_future(),
        )
        await repo_t2.create(
            user_id=user_b.id, token_hash="t2_token", expires_at=_future(),
        )

        await repo_t1.revoke_all_for_user(user_id=user.id)

        t2_found = await repo_t2.get_by_token_hash("t2_token")
        assert t2_found is not None
        assert t2_found.revoked_at is None, "T2 no debe ser afectado"


class TestRefreshTokenRepositoryCountAndFamily:
    """Tests de conteo de activos y revoke_family."""

    async def test_count_active_for_user(
        self, db_session, tenant: Tenant, user: User,
    ) -> None:
        """GIVEN 2 tokens activos y 1 revocado WHEN count_active_for_user
        THEN retorna 2."""
        repo = _make_repo(db_session, tenant)
        for i in range(2):
            await repo.create(
                user_id=user.id,
                token_hash=f"active_{i}",
                expires_at=_future(),
            )
        revoked = await repo.create(
            user_id=user.id,
            token_hash="revoked_token",
            expires_at=_future(),
        )
        await repo.revoke(revoked.id)

        count = await repo.count_active_for_user(user_id=user.id)
        assert count == 2

    async def test_count_active_excludes_expired(
        self, db_session, tenant: Tenant, user: User,
    ) -> None:
        """GIVEN token expirado WHEN count_active_for_user THEN no lo
        cuenta."""
        repo = _make_repo(db_session, tenant)
        await repo.create(
            user_id=user.id,
            token_hash="expired_token",
            expires_at=_past(),
        )
        count = await repo.count_active_for_user(user_id=user.id)
        assert count == 0

    async def test_revoke_family_revokes_all_for_user(
        self, db_session, tenant: Tenant, user: User,
    ) -> None:
        """GIVEN 3 tokens activos del mismo usuario WHEN revoke_family
        THEN los 3 quedan revocados y retorna 3."""
        repo = _make_repo(db_session, tenant)
        for i in range(3):
            await repo.create(
                user_id=user.id,
                token_hash=f"family_{i}",
                expires_at=_future(),
            )

        target = await repo.get_by_token_hash("family_0")
        assert target is not None

        count = await repo.revoke_family(
            user_id=user.id, token_id=target.id,
        )
        assert count == 3

        for i in range(3):
            found = await repo.get_by_token_hash(f"family_{i}")
            assert found is not None
            assert found.revoked_at is not None

    async def test_revoke_family_respects_tenant_scope(
        self, db_session, tenant: Tenant, tenant_b: Tenant, user: User,
    ) -> None:
        """GIVEN tokens en T1 y T2 WHEN revoke_family en T1 THEN solo
        tokens de T1 son revocados."""
        repo_t1 = _make_repo(db_session, tenant)
        repo_t2 = _make_repo(db_session, tenant_b)
        user_b = await UserRepository(
            session=db_session, tenant_id=tenant_b.id,
        ).create(email="rt_family_b@example.com", password_hash=hash_password("p4ss"))

        for i in range(2):
            await repo_t1.create(
                user_id=user.id, token_hash=f"fam_t1_{i}", expires_at=_future(),
            )
        await repo_t2.create(
            user_id=user_b.id, token_hash="fam_t2", expires_at=_future(),
        )

        target = await repo_t1.get_by_token_hash("fam_t1_0")
        assert target is not None
        count = await repo_t1.revoke_family(
            user_id=user.id, token_id=target.id,
        )
        assert count == 2

        t2_token = await repo_t2.get_by_token_hash("fam_t2")
        assert t2_token is not None
        assert t2_token.revoked_at is None

    async def test_count_active_zero_for_no_tokens(
        self, db_session, tenant: Tenant,
    ) -> None:
        """GIVEN tenant sin tokens WHEN count_active_for_user THEN 0."""
        repo = _make_repo(db_session, tenant)
        count = await repo.count_active_for_user(user_id=uuid.uuid4())
        assert count == 0


class TestRefreshTokenRepositorySoftDelete:
    """Tests de soft delete en RefreshTokenRepository."""

    async def test_soft_delete_excludes_from_list_all(
        self, db_session, tenant: Tenant, user: User,
    ) -> None:
        """GIVEN token soft-deleteado WHEN list_all THEN no aparece."""
        repo = _make_repo(db_session, tenant)
        active = await repo.create(
            user_id=user.id, token_hash="keep_me", expires_at=_future(),
        )
        to_delete = await repo.create(
            user_id=user.id, token_hash="delete_me", expires_at=_future(),
        )

        await repo.soft_delete(to_delete)

        results = await repo.list_all()
        hashes = {t.token_hash for t in results}
        assert "keep_me" in hashes
        assert "delete_me" not in hashes

    async def test_soft_delete_excludes_from_get_by_hash(
        self, db_session, tenant: Tenant, user: User,
    ) -> None:
        """GIVEN token soft-deleteado WHEN get_by_token_hash THEN None."""
        repo = _make_repo(db_session, tenant)
        token = await repo.create(
            user_id=user.id, token_hash="gone_hash", expires_at=_future(),
        )
        await repo.soft_delete(token)

        found = await repo.get_by_token_hash("gone_hash")
        assert found is None
