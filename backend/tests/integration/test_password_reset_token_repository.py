"""Tests de integración para PasswordResetTokenRepository contra PostgreSQL real.

Ejercita creación, lookup por hash, mark_used, invalidate_all_pending_for_user,
detección de expirados y verificación de que el modelo NO tiene soft delete.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.core.security import hash_password
from app.models.password_reset_token import PasswordResetToken
from app.models.tenant import Tenant
from app.models.user import User
from app.repositories.password_reset_token_repository import (
    PasswordResetTokenRepository,
)
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
    tenant = Tenant(id=tid, tenant_id=tid, nombre="ResetTokenRepoTest")
    db_session.add(tenant)
    await db_session.flush()
    return tenant


@pytest_asyncio.fixture
async def tenant_b(db_session) -> Tenant:
    tid = uuid.uuid4()
    tenant = Tenant(id=tid, tenant_id=tid, nombre="ResetTokenRepoTestB")
    db_session.add(tenant)
    await db_session.flush()
    return tenant


@pytest_asyncio.fixture
async def user(db_session, tenant: Tenant) -> User:
    repo = UserRepository(session=db_session, tenant_id=tenant.id)
    return await repo.create(
        email="reset_user@example.com",
        password_hash=hash_password("p4ss"),
    )


def _make_repo(db_session, tenant: Tenant) -> PasswordResetTokenRepository:
    return PasswordResetTokenRepository(session=db_session, tenant_id=tenant.id)


def _future(seconds: int = 1800) -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=seconds)


def _past(seconds: int = 60) -> datetime:
    return datetime.now(timezone.utc) - timedelta(seconds=seconds)


class TestPasswordResetTokenRepositoryCreateAndRead:
    """Tests de creación y lookup."""

    async def test_create_and_get_by_hash(
        self, db_session, tenant: Tenant, user: User,
    ) -> None:
        """GIVEN token creado WHEN get_by_token_hash THEN lo retorna."""
        repo = _make_repo(db_session, tenant)
        expires = _future()

        created = await repo.create(
            user_id=user.id,
            token_hash="prt_hash_001",
            expires_at=expires,
        )

        assert created.user_id == user.id
        assert created.token_hash == "prt_hash_001"
        assert created.expires_at == expires
        assert created.used_at is None
        assert created.tenant_id == tenant.id

        found = await repo.get_by_token_hash("prt_hash_001")
        assert found is not None
        assert found.id == created.id

    async def test_get_by_hash_nonexistent_returns_none(
        self, db_session, tenant: Tenant,
    ) -> None:
        """GIVEN hash inexistente WHEN get_by_token_hash THEN None."""
        repo = _make_repo(db_session, tenant)
        found = await repo.get_by_token_hash("no_such_hash")
        assert found is None


class TestPasswordResetTokenRepositoryUsage:
    """Tests de mark_used e invalidate_all_pending."""

    async def test_mark_used(
        self, db_session, tenant: Tenant, user: User,
    ) -> None:
        """GIVEN token activo WHEN mark_used THEN used_at no es None."""
        repo = _make_repo(db_session, tenant)
        await repo.create(
            user_id=user.id,
            token_hash="use_me",
            expires_at=_future(),
        )
        token = await repo.get_by_token_hash("use_me")
        assert token is not None

        await repo.mark_used(token.id)

        found = await repo.get_by_token_hash("use_me")
        assert found is not None
        assert found.used_at is not None

    async def test_invalidate_all_pending_for_user(
        self, db_session, tenant: Tenant, user: User,
    ) -> None:
        """GIVEN 3 tokens pendientes WHEN invalidate_all_pending_for_user
        THEN los 3 quedan marcados como usados."""
        repo = _make_repo(db_session, tenant)
        for i in range(3):
            await repo.create(
                user_id=user.id,
                token_hash=f"pending_{i}",
                expires_at=_future(),
            )

        count = await repo.invalidate_all_pending_for_user(user_id=user.id)
        assert count == 3

        for i in range(3):
            found = await repo.get_by_token_hash(f"pending_{i}")
            assert found is not None
            assert found.used_at is not None

    async def test_invalidate_does_not_affect_other_tenants(
        self, db_session, tenant: Tenant, tenant_b: Tenant, user: User,
    ) -> None:
        """GIVEN tokens pendientes en T1 y T2 WHEN invalidate en T1 THEN
        tokens de T2 no se afectan."""
        repo_t1 = _make_repo(db_session, tenant)
        repo_t2 = _make_repo(db_session, tenant_b)
        user_b = await UserRepository(
            session=db_session, tenant_id=tenant_b.id,
        ).create(email="prt_other@example.com", password_hash=hash_password("p4ss"))

        await repo_t1.create(
            user_id=user.id, token_hash="t1_prt", expires_at=_future(),
        )
        await repo_t2.create(
            user_id=user_b.id, token_hash="t2_prt", expires_at=_future(),
        )

        await repo_t1.invalidate_all_pending_for_user(user_id=user.id)

        t2_token = await repo_t2.get_by_token_hash("t2_prt")
        assert t2_token is not None
        assert t2_token.used_at is None

    async def test_invalidate_returns_zero_when_none_pending(
        self, db_session, tenant: Tenant, user: User,
    ) -> None:
        """GIVEN usuario sin tokens pendientes WHEN
        invalidate_all_pending_for_user THEN retorna 0."""
        repo = _make_repo(db_session, tenant)
        count = await repo.invalidate_all_pending_for_user(user_id=user.id)
        assert count == 0


class TestPasswordResetTokenRepositoryExpiration:
    """Tests de detección de expiración."""

    async def test_expired_token_detectable(
        self, db_session, tenant: Tenant, user: User,
    ) -> None:
        """GIVEN token con expires_at en pasado WHEN is_expired THEN True."""
        repo = _make_repo(db_session, tenant)
        token = await repo.create(
            user_id=user.id,
            token_hash="expired_prt",
            expires_at=_past(),
        )
        assert token.is_expired() is True

    async def test_active_token_not_expired(
        self, db_session, tenant: Tenant, user: User,
    ) -> None:
        """GIVEN token con expires_at en futuro WHEN is_expired THEN False."""
        repo = _make_repo(db_session, tenant)
        token = await repo.create(
            user_id=user.id,
            token_hash="active_prt",
            expires_at=_future(),
        )
        assert token.is_expired() is False


class TestPasswordResetTokenRepositoryNoSoftDelete:
    """Verifica que PasswordResetToken NO tiene soft delete (es efímero)."""

    async def test_model_has_no_deleted_at(
        self,
    ) -> None:
        """GIVEN modelo PasswordResetToken THEN no tiene atributo
        deleted_at."""
        assert not hasattr(PasswordResetToken, "deleted_at")

    async def test_list_all_includes_all_records(
        self, db_session, tenant: Tenant, user: User,
    ) -> None:
        """GIVEN tokens creados WHEN list_all THEN todos aparecen (no hay
        filtro de soft delete)."""
        repo = _make_repo(db_session, tenant)
        for i in range(3):
            await repo.create(
                user_id=user.id,
                token_hash=f"list_prt_{i}",
                expires_at=_future(),
            )

        results = await repo.list_all()
        assert len(results) == 3
