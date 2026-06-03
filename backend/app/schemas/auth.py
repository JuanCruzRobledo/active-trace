"""Schemas Pydantic v2 (DTOs) del cambio C-03 auth-jwt-2fa.

Todos los schemas usan ``model_config = ConfigDict(extra='forbid')``
(REGLA DURA #5). Los requests rechazan campos no declarados para
prevenir mass-assignment; los responses también para detectar bugs
de serialización que filtren atributos sensibles (ej. ``password_hash``).

Convención:
- ``*Request`` → body de entrada del endpoint.
- ``*Response`` → body de salida.
- ``TokenPair`` → respuesta común a ``/login`` (sin 2FA), ``/2fa/verify`` y ``/refresh``.
- ``TwoFactorChallengeResponse`` → respuesta de ``/login`` cuando 2FA está activo
  (en lugar de ``TokenPair``).
"""

from __future__ import annotations

from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
)


# ---------------------------------------------------------------------------
# Validadores reutilizables
# ---------------------------------------------------------------------------


def _validate_strong_password(value: str) -> str:
    """Validador de política mínima de contraseña.

    Reglas (spec §password-recovery → Política mínima de contraseñas):
    - Mínimo 12 caracteres.
    - Al menos 1 mayúscula, 1 minúscula, 1 dígito.
    - No se exige carácter especial (recomendado pero no obligatorio).

    Args:
        value: Password en texto plano.

    Returns:
        El mismo ``value`` si pasa todas las reglas.

    Raises:
        ValueError: Con detalle de la regla que falla (Pydantic convierte
            a 422 Unprocessable Entity).
    """
    if len(value) < 12:
        raise ValueError("Password must be at least 12 characters long")
    if not any(c.isupper() for c in value):
        raise ValueError("Password must contain at least 1 uppercase letter")
    if not any(c.islower() for c in value):
        raise ValueError("Password must contain at least 1 lowercase letter")
    if not any(c.isdigit() for c in value):
        raise ValueError("Password must contain at least 1 digit")
    return value


# Tipo reusable — usar como ``new_password: StrongPassword`` en cualquier schema.
StrongPassword = Annotated[str, AfterValidator(_validate_strong_password)]


# Pattern de código TOTP: exactamente 6 dígitos (regex anchorada).
_TOTP_CODE_PATTERN = r"^\d{6}$"


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    """Body de ``POST /api/auth/login``.

    Attributes:
        email: Email del usuario (lookup key).
        password: Password en texto plano. El backend lo hashea con Argon2id;
            nunca se loggea ni se devuelve.
    """

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


# ---------------------------------------------------------------------------
# Token pair (respuesta común a login / refresh / 2fa/verify)
# ---------------------------------------------------------------------------


class TokenPair(BaseModel):
    """Par de tokens emitidos al usuario autenticado.

    Attributes:
        access_token: JWT firmado con HS256 (claims: sub, tenant_id, roles, exp).
        refresh_token: Token opaco (256 bits). Se guarda hasheado en DB; el
            cliente lo presenta en cada ``/refresh`` y se rota.
        token_type: Siempre ``"bearer"`` (estándar OAuth2).
        expires_in: TTL del access en segundos (``ACCESS_TOKEN_EXPIRE_MINUTES * 60``,
            default 900 = 15 min).
    """

    model_config = ConfigDict(extra="forbid")

    access_token: str
    refresh_token: str
    token_type: str = Field(default="bearer", frozen=True)
    expires_in: int = Field(gt=0, le=86400)  # entre 1s y 24h


# ---------------------------------------------------------------------------
# 2FA — challenge (response de /login cuando totp_enabled=True)
# ---------------------------------------------------------------------------


class TwoFactorChallengeResponse(BaseModel):
    """Respuesta de ``/login`` cuando el usuario tiene 2FA habilitado.

    NO emite access ni refresh. El cliente debe ``POST /2fa/verify`` con
    ``challenge_token`` + código TOTP para obtener el par.

    Attributes:
        twofa_required: Siempre ``True``. El discriminador para que el frontend
            sepa qué hacer (mostrar input de código TOTP).
        challenge_token: Token opaco de un solo uso (TTL 5 min).
    """

    model_config = ConfigDict(extra="forbid")

    twofa_required: bool = Field(default=True, frozen=True)
    challenge_token: str = Field(min_length=32)


# ---------------------------------------------------------------------------
# 2FA — enrollment
# ---------------------------------------------------------------------------


class TwoFactorEnrollResponse(BaseModel):
    """Respuesta de ``POST /2fa/enroll``.

    Attributes:
        secret: Secreto TOTP en base32 (160 bits). Se cifra antes de persistir.
        otpauth_uri: URI estándar ``otpauth://totp/<issuer>:<email>?...``
            (compatible con Google Authenticator, Authy, 1Password, etc.).
        qr_png_base64: PNG del QR code codificado en base64. El frontend
            lo decodifica y muestra al usuario para escaneo.
    """

    model_config = ConfigDict(extra="forbid")

    secret: str = Field(min_length=16, max_length=64)
    otpauth_uri: str = Field(min_length=20)
    qr_png_base64: str = Field(min_length=1)


class TOTPConfirmRequest(BaseModel):
    """Body de ``POST /2fa/confirm``.

    El usuario confirma que pudo escanear el QR y obtener un código TOTP
    válido. Si el código es OK, ``totp_enabled`` pasa a ``True``.

    Attributes:
        code: Código TOTP de 6 dígitos.
    """

    model_config = ConfigDict(extra="forbid")

    code: str = Field(pattern=_TOTP_CODE_PATTERN, min_length=6, max_length=6)


# ---------------------------------------------------------------------------
# 2FA — verify (post-login con 2FA)
# ---------------------------------------------------------------------------


class TOTPVerifyRequest(BaseModel):
    """Body de ``POST /2fa/verify``.

    Attributes:
        challenge_token: Token opaco devuelto por ``/login`` cuando 2FA activo.
        code: Código TOTP de 6 dígitos.
    """

    model_config = ConfigDict(extra="forbid")

    challenge_token: str = Field(min_length=32)
    code: str = Field(pattern=_TOTP_CODE_PATTERN, min_length=6, max_length=6)


# ---------------------------------------------------------------------------
# Refresh + Logout
# ---------------------------------------------------------------------------


class RefreshRequest(BaseModel):
    """Body de ``POST /api/auth/refresh``.

    Attributes:
        refresh_token: Token opaco recibido en un ``TokenPair`` previo.
    """

    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(min_length=32)


class LogoutRequest(BaseModel):
    """Body de ``POST /api/auth/logout``.

    Attributes:
        refresh_token: Token opaco a revocar.
    """

    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(min_length=32)


# ---------------------------------------------------------------------------
# Forgot / Reset password
# ---------------------------------------------------------------------------


class ForgotRequest(BaseModel):
    """Body de ``POST /api/auth/forgot``.

    Attributes:
        email: Email del usuario que quiere recuperar su contraseña.
    """

    model_config = ConfigDict(extra="forbid")

    email: EmailStr


class ResetRequest(BaseModel):
    """Body de ``POST /api/auth/reset``.

    Attributes:
        token: Token opaco recibido por email (del ``/forgot``).
        new_password: Nuevo password. Validado por ``StrongPassword``
            (≥12 chars + 1 upper + 1 lower + 1 digit).
    """

    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=32)
    new_password: StrongPassword


# ---------------------------------------------------------------------------
# Impersonation
# ---------------------------------------------------------------------------


class ImpersonateRequest(BaseModel):
    """Body de ``POST /api/auth/impersonate``.

    Attributes:
        target_user_id: UUID del usuario a impersonar.
    """

    model_config = ConfigDict(extra="forbid")

    target_user_id: str = Field(min_length=36, max_length=36)


class ImpersonateStopResponse(BaseModel):
    """Respuesta de ``POST /api/auth/impersonate/stop``.

    Attributes:
        access_token: Nuevo JWT para el actor real.
        refresh_token: Nuevo refresh token para el actor real.
        token_type: Siempre ``"bearer"``.
        expires_in: TTL del access token en segundos.
    """

    model_config = ConfigDict(extra="forbid")

    access_token: str
    refresh_token: str
    token_type: str = Field(default="bearer", frozen=True)
    expires_in: int = Field(gt=0, le=86400)


class PasswordResetRequest(BaseModel):
    """Body de un futuro ``POST /api/auth/password`` (cambio autenticado).

    Existe como schema explícito para casos de uso donde el usuario ya está
    autenticado y quiere cambiar su propia contraseña (futuro endpoint, no
    expuesto aún en el router C-03). Mantiene la misma política de
    ``StrongPassword`` que ``ResetRequest``.

    Attributes:
        new_password: Nuevo password. Validado por ``StrongPassword``.
    """

    model_config = ConfigDict(extra="forbid")

    new_password: StrongPassword


# ---------------------------------------------------------------------------
# /me — identidad del usuario actual
# ---------------------------------------------------------------------------


class UserMeResponse(BaseModel):
    """Respuesta de ``GET /api/auth/me``.

    Contiene la identidad derivada del JWT. NO incluye ``password_hash``
    ni ``totp_secret`` (que está cifrado).

    Attributes:
        id: UUID del usuario.
        tenant_id: UUID del tenant.
        email: Email del usuario.
        is_active: Si el usuario está habilitado.
        totp_enabled: Si tiene 2FA enrolado y activo.
        roles: Lista de roles (del JWT, poblado en C-04).
        permisos: Permisos efectivos del usuario (resueltos server-side).
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    tenant_id: str
    email: EmailStr
    is_active: bool
    totp_enabled: bool
    roles: list[str] = Field(default_factory=list)
    permisos: list[str] = Field(default_factory=list)
