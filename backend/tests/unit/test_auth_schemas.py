"""Tests para los DTOs de autenticación (Pydantic v2).

Cubren:
- ``extra='forbid'`` rechaza campos no declarados (regla dura #5).
- ``StrongPassword``: ≥12 chars, 1 upper, 1 lower, 1 digit.
- ``EmailStr`` valida formato de email.
- ``TOTPConfirmRequest.code`` y ``TOTPVerifyRequest.code`` aceptan solo 6 dígitos.
- ``TokenPair`` shape consistente.
- Schemas de respuesta tienen los campos exactos del spec.
"""

from __future__ import annotations

import secrets

import pytest
from pydantic import ValidationError


def _opaque(n_chars: int = 43) -> str:
    """Genera un token opaco del largo esperado (≥32 chars)."""
    return secrets.token_urlsafe(n_chars)[:n_chars]


# ===========================================================================
# extra='forbid' (regla dura #5)
# ===========================================================================


class TestExtraForbid:
    """Todo schema de auth rechaza campos no declarados."""

    def test_login_request_rejects_unknown_field(self):
        from app.schemas.auth import LoginRequest

        with pytest.raises(ValidationError) as exc:
            LoginRequest(email="a@b.com", password="x", admin=True)  # type: ignore[call-arg]
        assert "admin" in str(exc.value).lower()

    def test_refresh_request_rejects_unknown_field(self):
        from app.schemas.auth import RefreshRequest

        with pytest.raises(ValidationError) as exc:
            RefreshRequest(refresh_token=_opaque(), foo="bar")  # type: ignore[call-arg]
        assert "foo" in str(exc.value).lower()

    def test_logout_request_rejects_unknown_field(self):
        from app.schemas.auth import LogoutRequest

        with pytest.raises(ValidationError) as exc:
            LogoutRequest(refresh_token=_opaque(), leak=True)  # type: ignore[call-arg]
        assert "leak" in str(exc.value).lower()

    def test_totp_confirm_request_rejects_unknown_field(self):
        from app.schemas.auth import TOTPConfirmRequest

        with pytest.raises(ValidationError) as exc:
            TOTPConfirmRequest(code="123456", bypass=True)  # type: ignore[call-arg]
        assert "bypass" in str(exc.value).lower()

    def test_totp_verify_request_rejects_unknown_field(self):
        from app.schemas.auth import TOTPVerifyRequest

        with pytest.raises(ValidationError) as exc:
            TOTPVerifyRequest(
                challenge_token="abc", code="123456", admin_override=True
            )  # type: ignore[call-arg]
        assert "admin_override" in str(exc.value).lower()

    def test_forgot_request_rejects_unknown_field(self):
        from app.schemas.auth import ForgotRequest

        with pytest.raises(ValidationError) as exc:
            ForgotRequest(email="a@b.com", spam=True)  # type: ignore[call-arg]
        assert "spam" in str(exc.value).lower()

    def test_reset_request_rejects_unknown_field(self):
        from app.schemas.auth import ResetRequest

        with pytest.raises(ValidationError) as exc:
            ResetRequest(token="t", new_password="MiPassword2026!", extra=1)  # type: ignore[call-arg]
        assert "extra" in str(exc.value).lower()


# ===========================================================================
# LoginRequest
# ===========================================================================


class TestLoginRequest:
    """``LoginRequest`` requiere email válido + password no vacío."""

    def test_valid_email_and_password(self):
        from app.schemas.auth import LoginRequest

        req = LoginRequest(email="alice@example.com", password="whatever")
        assert req.email == "alice@example.com"
        assert req.password == "whatever"

    def test_rejects_invalid_email_format(self):
        from app.schemas.auth import LoginRequest

        with pytest.raises(ValidationError) as exc:
            LoginRequest(email="not-an-email", password="x")
        assert "email" in str(exc.value).lower()

    def test_rejects_empty_password(self):
        from app.schemas.auth import LoginRequest

        with pytest.raises(ValidationError) as exc:
            LoginRequest(email="a@b.com", password="")
        assert "password" in str(exc.value).lower()

    def test_rejects_missing_email(self):
        from app.schemas.auth import LoginRequest

        with pytest.raises(ValidationError):
            LoginRequest(password="x")  # type: ignore[call-arg]

    def test_rejects_missing_password(self):
        from app.schemas.auth import LoginRequest

        with pytest.raises(ValidationError):
            LoginRequest(email="a@b.com")  # type: ignore[call-arg]


# ===========================================================================
# TokenPair
# ===========================================================================


class TestTokenPair:
    """``TokenPair`` retorna access + refresh + tipo + expires_in."""

    def test_token_pair_has_required_fields(self):
        from app.schemas.auth import TokenPair

        pair = TokenPair(
            access_token="access.x.y",
            refresh_token="opaque",
            token_type="bearer",
            expires_in=900,
        )
        assert pair.access_token == "access.x.y"
        assert pair.refresh_token == "opaque"
        assert pair.token_type == "bearer"
        assert pair.expires_in == 900

    def test_token_pair_rejects_extra_fields(self):
        """TokenPair también ``extra='forbid'`` (regla dura #5, sin excepciones)."""
        from app.schemas.auth import TokenPair

        with pytest.raises(ValidationError) as exc:
            TokenPair(
                access_token="a",
                refresh_token="r",
                token_type="bearer",
                expires_in=900,
                admin_token="x",  # type: ignore[call-arg]
            )
        assert "admin_token" in str(exc.value).lower()


# ===========================================================================
# UserMeResponse
# ===========================================================================


class TestUserMeResponse:
    """``UserMeResponse`` retorna la identidad del usuario logueado."""

    def test_user_me_response_includes_key_fields(self):
        from app.schemas.auth import UserMeResponse

        me = UserMeResponse(
            id="36241ae3-590c-46de-90e7-42fc6ed7aa3a",
            tenant_id="36241ae3-590c-46de-90e7-42fc6ed7aa3a",
            email="alice@example.com",
            is_active=True,
            totp_enabled=False,
            roles=[],
        )
        assert me.email == "alice@example.com"
        assert me.is_active is True
        assert me.totp_enabled is False
        assert me.roles == []

    def test_user_me_response_rejects_extra_fields(self):
        from app.schemas.auth import UserMeResponse

        with pytest.raises(ValidationError) as exc:
            UserMeResponse(
                id="36241ae3-590c-46de-90e7-42fc6ed7aa3a",
                tenant_id="36241ae3-590c-46de-90e7-42fc6ed7aa3a",
                email="a@b.com",
                is_active=True,
                totp_enabled=False,
                roles=[],
                password_hash="leaked",  # type: ignore[call-arg]
            )
        assert "password_hash" in str(exc.value).lower()


# ===========================================================================
# TwoFactorChallengeResponse
# ===========================================================================


class TestTwoFactorChallengeResponse:
    """``TwoFactorChallengeResponse`` es lo que ``/login`` devuelve cuando 2FA activo."""

    def test_challenge_response_shape(self):
        from app.schemas.auth import TwoFactorChallengeResponse

        resp = TwoFactorChallengeResponse(
            twofa_required=True, challenge_token=_opaque()
        )
        assert resp.twofa_required is True
        assert resp.challenge_token

    def test_challenge_response_rejects_extra_fields(self):
        from app.schemas.auth import TwoFactorChallengeResponse

        with pytest.raises(ValidationError) as exc:
            TwoFactorChallengeResponse(
                twofa_required=True,
                challenge_token="x",
                access_token="leak",  # type: ignore[call-arg]
            )
        assert "access_token" in str(exc.value).lower()


# ===========================================================================
# TwoFactorEnrollResponse
# ===========================================================================


class TestTwoFactorEnrollResponse:
    """``/2fa/enroll`` retorna secret, URI otpauth, QR en base64."""

    def test_enroll_response_shape(self):
        from app.schemas.auth import TwoFactorEnrollResponse

        resp = TwoFactorEnrollResponse(
            secret="JBSWY3DPEHPK3PXP",
            otpauth_uri="otpauth://totp/activia-trace:a@b.com?secret=...&issuer=activia-trace",
            qr_png_base64="iVBORw0KGgoAAAANSUhEUgAA...",
        )
        assert resp.secret == "JBSWY3DPEHPK3PXP"
        assert resp.otpauth_uri.startswith("otpauth://totp/")
        assert resp.qr_png_base64  # non-empty

    def test_enroll_response_rejects_extra_fields(self):
        from app.schemas.auth import TwoFactorEnrollResponse

        with pytest.raises(ValidationError) as exc:
            TwoFactorEnrollResponse(
                secret="x",
                otpauth_uri="u",
                qr_png_base64="q",
                backdoor_code="999999",  # type: ignore[call-arg]
            )
        assert "backdoor_code" in str(exc.value).lower()


# ===========================================================================
# TOTP code validation (6 digits)
# ===========================================================================


class TestTOTPCodeValidation:
    """TOTP codes: exactamente 6 dígitos."""

    @pytest.mark.parametrize("code", ["000000", "123456", "999999", "654321"])
    def test_totp_confirm_accepts_6_digits(self, code):
        from app.schemas.auth import TOTPConfirmRequest

        req = TOTPConfirmRequest(code=code)
        assert req.code == code

    @pytest.mark.parametrize(
        "code",
        [
            "12345",  # 5 digits
            "1234567",  # 7 digits
            "abcdef",  # letras
            "12 456",  # espacio
            "12345a",  # mezcla
            "",  # vacío
        ],
    )
    def test_totp_confirm_rejects_invalid_codes(self, code):
        from app.schemas.auth import TOTPConfirmRequest

        with pytest.raises(ValidationError):
            TOTPConfirmRequest(code=code)

    def test_totp_verify_request_validates_code(self):
        from app.schemas.auth import TOTPVerifyRequest

        req = TOTPVerifyRequest(challenge_token=_opaque(), code="123456")
        assert req.code == "123456"

    def test_totp_verify_request_rejects_short_code(self):
        from app.schemas.auth import TOTPVerifyRequest

        with pytest.raises(ValidationError):
            TOTPVerifyRequest(challenge_token=_opaque(), code="12345")

    def test_totp_verify_request_rejects_non_digit_code(self):
        from app.schemas.auth import TOTPVerifyRequest

        with pytest.raises(ValidationError):
            TOTPVerifyRequest(challenge_token=_opaque(), code="abcdef")


# ===========================================================================
# ForgotRequest
# ===========================================================================


class TestForgotRequest:
    """``/forgot`` recibe email."""

    def test_valid_email_accepted(self):
        from app.schemas.auth import ForgotRequest

        req = ForgotRequest(email="alice@example.com")
        assert req.email == "alice@example.com"

    def test_invalid_email_rejected(self):
        from app.schemas.auth import ForgotRequest

        with pytest.raises(ValidationError):
            ForgotRequest(email="not-an-email")


# ===========================================================================
# StrongPassword validator
# ===========================================================================


class TestStrongPassword:
    """``StrongPassword``: ≥12 chars + 1 upper + 1 lower + 1 digit."""

    def test_strong_password_accepted(self):
        """Password que cumple las 4 reglas es aceptado."""
        from app.schemas.auth import ResetRequest

        req = ResetRequest(token=_opaque(), new_password="MiPassword2026!")
        assert req.new_password == "MiPassword2026!"

    def test_password_too_short_rejected(self):
        """< 12 chars → 422."""
        from app.schemas.auth import ResetRequest

        with pytest.raises(ValidationError) as exc:
            ResetRequest(token=_opaque(), new_password="Abc1")
        msg = str(exc.value).lower()
        assert "12" in msg or "caracteres" in msg or "caract" in msg or "at least" in msg

    def test_password_without_uppercase_rejected(self):
        """Sin mayúscula → 422."""
        from app.schemas.auth import ResetRequest

        with pytest.raises(ValidationError):
            ResetRequest(token=_opaque(), new_password="mipassword2026!")

    def test_password_without_lowercase_rejected(self):
        """Sin minúscula → 422."""
        from app.schemas.auth import ResetRequest

        with pytest.raises(ValidationError):
            ResetRequest(token=_opaque(), new_password="MIPASSWORD2026!")

    def test_password_without_digit_rejected(self):
        """Sin dígito → 422."""
        from app.schemas.auth import ResetRequest

        with pytest.raises(ValidationError):
            ResetRequest(token=_opaque(), new_password="MiPasswordWithoutDigit!")

    def test_password_exactly_12_chars_with_all_rules_accepted(self):
        """12 chars exactos con las 4 reglas (límite)."""
        from app.schemas.auth import ResetRequest

        req = ResetRequest(token=_opaque(), new_password="Abcdefgh1!@#")
        assert req.new_password == "Abcdefgh1!@#"

    def test_password_13_chars_with_all_rules_accepted(self):
        """13 chars con las 4 reglas (más del mínimo)."""
        from app.schemas.auth import ResetRequest

        req = ResetRequest(token=_opaque(), new_password="Abcdefghij1!@")
        assert req.new_password == "Abcdefghij1!@"

    def test_strong_password_rejects_empty(self):
        """Password vacío → 422 (cumple todas las validaciones de length)."""
        from app.schemas.auth import ResetRequest

        with pytest.raises(ValidationError):
            ResetRequest(token=_opaque(), new_password="")


# ===========================================================================
# ResetRequest
# ===========================================================================


class TestResetRequest:
    """``/reset`` recibe token opaco + new_password (validada)."""

    def test_reset_request_valid_fields(self):
        from app.schemas.auth import ResetRequest

        req = ResetRequest(token=_opaque(), new_password="MiPassword2026!")
        assert req.token
        assert req.new_password == "MiPassword2026!"

    def test_reset_request_rejects_missing_token(self):
        from app.schemas.auth import ResetRequest

        with pytest.raises(ValidationError):
            ResetRequest(new_password="MiPassword2026!")  # type: ignore[call-arg]

    def test_reset_request_rejects_missing_password(self):
        from app.schemas.auth import ResetRequest

        with pytest.raises(ValidationError):
            ResetRequest(token=_opaque())  # type: ignore[call-arg]


# ===========================================================================
# PasswordResetRequest (alias de ResetRequest, presente por consistencia)
# ===========================================================================


class TestPasswordResetRequest:
    """``PasswordResetRequest`` existe para uso futuro (cambio de password autenticado)."""

    def test_password_reset_request_valid(self):
        from app.schemas.auth import PasswordResetRequest

        req = PasswordResetRequest(new_password="MiPassword2026!")
        assert req.new_password == "MiPassword2026!"

    def test_password_reset_request_rejects_weak_password(self):
        from app.schemas.auth import PasswordResetRequest

        with pytest.raises(ValidationError):
            PasswordResetRequest(new_password="weak")

    def test_password_reset_request_rejects_extra_fields(self):
        from app.schemas.auth import PasswordResetRequest

        with pytest.raises(ValidationError):
            PasswordResetRequest(
                new_password="MiPassword2026!",
                bypass=True,  # type: ignore[call-arg]
            )


# ===========================================================================
# RefreshRequest, LogoutRequest
# ===========================================================================


class TestRefreshRequest:
    def test_refresh_request_valid(self):
        from app.schemas.auth import RefreshRequest

        req = RefreshRequest(refresh_token=_opaque())
        assert req.refresh_token

    def test_refresh_request_requires_field(self):
        from app.schemas.auth import RefreshRequest

        with pytest.raises(ValidationError):
            RefreshRequest()  # type: ignore[call-arg]


class TestLogoutRequest:
    def test_logout_request_valid(self):
        from app.schemas.auth import LogoutRequest

        req = LogoutRequest(refresh_token=_opaque())
        assert req.refresh_token


# ===========================================================================
# Triangulación
# ===========================================================================


class TestSchemasTriangulate:
    """Sanity checks cruzados."""

    def test_all_request_schemas_have_extra_forbid(self):
        """Todos los schemas de auth son ``extra='forbid'`` (regla dura #5)."""
        from app.schemas import auth  # noqa: PLC0415

        request_schemas = [
            auth.LoginRequest,
            auth.RefreshRequest,
            auth.LogoutRequest,
            auth.TOTPConfirmRequest,
            auth.TOTPVerifyRequest,
            auth.ForgotRequest,
            auth.ResetRequest,
            auth.PasswordResetRequest,
        ]
        for schema in request_schemas:
            assert (
                schema.model_config.get("extra") == "forbid"
            ), f"{schema.__name__} SHOULD forbid extra fields"

    def test_all_response_schemas_have_extra_forbid(self):
        """Schemas de respuesta también ``extra='forbid'`` (defense in depth)."""
        from app.schemas import auth  # noqa: PLC0415

        response_schemas = [
            auth.TokenPair,
            auth.UserMeResponse,
            auth.TwoFactorChallengeResponse,
            auth.TwoFactorEnrollResponse,
        ]
        for schema in response_schemas:
            assert (
                schema.model_config.get("extra") == "forbid"
            ), f"{schema.__name__} SHOULD forbid extra fields"
