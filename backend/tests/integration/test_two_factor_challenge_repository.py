"""Tests de integración para TwoFactorChallengeRepository contra PostgreSQL real.

Ejercita creación, lookup por hash, mark_used, cleanup_expired y verificación
de que el modelo NO tiene soft delete.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.core.security import hash_password
from app.models.tenant import Tenant
from app.models.two_factor_challenge import TwoFactorChallenge
from app.models.user import User
from app.repositories.two_factor_challenge_repository import (
    TwoFactorChallengeRepository,
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
    tenant = Tenant(id=tid, tenant_id=tid, nombre="TFAChallengeRepoTest")
    db_session.add(tenant)
    await db_session.flush()
    return tenant


@pytest_asyncio.fixture
async def user(db_session, tenant: Tenant) -> User:
    repo = UserRepository(session=db_session, tenant_id=tenant.id)
    return await repo.create(
        email="tfa_user@example.com",
        password_hash=hash_password("p4ss"),
    )


def _make_repo(db_session, tenant: Tenant) -> TwoFactorChallengeRepository:
    return TwoFactorChallengeRepository(session=db_session, tenant_id=tenant.id)


def _future(seconds: int = 300) -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=seconds)


def _past(seconds: int = 60) -> datetime:
    return datetime.now(timezone.utc) - timedelta(seconds=seconds)


class TestTwoFactorChallengeRepositoryCreateAndRead:
    """Tests de creación y lookup."""

    async def test_create_and_get_by_hash(
        self, db_session, tenant: Tenant, user: User,
    ) -> None:
        """GIVEN challenge creado WHEN get_by_token_hash THEN lo retorna."""
        repo = _make_repo(db_session, tenant)
        expires = _future()

        created = await repo.create(
            user_id=user.id,
            token_hash="tfc_hash_001",
            expires_at=expires,
        )

        assert created.user_id == user.id
        assert created.token_hash == "tfc_hash_001"
        assert created.expires_at == expires
        assert created.used_at is None
        assert created.tenant_id == tenant.id

        found = await repo.get_by_token_hash("tfc_hash_001")
        assert found is not None
        assert found.id == created.id

    async def test_get_by_hash_nonexistent_returns_none(
        self, db_session, tenant: Tenant,
    ) -> None:
        """GIVEN hash inexistente WHEN get_by_token_hash THEN None."""
        repo = _make_repo(db_session, tenant)
        found = await repo.get_by_token_hash("no_such_challenge")
        assert found is None


class TestTwoFactorChallengeRepositoryUsage:
    """Tests de mark_used y cleanup_expired."""

    async def test_mark_used(
        self, db_session, tenant: Tenant, user: User,
    ) -> None:
        """GIVEN challenge activo WHEN mark_used THEN used_at no es None."""
        repo = _make_repo(db_session, tenant)
        await repo.create(
            user_id=user.id,
            token_hash="use_challenge",
            expires_at=_future(),
        )
        challenge = await repo.get_by_token_hash("use_challenge")
        assert challenge is not None

        await repo.mark_used(challenge.id)

        found = await repo.get_by_token_hash("use_challenge")
        assert found is not None
        assert found.used_at is not None

    async def test_cleanup_expired_marks_expired_challenges(
        self, db_session, tenant: Tenant, user: User,
    ) -> None:
        """GIVEN challenge expirado WHEN cleanup_expired THEN se marca como
        usado y retorna 1."""
        repo = _make_repo(db_session, tenant)
        await repo.create(
            user_id=user.id,
            token_hash="old_expired",
            expires_at=_past(seconds=3600),
        )

        count = await repo.cleanup_expired()
        assert count == 1

        found = await repo.get_by_token_hash("old_expired")
        assert found is not None
        assert found.used_at is not None

    async def test_cleanup_does_not_touch_active_challenges(
        self, db_session, tenant: Tenant, user: User,
    ) -> None:
        """GIVEN challenge no expirado WHEN cleanup_expired THEN no se
        marca y retorna 0."""
        repo = _make_repo(db_session, tenant)
        await repo.create(
            user_id=user.id,
            token_hash="still_valid",
            expires_at=_future(),
        )

        count = await repo.cleanup_expired()
        assert count == 0

        found = await repo.get_by_token_hash("still_valid")
        assert found is not None
        assert found.used_at is None

    async def test_cleanup_does_not_affect_already_used(
        self, db_session, tenant: Tenant, user: User,
    ) -> None:
        """GIVEN challenge usado y expirado WHEN cleanup_expired THEN no lo
        cuenta (ya estaba marcado)."""
        repo = _make_repo(db_session, tenant)
        await repo.create(
            user_id=user.id,
            token_hash="already_used",
            expires_at=_past(),
        )
        challenge = await repo.get_by_token_hash("already_used")
        assert challenge is not None
        await repo.mark_used(challenge.id)

        count = await repo.cleanup_expired()
        assert count == 0

    async def test_cleanup_expired_mixed_scenario(
        self, db_session, tenant: Tenant, user: User,
    ) -> None:
        """GIVEN 2 expirados + 1 activo WHEN cleanup_expired THEN solo
        limpia los expirados."""
        repo = _make_repo(db_session, tenant)
        for i in range(2):
            await repo.create(
                user_id=user.id,
                token_hash=f"expired_{i}",
                expires_at=_past(),
            )
        await repo.create(
            user_id=user.id,
            token_hash="fresh",
            expires_at=_future(),
        )

        count = await repo.cleanup_expired()
        assert count == 2

        for i in range(2):
            found = await repo.get_by_token_hash(f"expired_{i}")
            assert found is not None
            assert found.used_at is not None

        fresh = await repo.get_by_token_hash("fresh")
        assert fresh is not None
        assert fresh.used_at is None


class TestTwoFactorChallengeRepositoryNoSoftDelete:
    """Verifica que TwoFactorChallenge NO tiene soft delete (es efímero)."""

    async def test_model_has_no_deleted_at(
        self,
    ) -> None:
        """GIVEN modelo TwoFactorChallenge THEN no tiene deleted_at."""
        assert not hasattr(TwoFactorChallenge, "deleted_at")

    async def test_list_all_includes_all_records(
        self, db_session, tenant: Tenant, user: User,
    ) -> None:
        """GIVEN challenges creados WHEN list_all THEN todos aparecen."""
        repo = _make_repo(db_session, tenant)
        for i in range(3):
            await repo.create(
                user_id=user.id,
                token_hash=f"tfc_list_{i}",
                expires_at=_future(),
            )

        results = await repo.list_all()
        assert len(results) == 3
