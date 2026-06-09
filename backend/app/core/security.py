"""Seguridad core: password hashing, JWT, tokens opacos (C-03).

Decisiones de diseño (ver ``openspec/changes/c-03-auth-jwt-2fa/design.md``):

- **D1 — pyjwt sobre python-jose**: ``python-jose`` está abandonado (2022);
  ``pyjwt`` es mantenida, simple y cubre HS256. Single-issuer por ahora.

- **D2 — Refresh tokens opacos hasheados**: ``secrets.token_urlsafe(32)``
  (256 bits) se devuelve al cliente UNA vez en claro y se guarda hasheado
  con SHA-256. Los JWT no se pueden revocar sin blacklist — la rotación
  + DB row ya implementa revocación instantánea sin estado extra.

- **D3 — Argon2id**: ``argon2-cffi`` con parámetros por defecto (mem=64MB,
  t=3, p=4). Cumple NIST SP 800-63B. El password nunca aparece en logs
  ni en responses (ni siquiera hasheado en responses de error).

El módulo expone:
- :func:`hash_password` / :func:`verify_password` — Argon2id.
- :func:`create_access_token` / :func:`decode_access_token` — JWT HS256.
- :func:`generate_opaque_token` / :func:`hash_opaque_token` — 256 bits
  aleatorios + SHA-256.
- :exc:`InvalidTokenError`, :exc:`TokenExpiredError` — para manejo
  tipado en routers/services.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

# ---------------------------------------------------------------------------
# Errores tipados
# ---------------------------------------------------------------------------


class SecurityError(Exception):
    """Base para todos los errores de seguridad."""


class InvalidTokenError(SecurityError):
    """Token JWT o opaco inválido (firma, formato, claims faltantes)."""


class TokenExpiredError(SecurityError):
    """Token JWT expirado (claim ``exp < now``)."""


# ---------------------------------------------------------------------------
# Password hashing (Argon2id)
# ---------------------------------------------------------------------------


def _get_password_hasher() -> PasswordHasher:
    """Hasher Argon2id con parámetros por defecto (mem=64MB, t=3, p=4).

    Cached como singleton a nivel de módulo para evitar reinstanciar
    el costoso :class:`PasswordHasher` en cada llamada.
    """
    global _password_hasher  # noqa: PLW0603
    if "_password_hasher" not in globals():
        _password_hasher = PasswordHasher()  # type: ignore[has-type]
    return _password_hasher  # type: ignore[has-type]


def hash_password(plain: str) -> str:
    """Hashea un password con Argon2id.

    Args:
        plain: Password en texto plano. Nunca se loggea.

    Returns:
        Hash Argon2id (string con salt + parámetros embebidos).

    Raises:
        ValueError: Si ``plain`` está vacío.
    """
    if not plain:
        raise ValueError("Password cannot be empty")
    return _get_password_hasher().hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verifica un password contra un hash Argon2id.

    Args:
        plain: Password en texto plano provisto por el usuario.
        hashed: Hash Argon2id almacenado en DB.

    Returns:
        ``True`` si el password coincide; ``False`` en caso contrario
        (o si el hash es inválido). Esta función NUNCA levanta — un
        hash corrupto se trata como "no coincide" (defensive).

    Note:
        Es CONSTANT-TIME en la verificación interna de Argon2id.
    """
    if not plain or not hashed:
        return False
    try:
        return _get_password_hasher().verify(hashed, plain)
    except (VerifyMismatchError, InvalidHashError):
        return False


# ---------------------------------------------------------------------------
# JWT (access tokens)
# ---------------------------------------------------------------------------

# Claims estándar + custom
JWT_ALGORITHM: ClassVar[str] = "HS256"
JWT_CLAIM_USER_ID: ClassVar[str] = "sub"
JWT_CLAIM_TENANT_ID: ClassVar[str] = "tenant_id"
JWT_CLAIM_ROLES: ClassVar[str] = "roles"
JWT_CLAIM_TYPE: ClassVar[str] = "type"
JWT_CLAIM_IMPERSONATED_BY: ClassVar[str] = "impersonated_by"
JWT_TYPE_ACCESS: ClassVar[str] = "access"


def create_access_token(
    user_id: UUID,
    tenant_id: UUID,
    secret_key: str,
    roles: list[str] | None = None,
    expires_minutes: int = 15,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Firma un access token JWT HS256.

    Args:
        user_id: UUID del usuario (claim ``sub``).
        tenant_id: UUID del tenant (claim custom ``tenant_id``).
        roles: Lista de roles (claim custom ``roles``). ``[]`` por defecto
            en C-03; C-04 (rbac) la puebla desde la tabla de permisos.
        secret_key: ``SECRET_KEY`` del config. Se pasa explícito para
            que la función sea testeable sin monkey-patch de settings.
        expires_minutes: TTL en minutos. Default: 15 (config
            ``ACCESS_TOKEN_EXPIRE_MINUTES``).
        extra_claims: Claims adicionales opcionales (no usar para datos
            sensibles — el JWT es legible por cualquiera que lo intercepte).

    Returns:
        JWT firmado (string).
    """
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        JWT_CLAIM_USER_ID: str(user_id),
        JWT_CLAIM_TENANT_ID: str(tenant_id),
        JWT_CLAIM_ROLES: list(roles or []),
        JWT_CLAIM_TYPE: JWT_TYPE_ACCESS,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_minutes)).timestamp()),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, secret_key, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str, secret_key: str) -> dict[str, Any]:
    """Decodifica y verifica la firma de un access token JWT.

    Args:
        token: JWT firmado.
        secret_key: ``SECRET_KEY`` del config (debe coincidir con el usado
            al firmar).

    Returns:
        Payload (dict con ``sub``, ``tenant_id``, ``roles``, ``exp``, etc.).

    Raises:
        TokenExpiredError: Si ``exp < now()``.
        InvalidTokenError: Si la firma es inválida, el formato es
            malformado o faltan claims requeridos (``sub``, ``tenant_id``).
    """
    if not token:
        raise InvalidTokenError("Token is empty")
    try:
        payload = jwt.decode(
            token, secret_key, algorithms=[JWT_ALGORITHM]
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiredError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise InvalidTokenError(f"Invalid token: {exc}") from exc

    # Validar claims requeridos (defense in depth)
    if JWT_CLAIM_USER_ID not in payload:
        raise InvalidTokenError("Missing 'sub' claim")
    if JWT_CLAIM_TENANT_ID not in payload:
        raise InvalidTokenError("Missing 'tenant_id' claim")
    if payload.get(JWT_CLAIM_TYPE) != JWT_TYPE_ACCESS:
        raise InvalidTokenError("Token type is not 'access'")
    return payload


# ---------------------------------------------------------------------------
# Opaque tokens (refresh + reset + 2FA challenge)
# ---------------------------------------------------------------------------


def generate_opaque_token() -> str:
    """Genera un token opaco de 256 bits de entropía.

    Usa ``secrets.token_urlsafe(32)`` (32 bytes = 256 bits, codificados
    en base64 URL-safe ≈ 43 caracteres). Apto para refresh tokens,
    reset tokens y 2FA challenges.

    Returns:
        Token opaco (string, ~43 chars).
    """
    return secrets.token_urlsafe(32)


def hash_opaque_token(token: str) -> str:
    """Hashea un token opaco con SHA-256 (hex).

    Se usa para indexar en DB: ``token_hash`` es UNIQUE, y el valor
    que se busca/compara es siempre el SHA-256, nunca el token en claro.
    Así, un dump de la DB no permite reuso de tokens.

    Args:
        token: Token opaco en claro.

    Returns:
        SHA-256 hex (64 chars).
    """
    if not token:
        raise ValueError("Token cannot be empty")
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
