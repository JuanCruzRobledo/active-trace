"""Tests para ``app.core.security`` (C-03): password, JWT, tokens opacos."""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from argon2.exceptions import VerifyMismatchError

from app.core.security import (
    JWT_ALGORITHM,
    JWT_TYPE_ACCESS,
    SecurityError,
    create_access_token,
    decode_access_token,
    generate_opaque_token,
    hash_opaque_token,
    hash_password,
    InvalidTokenError,
    TokenExpiredError,
    verify_password,
)


SECRET = "x" * 64  # ≥32 chars


# ===========================================================================
# Password hashing (Argon2id)
# ===========================================================================


class TestHashPassword:
    """``hash_password`` produce un hash Argon2id válido."""

    def test_hash_returns_non_empty_string(self):
        h = hash_password("MiPassword2026!")
        assert isinstance(h, str)
        assert len(h) > 50  # hash Argon2id es ~80-100 chars

    def test_hash_starts_with_argon2_marker(self):
        """Argon2id format: ``$argon2id$v=19$m=...$...$...``."""
        h = hash_password("MiPassword2026!")
        assert h.startswith("$argon2id$")

    def test_hash_is_deterministic_on_salt(self):
        """Cada hash usa un salt aleatorio distinto (mismo password → distintos hashes)."""
        h1 = hash_password("MiPassword2026!")
        h2 = hash_password("MiPassword2026!")
        assert h1 != h2

    def test_hash_rejects_empty_password(self):
        with pytest.raises(ValueError):
            hash_password("")


class TestVerifyPassword:
    """``verify_password`` valida contra el hash."""

    def test_correct_password_returns_true(self):
        h = hash_password("MiPassword2026!")
        assert verify_password("MiPassword2026!", h) is True

    def test_wrong_password_returns_false(self):
        h = hash_password("MiPassword2026!")
        assert verify_password("OtraPassword2026!", h) is False

    def test_empty_plain_returns_false(self):
        h = hash_password("MiPassword2026!")
        assert verify_password("", h) is False

    def test_empty_hash_returns_false(self):
        assert verify_password("MiPassword2026!", "") is False

    def test_corrupted_hash_returns_false(self):
        """Hash inválido no levanta — se trata como "no coincide" (defense)."""
        assert verify_password("MiPassword2026!", "$invalid$hash") is False

    def test_verify_against_fresh_hash(self):
        """Roundtrip: hash + verify inmediato del mismo password."""
        pwd = "MiPassword2026!"
        assert verify_password(pwd, hash_password(pwd)) is True


# ===========================================================================
# JWT (access tokens)
# ===========================================================================


class TestCreateAccessToken:
    """``create_access_token`` firma JWT HS256 con los claims correctos."""

    def test_returns_string(self):
        token = create_access_token(uuid4(), uuid4(), secret_key=SECRET)
        assert isinstance(token, str)
        # JWT tiene 3 segmentos separados por puntos
        assert len(token.split(".")) == 3

    def test_token_contains_user_id_in_sub(self):
        user_id = uuid4()
        token = create_access_token(user_id, uuid4(), secret_key=SECRET)
        payload = jwt.decode(token, SECRET, algorithms=[JWT_ALGORITHM])
        assert payload["sub"] == str(user_id)

    def test_token_contains_tenant_id(self):
        tenant_id = uuid4()
        token = create_access_token(uuid4(), tenant_id, secret_key=SECRET)
        payload = jwt.decode(token, SECRET, algorithms=[JWT_ALGORITHM])
        assert payload["tenant_id"] == str(tenant_id)

    def test_token_contains_roles(self):
        token = create_access_token(
            uuid4(), uuid4(), roles=["admin", "tutor"], secret_key=SECRET
        )
        payload = jwt.decode(token, SECRET, algorithms=[JWT_ALGORITHM])
        assert payload["roles"] == ["admin", "tutor"]

    def test_token_default_roles_empty_list(self):
        token = create_access_token(uuid4(), uuid4(), secret_key=SECRET)
        payload = jwt.decode(token, SECRET, algorithms=[JWT_ALGORITHM])
        assert payload["roles"] == []

    def test_token_contains_type_access(self):
        token = create_access_token(uuid4(), uuid4(), secret_key=SECRET)
        payload = jwt.decode(token, SECRET, algorithms=[JWT_ALGORITHM])
        assert payload["type"] == JWT_TYPE_ACCESS

    def test_token_contains_iat_and_exp(self):
        before = int(datetime.now(UTC).timestamp())
        token = create_access_token(
            uuid4(), uuid4(), secret_key=SECRET, expires_minutes=15
        )
        after = int(datetime.now(UTC).timestamp())
        payload = jwt.decode(token, SECRET, algorithms=[JWT_ALGORITHM])
        assert before <= payload["iat"] <= after
        # 15 min = 900s
        assert payload["exp"] - payload["iat"] == 15 * 60

    def test_custom_expires_minutes(self):
        token = create_access_token(
            uuid4(), uuid4(), secret_key=SECRET, expires_minutes=60
        )
        payload = jwt.decode(token, SECRET, algorithms=[JWT_ALGORITHM])
        assert payload["exp"] - payload["iat"] == 60 * 60

    def test_extra_claims_merged(self):
        token = create_access_token(
            uuid4(),
            uuid4(),
            secret_key=SECRET,
            extra_claims={"custom_claim": "x"},
        )
        payload = jwt.decode(token, SECRET, algorithms=[JWT_ALGORITHM])
        assert payload["custom_claim"] == "x"


class TestDecodeAccessToken:
    """``decode_access_token`` valida firma, expiración y claims."""

    def test_decode_valid_token(self):
        user_id = uuid4()
        tenant_id = uuid4()
        token = create_access_token(user_id, tenant_id, secret_key=SECRET)
        payload = decode_access_token(token, secret_key=SECRET)
        assert payload["sub"] == str(user_id)
        assert payload["tenant_id"] == str(tenant_id)

    def test_decode_with_different_secret_raises_invalid(self):
        token = create_access_token(uuid4(), uuid4(), secret_key=SECRET)
        with pytest.raises(InvalidTokenError):
            decode_access_token(token, secret_key="y" * 64)

    def test_decode_expired_token_raises_expired(self):
        # Generar un token que ya expiró
        now = datetime.now(UTC)
        payload = {
            "sub": str(uuid4()),
            "tenant_id": str(uuid4()),
            "roles": [],
            "type": JWT_TYPE_ACCESS,
            "iat": int((now - timedelta(minutes=30)).timestamp()),
            "exp": int((now - timedelta(minutes=15)).timestamp()),
        }
        token = jwt.encode(payload, SECRET, algorithm=JWT_ALGORITHM)
        with pytest.raises(TokenExpiredError):
            decode_access_token(token, secret_key=SECRET)

    def test_decode_malformed_token_raises_invalid(self):
        with pytest.raises(InvalidTokenError):
            decode_access_token("not.a.jwt", secret_key=SECRET)

    def test_decode_empty_token_raises_invalid(self):
        with pytest.raises(InvalidTokenError):
            decode_access_token("", secret_key=SECRET)

    def test_decode_token_missing_sub_raises_invalid(self):
        now = datetime.now(UTC)
        payload = {
            "tenant_id": str(uuid4()),
            "roles": [],
            "type": JWT_TYPE_ACCESS,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=15)).timestamp()),
        }
        token = jwt.encode(payload, SECRET, algorithm=JWT_ALGORITHM)
        with pytest.raises(InvalidTokenError, match="sub"):
            decode_access_token(token, secret_key=SECRET)

    def test_decode_token_missing_tenant_id_raises_invalid(self):
        now = datetime.now(UTC)
        payload = {
            "sub": str(uuid4()),
            "roles": [],
            "type": JWT_TYPE_ACCESS,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=15)).timestamp()),
        }
        token = jwt.encode(payload, SECRET, algorithm=JWT_ALGORITHM)
        with pytest.raises(InvalidTokenError, match="tenant_id"):
            decode_access_token(token, secret_key=SECRET)

    def test_decode_token_wrong_type_raises_invalid(self):
        """Token de tipo != 'access' es rechazado (defense vs refresh-as-access)."""
        now = datetime.now(UTC)
        payload = {
            "sub": str(uuid4()),
            "tenant_id": str(uuid4()),
            "roles": [],
            "type": "refresh",  # no es access
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=15)).timestamp()),
        }
        token = jwt.encode(payload, SECRET, algorithm=JWT_ALGORITHM)
        with pytest.raises(InvalidTokenError, match="type"):
            decode_access_token(token, secret_key=SECRET)


class TestJWTRoundTrip:
    """El roundtrip completo: create → decode → claims correctos."""

    def test_full_roundtrip(self):
        user_id = uuid4()
        tenant_id = uuid4()
        roles = ["tutor", "coordinador"]
        token = create_access_token(
            user_id, tenant_id, roles=roles, secret_key=SECRET
        )
        payload = decode_access_token(token, secret_key=SECRET)
        assert payload["sub"] == str(user_id)
        assert payload["tenant_id"] == str(tenant_id)
        assert payload["roles"] == roles
        assert payload["type"] == JWT_TYPE_ACCESS

    def test_different_secrets_produce_invalid_signature(self):
        """Un token firmado con key A no se decodifica con key B."""
        token = create_access_token(uuid4(), uuid4(), secret_key="A" * 64)
        with pytest.raises(InvalidTokenError):
            decode_access_token(token, secret_key="B" * 64)


# ===========================================================================
# Opaque tokens
# ===========================================================================


class TestGenerateOpaqueToken:
    """``generate_opaque_token`` produce tokens de 256 bits."""

    def test_returns_string(self):
        t = generate_opaque_token()
        assert isinstance(t, str)

    def test_token_has_at_least_32_chars(self):
        """256 bits en base64 URL-safe = ~43 chars; exigimos ≥32 para flexibilidad."""
        t = generate_opaque_token()
        assert len(t) >= 32

    def test_token_has_sufficient_entropy(self):
        """Ningún par de tokens consecutivos es igual (probabilístico, no testea entropía real)."""
        tokens = {generate_opaque_token() for _ in range(1000)}
        assert len(tokens) == 1000

    def test_token_is_url_safe(self):
        """El token no debe tener caracteres que rompan URLs (sin ``+``, ``/``, ``=``)."""
        t = generate_opaque_token()
        assert "+" not in t
        assert "/" not in t


class TestHashOpaqueToken:
    """``hash_opaque_token`` produce SHA-256 hex."""

    def test_hash_returns_64_char_hex(self):
        h = hash_opaque_token("opaque-token")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_hash_is_deterministic(self):
        assert hash_opaque_token("abc") == hash_opaque_token("abc")

    def test_different_tokens_different_hashes(self):
        assert hash_opaque_token("a") != hash_opaque_token("b")

    def test_hash_known_value(self):
        """SHA-256 de 'abc' = ba7816bf... (test vector oficial NIST)."""
        expected = (
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        )
        assert hash_opaque_token("abc") == expected

    def test_rejects_empty(self):
        with pytest.raises(ValueError):
            hash_opaque_token("")


# ===========================================================================
# Triangulación
# ===========================================================================


class TestSecurityTriangulate:
    """Sanity checks cruzados."""

    def test_invalid_token_error_is_security_error(self):
        """``InvalidTokenError`` extiende ``SecurityError`` (jerarquía usable en except)."""
        assert issubclass(InvalidTokenError, SecurityError)

    def test_token_expired_error_is_security_error(self):
        assert issubclass(TokenExpiredError, SecurityError)

    def test_password_and_token_have_no_collisions(self):
        """Hashes de password (Argon2id) y de token (SHA-256) son distinguibles."""
        pwd_hash = hash_password("MiPassword2026!")
        tok_hash = hash_opaque_token("MiPassword2026!")
        # Argon2id empieza con $argon2id$; SHA-256 es hex puro
        assert pwd_hash.startswith("$argon2id$")
        assert not tok_hash.startswith("$argon2id$")
        assert len(tok_hash) == 64
