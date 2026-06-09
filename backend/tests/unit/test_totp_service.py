"""Tests para TOTPService — enrollment y verificación de 2FA TOTP."""

from __future__ import annotations

import base64
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pyotp
import pytest

from app.core.config import Settings
from app.schemas.auth import TwoFactorEnrollResponse
from app.services.totp_service import TOTPService


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
def service(settings, user_repo, tenant_id):
    return TOTPService(
        user_repo=user_repo,
        settings=settings,
        tenant_id=tenant_id,
    )


# ===========================================================================
# generate_secret
# ===========================================================================


class TestGenerateSecret:
    """``generate_secret`` produce un secreto TOTP válido."""

    def test_returns_base32_string(self, service):
        secret = service.generate_secret()

        assert isinstance(secret, str)
        assert len(secret) >= 16
        # base32 chars: A-Z, 2-7
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567" for c in secret)

    def test_generates_different_secrets(self, service):
        s1 = service.generate_secret()
        s2 = service.generate_secret()
        assert s1 != s2


# ===========================================================================
# build_otpauth_uri
# ===========================================================================


class TestBuildOtpauthUri:
    """``build_otpauth_uri`` construye URI estándar."""

    def test_contains_otpauth_totp_prefix(self, service):
        secret = service.generate_secret()
        uri = service.build_otpauth_uri(secret, "alice@test.com")

        assert uri.startswith("otpauth://totp/")
        assert "alice" in uri

    def test_uses_custom_issuer(self, service):
        secret = service.generate_secret()
        uri = service.build_otpauth_uri(
            secret, "alice@test.com", issuer="MiApp"
        )

        assert "issuer=MiApp" in uri or "MiApp" in uri

    def test_uses_default_issuer_from_settings(self, service, settings):
        secret = service.generate_secret()
        uri = service.build_otpauth_uri(secret, "alice@test.com")

        assert settings.TOTP_ISSUER in uri


# ===========================================================================
# generate_qr_png_base64
# ===========================================================================


class TestGenerateQR:
    """``generate_qr_png_base64`` produce un QR code PNG en base64."""

    def test_returns_valid_base64(self, service):
        secret = service.generate_secret()
        uri = service.build_otpauth_uri(secret, "alice@test.com")
        qr_b64 = service.generate_qr_png_base64(uri)

        assert isinstance(qr_b64, str)
        # Se puede decodificar como base64 válido
        decoded = base64.b64decode(qr_b64)
        # PNG header: \x89PNG
        assert decoded[:4] == b"\x89PNG"

    def test_different_uris_produce_different_qrs(self, service):
        secret = service.generate_secret()
        uri1 = service.build_otpauth_uri(secret, "a@test.com")
        uri2 = service.build_otpauth_uri(secret, "b@test.com")

        qr1 = service.generate_qr_png_base64(uri1)
        qr2 = service.generate_qr_png_base64(uri2)
        assert qr1 != qr2


# ===========================================================================
# enroll
# ===========================================================================


class TestEnroll:
    """``enroll`` inicia enrollment 2FA."""

    async def test_returns_enroll_response(
        self, service, user_repo, settings
    ):
        user_id = uuid4()
        email = "alice@test.com"

        result = await service.enroll(user_id=user_id, email=email)

        assert isinstance(result, TwoFactorEnrollResponse)
        assert result.secret
        assert len(result.secret) >= 16
        assert result.otpauth_uri.startswith("otpauth://totp/")
        assert result.qr_png_base64
        # QR es PNG válido
        decoded = base64.b64decode(result.qr_png_base64)
        assert decoded[:4] == b"\x89PNG"

    async def test_persists_secret_in_user_repo(self, service, user_repo):
        user_id = uuid4()
        email = "alice@test.com"

        await service.enroll(user_id=user_id, email=email)

        user_repo.enable_totp.assert_awaited_once()
        call = user_repo.enable_totp.await_args
        assert call is not None
        assert call.kwargs["user_id"] == user_id
        assert call.kwargs["encrypted_secret"] is not None

    async def test_otpauth_uri_includes_email(self, service, user_repo):
        user_id = uuid4()
        email = "alice@test.com"

        result = await service.enroll(user_id=user_id, email=email)

        assert "alice" in result.otpauth_uri


# ===========================================================================
# confirm
# ===========================================================================


class TestTOTPConfirm:
    """``confirm`` confirma enrollment con código TOTP."""

    async def test_with_valid_code_returns_true(self, service, user_repo):
        user_id = uuid4()
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)

        user = MagicMock()
        user.totp_secret = secret
        user_repo.get_by_id.return_value = user

        valid_code = totp.now()
        result = await service.confirm(user_id=user_id, code=valid_code)

        assert result is True
        user_repo.enable_totp.assert_awaited_once_with(
            user_id=user_id, encrypted_secret=secret
        )

    async def test_with_invalid_code_returns_false(self, service, user_repo):
        user_id = uuid4()
        secret = pyotp.random_base32()

        user = MagicMock()
        user.totp_secret = secret
        user_repo.get_by_id.return_value = user

        result = await service.confirm(user_id=user_id, code="000000")

        assert result is False
        user_repo.enable_totp.assert_not_called()

    async def test_with_user_without_secret_returns_false(
        self, service, user_repo
    ):
        user_id = uuid4()

        user = MagicMock()
        user.totp_secret = None
        user_repo.get_by_id.return_value = user

        result = await service.confirm(user_id=user_id, code="123456")

        assert result is False

    async def test_with_nonexistent_user_returns_false(
        self, service, user_repo
    ):
        user_repo.get_by_id.return_value = None

        result = await service.confirm(user_id=uuid4(), code="123456")

        assert result is False


# ===========================================================================
# verify
# ===========================================================================


class TestTOTPVerify:
    """``verify`` verifica código TOTP para login gate."""

    async def test_with_valid_code_returns_true(self, service, user_repo):
        user_id = uuid4()
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)

        user = MagicMock()
        user.totp_secret = secret
        user_repo.get_by_id.return_value = user

        valid_code = totp.now()
        result = await service.verify(user_id=user_id, code=valid_code)

        assert result is True

    async def test_with_invalid_code_returns_false(self, service, user_repo):
        user_id = uuid4()
        secret = pyotp.random_base32()

        user = MagicMock()
        user.totp_secret = secret
        user_repo.get_by_id.return_value = user

        result = await service.verify(user_id=user_id, code="000000")

        assert result is False

    async def test_with_user_without_secret_returns_false(
        self, service, user_repo
    ):
        user_id = uuid4()

        user = MagicMock()
        user.totp_secret = None
        user_repo.get_by_id.return_value = user

        result = await service.verify(user_id=user_id, code="123456")

        assert result is False


# ===========================================================================
# Triangulación
# ===========================================================================


class TestTOTPTriangulate:
    """Sanity checks cruzados."""

    async def test_qr_is_valid_png_base64(
        self, service, user_repo, settings
    ):
        user_id = uuid4()
        email = "alice@test.com"

        result = await service.enroll(user_id=user_id, email=email)

        decoded = base64.b64decode(result.qr_png_base64)
        assert decoded[:4] == b"\x89PNG"

    def test_enroll_uri_is_compatible_with_authenticator(self, service):
        """URI generada debería ser compatible con Google Authenticator."""
        secret = service.generate_secret()
        uri = service.build_otpauth_uri(
            secret, "alice@test.com", issuer="activia-trace"
        )

        assert "otpauth://totp/" in uri
        assert "secret=" in uri
        assert "issuer=" in uri
