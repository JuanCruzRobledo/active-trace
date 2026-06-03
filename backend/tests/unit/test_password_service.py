"""Tests para PasswordService — solicitud y confirmación de reseteo."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.core.security import SecurityError, TokenExpiredError, hash_password
from app.models.password_reset_token import PasswordResetToken
from app.services.password_service import PasswordService


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


def _stored_reset_token(**kwargs) -> MagicMock:
    t = MagicMock(spec=PasswordResetToken)
    t.id = kwargs.get("id", uuid4())
    t.user_id = kwargs.get("user_id", uuid4())
    t.is_used.return_value = kwargs.get("used", False)
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
def user_repo():
    return AsyncMock()


@pytest.fixture
def reset_token_repo():
    return AsyncMock()


@pytest.fixture
def refresh_token_repo():
    return AsyncMock()


@pytest.fixture
def mailer():
    return MagicMock()


@pytest.fixture
def service(
    user_repo,
    reset_token_repo,
    refresh_token_repo,
    mailer,
    settings,
    tenant_id,
):
    return PasswordService(
        user_repo=user_repo,
        reset_token_repo=reset_token_repo,
        refresh_token_repo=refresh_token_repo,
        mailer=mailer,
        settings=settings,
        tenant_id=tenant_id,
    )


@pytest.fixture
def user():
    from app.models.user import User

    u = MagicMock(spec=User)
    u.id = uuid4()
    u.tenant_id = uuid4()
    u.email = "test@test.com"
    u.password_hash = hash_password("MiPassword2026!")
    u.is_active = True
    return u


# ===========================================================================
# request_reset
# ===========================================================================


class TestRequestReset:
    """``request_reset`` solicita un token de reset."""

    async def test_with_existing_email_creates_token_and_sends_mail(
        self, service, user, user_repo, reset_token_repo, mailer
    ):
        user_repo.get_by_email.return_value = user

        await service.request_reset(user.email)

        reset_token_repo.invalidate_all_pending_for_user.assert_awaited_once_with(
            user.id
        )
        reset_token_repo.create.assert_awaited_once()
        mailer.send_reset_link.assert_called_once()
        call = mailer.send_reset_link.call_args
        assert call is not None
        assert call.kwargs["to_email"] == user.email
        assert "reset?token=" in call.kwargs["link"]

    async def test_with_nonexistent_email_is_noop(
        self, service, user_repo, reset_token_repo, mailer
    ):
        user_repo.get_by_email.return_value = None

        await service.request_reset("nonexistent@test.com")

        reset_token_repo.invalidate_all_pending_for_user.assert_not_called()
        reset_token_repo.create.assert_not_called()
        mailer.send_reset_link.assert_not_called()

    async def test_invalidates_previous_tokens(
        self, service, user, user_repo, reset_token_repo
    ):
        user_repo.get_by_email.return_value = user

        await service.request_reset(user.email)

        reset_token_repo.invalidate_all_pending_for_user.assert_awaited_once_with(
            user.id
        )


# ===========================================================================
# confirm_reset
# ===========================================================================


class TestConfirmReset:
    """``confirm_reset`` valida el token y actualiza el password."""

    async def test_with_valid_token_updates_password(
        self, service, user, user_repo, reset_token_repo, refresh_token_repo
    ):
        stored = _stored_reset_token(used=False, expired=False, user_id=user.id)
        reset_token_repo.get_by_token_hash.return_value = stored

        new_password = "NuevoPassword2026!"
        await service.confirm_reset("valid-token", new_password)

        user_repo.update_password.assert_awaited_once()
        call = user_repo.update_password.await_args
        assert call is not None
        assert call.kwargs["user_id"] == user.id
        assert call.kwargs["new_hash"].startswith("$argon2id$")

    async def test_with_valid_token_marks_token_used_and_revokes_sessions(
        self, service, user, reset_token_repo, refresh_token_repo
    ):
        stored = _stored_reset_token(used=False, expired=False, user_id=user.id)
        reset_token_repo.get_by_token_hash.return_value = stored

        await service.confirm_reset("valid-token", "NuevoPassword2026!")

        reset_token_repo.mark_used.assert_awaited_once_with(stored.id)
        reset_token_repo.invalidate_all_pending_for_user.assert_awaited_once_with(
            stored.user_id
        )
        refresh_token_repo.revoke_all_for_user.assert_awaited_once_with(
            stored.user_id
        )

    async def test_with_nonexistent_token_raises_security_error(
        self, service, reset_token_repo
    ):
        reset_token_repo.get_by_token_hash.return_value = None

        with pytest.raises(SecurityError, match="not found"):
            await service.confirm_reset("bad-token", "NuevoPassword2026!")

    async def test_with_used_token_raises_security_error(
        self, service, reset_token_repo
    ):
        stored = _stored_reset_token(used=True, expired=False)
        reset_token_repo.get_by_token_hash.return_value = stored

        with pytest.raises(SecurityError, match="already used"):
            await service.confirm_reset("used-token", "NuevoPassword2026!")

    async def test_with_expired_token_raises_token_expired(
        self, service, reset_token_repo
    ):
        stored = _stored_reset_token(used=False, expired=True)
        reset_token_repo.get_by_token_hash.return_value = stored

        with pytest.raises(TokenExpiredError, match="expired"):
            await service.confirm_reset("expired-token", "NuevoPassword2026!")


# ===========================================================================
# Triangulación
# ===========================================================================


class TestPasswordServiceTriangulate:
    """Sanity checks cruzados."""

    async def test_confirm_reset_produces_different_hash(
        self, service, user, user_repo, reset_token_repo
    ):
        stored = _stored_reset_token(used=False, expired=False, user_id=user.id)
        reset_token_repo.get_by_token_hash.return_value = stored

        await service.confirm_reset("valid-token", "NuevoPassword2026!")

        user_repo.update_password.assert_awaited_once()
        call = user_repo.update_password.await_args
        assert call is not None
        assert call.kwargs["new_hash"] != "NuevoPassword2026!"

    async def test_request_reset_uses_opaque_token(
        self, service, user, user_repo, reset_token_repo
    ):
        user_repo.get_by_email.return_value = user

        await service.request_reset(user.email)

        reset_token_repo.create.assert_awaited_once()
        call = reset_token_repo.create.await_args
        assert call is not None
        assert len(call.kwargs["token_hash"]) == 64
