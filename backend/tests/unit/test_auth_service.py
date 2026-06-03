"""Tests para AuthService — orquestador de autenticación."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.core.security import hash_password
from app.schemas.auth import (
    TokenPair,
    TwoFactorChallengeResponse,
    TwoFactorEnrollResponse,
    UserMeResponse,
)
from app.services.auth_service import (
    AuthService,
    LoginFailedError,
    SecurityError,
    TwoFactorFailedError,
)


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


def _fake_token_pair() -> TokenPair:
    return TokenPair(
        access_token="eyJ.eyJ.eyJ",
        refresh_token="fake-opaque-token-xxxxxxxxxxxxxxxxxxxx",
        token_type="bearer",
        expires_in=900,
    )


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
def refresh_token_repo():
    return AsyncMock()


@pytest.fixture
def two_factor_repo():
    return AsyncMock()


@pytest.fixture
def password_reset_repo():
    return AsyncMock()


@pytest.fixture
def token_service():
    mock = AsyncMock()
    mock.issue_token_pair.return_value = _fake_token_pair()
    mock.rotate_refresh.return_value = _fake_token_pair()
    return mock


@pytest.fixture
def totp_service():
    return AsyncMock()


@pytest.fixture
def password_service():
    return AsyncMock()


@pytest.fixture
def mailer():
    return MagicMock()


@pytest.fixture
def user_rol_repo():
    mock = AsyncMock()
    mock.get_role_codigos_for_user.return_value = []
    return mock


@pytest.fixture
def service(
    user_repo,
    refresh_token_repo,
    two_factor_repo,
    password_reset_repo,
    token_service,
    totp_service,
    password_service,
    user_rol_repo,
    mailer,
    settings,
    tenant_id,
):
    return AuthService(
        user_repo=user_repo,
        refresh_token_repo=refresh_token_repo,
        two_factor_repo=two_factor_repo,
        password_reset_repo=password_reset_repo,
        token_service=token_service,
        totp_service=totp_service,
        password_service=password_service,
        user_rol_repo=user_rol_repo,
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
    u.email = "alice@test.com"
    u.password_hash = hash_password("MiPassword2026!")
    u.is_active = True
    u.totp_secret = None
    u.totp_enabled = False
    return u


# ===========================================================================
# login
# ===========================================================================


class TestLogin:
    """``login`` autentica por email+password con gate 2FA."""

    async def test_valid_credentials_without_2fa_returns_token_pair(
        self, service, user, user_repo
    ):
        user_repo.get_by_email.return_value = user

        result = await service.login(email=user.email, password="MiPassword2026!")

        assert isinstance(result, TokenPair)
        assert result.access_token
        assert result.refresh_token

    async def test_nonexistent_email_raises_login_failed(
        self, service, user_repo
    ):
        user_repo.get_by_email.return_value = None

        with pytest.raises(LoginFailedError, match="Invalid email or password"):
            await service.login(email="nobody@test.com", password="x")

    async def test_wrong_password_raises_login_failed(
        self, service, user, user_repo
    ):
        user_repo.get_by_email.return_value = user

        with pytest.raises(LoginFailedError, match="Invalid email or password"):
            await service.login(
                email=user.email, password="WrongPassword2026!"
            )

    async def test_inactive_user_raises_login_failed(
        self, service, user, user_repo
    ):
        user.is_active = False
        user_repo.get_by_email.return_value = user

        with pytest.raises(LoginFailedError, match="inactive|Account is inactive"):
            await service.login(
                email=user.email, password="MiPassword2026!"
            )

    async def test_with_2fa_active_returns_challenge_response(
        self, service, user, user_repo, two_factor_repo
    ):
        user.totp_enabled = True
        user_repo.get_by_email.return_value = user

        result = await service.login(email=user.email, password="MiPassword2026!")

        assert isinstance(result, TwoFactorChallengeResponse)
        assert result.twofa_required is True
        assert result.challenge_token
        two_factor_repo.create.assert_awaited_once()


# ===========================================================================
# verify_2fa
# ===========================================================================


class TestVerify2FA:
    """``verify_2fa`` completa el gate 2FA y emite TokenPair."""

    async def test_valid_challenge_and_code_returns_token_pair(
        self, service, user_repo, two_factor_repo, totp_service, token_service
    ):
        user_id = uuid4()
        challenge = MagicMock()
        challenge.is_used.return_value = False
        challenge.is_expired.return_value = False
        challenge.id = uuid4()
        challenge.user_id = user_id

        two_factor_repo.get_by_token_hash.return_value = challenge
        totp_service.verify.return_value = True
        user_repo.get_by_id.return_value = MagicMock(id=user_id)

        result = await service.verify_2fa(
            challenge_token="valid-challenge", code="123456"
        )

        assert isinstance(result, TokenPair)
        two_factor_repo.mark_used.assert_awaited_once_with(challenge.id)
        token_service.issue_token_pair.assert_awaited_once()

    async def test_invalid_challenge_raises_security_error(
        self, service, two_factor_repo
    ):
        two_factor_repo.get_by_token_hash.return_value = None

        with pytest.raises(SecurityError, match="not found"):
            await service.verify_2fa(
                challenge_token="bad", code="123456"
            )

    async def test_used_challenge_raises_security_error(
        self, service, two_factor_repo
    ):
        challenge = MagicMock()
        challenge.is_used.return_value = True
        two_factor_repo.get_by_token_hash.return_value = challenge

        with pytest.raises(SecurityError, match="already used"):
            await service.verify_2fa(
                challenge_token="used", code="123456"
            )

    async def test_wrong_totp_code_raises_two_factor_failed(
        self, service, two_factor_repo, totp_service
    ):
        challenge = MagicMock()
        challenge.is_used.return_value = False
        challenge.is_expired.return_value = False
        challenge.user_id = uuid4()

        two_factor_repo.get_by_token_hash.return_value = challenge
        totp_service.verify.return_value = False

        with pytest.raises(TwoFactorFailedError, match="Invalid TOTP code"):
            await service.verify_2fa(
                challenge_token="valid", code="000000"
            )


# ===========================================================================
# refresh
# ===========================================================================


class TestRefresh:
    """``refresh`` rota el refresh token."""

    async def test_delegates_to_token_service(
        self, service, token_service
    ):
        result = await service.refresh("some-refresh-token")

        assert isinstance(result, TokenPair)
        token_service.rotate_refresh.assert_awaited_once_with(
            refresh_token_str="some-refresh-token",
            user_agent=None,
            ip="unknown",
            roles=[],
        )


# ===========================================================================
# logout
# ===========================================================================


class TestLogout:
    """``logout`` revoca el refresh token del usuario."""

    async def test_revokes_token_for_current_user(
        self, service, refresh_token_repo
    ):
        user_id = uuid4()
        stored = MagicMock()
        stored.user_id = user_id
        stored.is_revoked.return_value = False
        stored.id = uuid4()
        refresh_token_repo.get_by_token_hash.return_value = stored

        await service.logout(
            refresh_token_str="some-token", current_user_id=user_id
        )

        refresh_token_repo.revoke.assert_awaited_once_with(stored.id)

    async def test_does_not_revoke_token_of_another_user(
        self, service, refresh_token_repo
    ):
        stored = MagicMock()
        stored.user_id = uuid4()  # different user
        stored.is_revoked.return_value = False
        stored.id = uuid4()
        refresh_token_repo.get_by_token_hash.return_value = stored

        await service.logout(
            refresh_token_str="some-token",
            current_user_id=uuid4(),  # another user
        )

        refresh_token_repo.revoke.assert_not_called()

    async def test_does_not_revoke_already_revoked_token(
        self, service, refresh_token_repo
    ):
        user_id = uuid4()
        stored = MagicMock()
        stored.user_id = user_id
        stored.is_revoked.return_value = True
        stored.id = uuid4()
        refresh_token_repo.get_by_token_hash.return_value = stored

        await service.logout(
            refresh_token_str="some-token", current_user_id=user_id
        )

        refresh_token_repo.revoke.assert_not_called()


# ===========================================================================
# forgot / reset (delegados)
# ===========================================================================


class TestForgot:
    """``forgot`` delega a PasswordService."""

    async def test_delegates_to_password_service(
        self, service, password_service
    ):
        email = "alice@test.com"

        await service.forgot(email)

        password_service.request_reset.assert_awaited_once_with(email)


class TestReset:
    """``reset`` delega a PasswordService."""

    async def test_delegates_to_password_service(
        self, service, password_service
    ):
        await service.reset(
            token="reset-token", new_password="NuevoPassword2026!"
        )

        password_service.confirm_reset.assert_awaited_once_with(
            "reset-token", "NuevoPassword2026!"
        )


# ===========================================================================
# enroll_2fa / confirm_2fa (delegados)
# ===========================================================================


class TestEnroll2FA:
    """``enroll_2fa`` delega a TOTPService."""

    async def test_delegates_to_totp_service(
        self, service, totp_service
    ):
        user_id = uuid4()
        email = "alice@test.com"
        totp_service.enroll.return_value = TwoFactorEnrollResponse(
            secret="JBSWY3DPEHPK3PXP",
            otpauth_uri="otpauth://totp/activia-trace:alice%40test.com?secret=JBSWY3DPEHPK3PXP&issuer=activia-trace",
            qr_png_base64="iVBORw0KGgo=",
        )

        result = await service.enroll_2fa(user_id=user_id, email=email)

        totp_service.enroll.assert_awaited_once_with(
            user_id, email
        )
        assert isinstance(result, TwoFactorEnrollResponse)


class TestConfirm2FA:
    """``confirm_2fa`` delega a TOTPService."""

    async def test_delegates_to_totp_service(
        self, service, totp_service
    ):
        user_id = uuid4()
        totp_service.confirm.return_value = True

        result = await service.confirm_2fa(user_id=user_id, code="123456")

        totp_service.confirm.assert_awaited_once_with(
            user_id, "123456"
        )
        assert result is True

    async def test_returns_false_when_totp_fails(
        self, service, totp_service
    ):
        totp_service.confirm.return_value = False

        result = await service.confirm_2fa(
            user_id=uuid4(), code="000000"
        )

        assert result is False


# ===========================================================================
# get_me
# ===========================================================================


class TestGetMe:
    """``get_me`` retorna perfil del usuario autenticado."""

    async def test_returns_user_me_response(
        self, service, user, user_repo
    ):
        user_repo.get_by_id.return_value = user

        result = await service.get_me(user_id=user.id)

        assert isinstance(result, UserMeResponse)
        assert result.id == str(user.id)
        assert result.email == user.email
        assert result.is_active == user.is_active
        assert result.totp_enabled == user.totp_enabled

    async def test_returns_none_for_nonexistent_user(
        self, service, user_repo
    ):
        user_repo.get_by_id.return_value = None

        result = await service.get_me(user_id=uuid4())

        assert result is None


# ===========================================================================
# Triangulación
# ===========================================================================


class TestAuthTriangulate:
    """Sanity checks cruzados."""

    async def test_login_failed_emits_audit_log(
        self, service, user_repo, caplog, user
    ):
        caplog.set_level(logging.INFO, logger="audit")
        user_repo.get_by_email.return_value = None

        with pytest.raises(LoginFailedError):
            await service.login(
                email="unknown@test.com", password="whatever"
            )

        audit_records = [
            r for r in caplog.records if r.name == "audit"
        ]
        assert len(audit_records) >= 1
        code = audit_records[0].extra["audit.code"]
        assert code == "LOGIN_FAIL"

    async def test_login_success_without_2fa_does_not_create_challenge(
        self, service, user, user_repo, two_factor_repo
    ):
        user_repo.get_by_email.return_value = user

        await service.login(email=user.email, password="MiPassword2026!")

        two_factor_repo.create.assert_not_called()

    async def test_verify_2fa_does_not_emit_refresh_without_challenge_used(
        self, service, two_factor_repo
    ):
        two_factor_repo.get_by_token_hash.return_value = None

        with pytest.raises(SecurityError):
            await service.verify_2fa(
                challenge_token="ghost", code="123456"
            )

        two_factor_repo.mark_used.assert_not_called()
