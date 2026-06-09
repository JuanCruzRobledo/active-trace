"""Tests para TokenService — emisión y rotación de pares access+refresh."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.core.security import (
    SecurityError,
    TokenExpiredError,
    generate_opaque_token,
    hash_opaque_token,
)
from app.models.refresh_token import RefreshToken
from app.schemas.auth import TokenPair
from app.services.token_service import TokenService


# ── Helpers ───────────────────────────────────────────────────────────────


def _settings(**kwargs) -> Settings:
    defaults = dict(
        SECRET_KEY="a" * 64,
        ENCRYPTION_KEY="b" * 32,
        DATABASE_URL="placeholder",
        ACCESS_TOKEN_EXPIRE_MINUTES=15,
        REFRESH_TOKEN_EXPIRE_DAYS=7,
        PASSWORD_RESET_EXPIRE_MINUTES=30,
        TWO_FA_CHALLENGE_EXPIRE_MINUTES=5,
        TOTP_ISSUER="activia-trace",
        LOGIN_RATE_LIMIT="5/60s",
        MAILER_MODE="console",
        ENVIRONMENT="development",
        LOG_LEVEL="DEBUG",
    )
    defaults.update(kwargs)
    return Settings(**defaults)


def _stored_token(**kwargs) -> MagicMock:
    t = MagicMock(spec=RefreshToken)
    t.id = kwargs.get("id", uuid4())
    t.user_id = kwargs.get("user_id", uuid4())
    t.user_agent = kwargs.get("user_agent", None)
    t.created_ip = kwargs.get("created_ip", None)
    t.impersonated_by = kwargs.get("impersonated_by", None)
    t.is_revoked.return_value = kwargs.get("revoked", False)
    t.is_expired.return_value = kwargs.get("expired", False)
    return t


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def settings():
    return _settings()


@pytest.fixture
def tenant_id():
    return uuid4()


@pytest.fixture
def secret_key():
    return "s" * 64


@pytest.fixture
def token_repo():
    return AsyncMock()


@pytest.fixture
def user():
    from app.models.user import User

    u = MagicMock(spec=User)
    u.id = uuid4()
    u.tenant_id = uuid4()
    u.email = "test@test.com"
    u.password_hash = "hash"
    u.is_active = True
    return u


@pytest.fixture
def service(token_repo, settings, secret_key, tenant_id):
    return TokenService(
        token_repo=token_repo,
        settings=settings,
        secret_key=secret_key,
        tenant_id=tenant_id,
    )


# ===========================================================================
# issue_token_pair
# ===========================================================================


class TestIssueTokenPair:
    """``issue_token_pair`` emite un par access+refresh."""

    async def test_returns_token_pair(self, service, user):
        result = await service.issue_token_pair(user=user)

        assert isinstance(result, TokenPair)
        assert result.access_token
        assert len(result.access_token.split(".")) == 3
        assert result.refresh_token
        assert result.expires_in > 0

    async def test_calls_repo_create_once(self, service, user, token_repo):
        await service.issue_token_pair(user=user)

        token_repo.create.assert_awaited_once()
        call = token_repo.create.await_args
        assert call is not None
        assert call.kwargs["user_id"] == user.id
        assert len(call.kwargs["token_hash"]) == 64
        assert call.kwargs["expires_at"] is not None

    async def test_expires_in_matches_settings(self, service, user, settings):
        result = await service.issue_token_pair(user=user)

        assert result.expires_in == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    async def test_token_pair_has_all_fields(self, service, user):
        result = await service.issue_token_pair(user=user)

        assert result.access_token
        assert result.refresh_token
        assert result.token_type == "bearer"
        assert result.expires_in == 900


# ===========================================================================
# rotate_refresh
# ===========================================================================


class TestRotateRefresh:
    """``rotate_refresh`` valida, rota y emite nuevo par."""

    async def test_with_valid_token_returns_new_pair(
        self, service, token_repo
    ):
        stored = _stored_token(revoked=False, expired=False)
        token_repo.get_by_token_hash.return_value = stored

        refresh_plain = generate_opaque_token()
        result = await service.rotate_refresh(refresh_plain)

        assert isinstance(result, TokenPair)
        assert result.access_token
        assert result.refresh_token
        assert result.access_token != refresh_plain
        token_repo.revoke.assert_awaited_once_with(stored.id)

    async def test_with_nonexistent_token_raises_security_error(
        self, service, token_repo
    ):
        token_repo.get_by_token_hash.return_value = None

        with pytest.raises(SecurityError, match="not found"):
            await service.rotate_refresh("nonexistent-token")

    async def test_with_revoked_token_raises_reuse_detected(
        self, service, token_repo
    ):
        stored = _stored_token(revoked=True, expired=False)
        token_repo.get_by_token_hash.return_value = stored

        with pytest.raises(SecurityError, match="reuse"):
            await service.rotate_refresh("revoked-token")

        token_repo.revoke_family.assert_awaited_once()

    async def test_with_expired_token_raises_token_expired(
        self, service, token_repo
    ):
        stored = _stored_token(revoked=False, expired=True)
        token_repo.get_by_token_hash.return_value = stored

        with pytest.raises(TokenExpiredError, match="expired"):
            await service.rotate_refresh("expired-token")


# ===========================================================================
# Triangulación
# ===========================================================================


class TestTokenServiceTriangulate:
    """Sanity checks cruzados."""

    async def test_expires_in_equals_access_token_expire_minutes_times_60(
        self, service, user, settings
    ):
        result = await service.issue_token_pair(user=user)

        assert result.expires_in == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    async def test_rotate_refresh_uses_hash_opaque_token(
        self, service, token_repo
    ):
        stored = _stored_token(revoked=False, expired=False)
        token_repo.get_by_token_hash.return_value = stored

        refresh_plain = generate_opaque_token()
        expected_hash = hash_opaque_token(refresh_plain)
        await service.rotate_refresh(refresh_plain)

        token_repo.get_by_token_hash.assert_awaited_once_with(expected_hash)

    async def test_issue_token_pair_passes_user_agent_and_ip(
        self, service, user, token_repo
    ):
        await service.issue_token_pair(
            user=user, user_agent="Mozilla/5.0", created_ip="127.0.0.1"
        )

        token_repo.create.assert_awaited_once()
        call = token_repo.create.await_args
        assert call is not None
        assert call.kwargs["user_agent"] == "Mozilla/5.0"
        assert call.kwargs["created_ip"] == "127.0.0.1"
