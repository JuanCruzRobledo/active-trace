"""Tests para ``get_current_user`` dependency (C-03).

Verifica que la identidad se extrae exclusivamente del JWT, que los errores
de autenticación se traducen a HTTPException 401 con mensajes correctos,
y que ningún parámetro externo (query string) puede overridear la identidad.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.dependencies import UserContext, get_current_user
from app.core.security import (
    JWT_ALGORITHM,
    JWT_TYPE_ACCESS,
    create_access_token,
)

SECRET = "x" * 64


@pytest.fixture(autouse=True)
def _mock_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mockea Settings para que ``get_current_user`` use un SECRET_KEY conocido.

    Sin este fixture los tests dependerían del archivo ``.env`` real, lo que
    los haría frágiles y no repetibles.
    """

    class _MockSettings:
        SECRET_KEY = SECRET

    monkeypatch.setattr("app.core.config.Settings", lambda: _MockSettings())


class TestGetCurrentUser:
    """``get_current_user`` extrae UserContext del JWT Bearer token."""

    async def test_valid_token_returns_user_context(self):
        """Token válido y vigente → UserContext con todos los claims."""
        user_id = uuid4()
        tenant_id = uuid4()
        roles = ["admin", "tutor"]
        token = create_access_token(user_id, tenant_id, roles=roles, secret_key=SECRET)
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        result = await get_current_user(credentials=credentials)

        assert isinstance(result, UserContext)
        assert result.user_id == user_id
        assert result.tenant_id == tenant_id
        assert result.roles == roles

    async def test_no_token_raises_401(self):
        """Sin credenciales (credentials=None) → 401 Not authenticated."""
        with pytest.raises(HTTPException) as exc:
            await get_current_user(credentials=None)
        assert exc.value.status_code == 401
        assert exc.value.detail == "Not authenticated"

    async def test_empty_token_raises_401(self):
        """Token vacío → 401 Not authenticated."""
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="")

        with pytest.raises(HTTPException) as exc:
            await get_current_user(credentials=credentials)
        assert exc.value.status_code == 401
        assert exc.value.detail == "Not authenticated"

    async def test_expired_token_raises_401(self):
        """Token con exp en el pasado → 401 Token expired."""
        now = datetime.now(UTC)
        payload = {
            "sub": str(uuid4()),
            "tenant_id": str(uuid4()),
            "roles": [],
            "type": JWT_TYPE_ACCESS,
            "iat": int((now - timedelta(hours=1)).timestamp()),
            "exp": int((now - timedelta(minutes=1)).timestamp()),
        }
        token = jwt.encode(payload, SECRET, algorithm=JWT_ALGORITHM)
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with pytest.raises(HTTPException) as exc:
            await get_current_user(credentials=credentials)
        assert exc.value.status_code == 401
        assert exc.value.detail == "Token expired"

    async def test_invalid_signature_raises_401(self):
        """Token firmado con otra key → 401 Invalid token."""
        token = create_access_token(uuid4(), uuid4(), secret_key="y" * 64)
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with pytest.raises(HTTPException) as exc:
            await get_current_user(credentials=credentials)
        assert exc.value.status_code == 401
        assert exc.value.detail == "Invalid token"

    async def test_malformed_token_raises_401(self):
        """String que no es JWT → 401 Invalid token."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="not-a-jwt"
        )

        with pytest.raises(HTTPException) as exc:
            await get_current_user(credentials=credentials)
        assert exc.value.status_code == 401
        assert exc.value.detail == "Invalid token"

    async def test_identity_comes_from_jwt_only(self):
        """La identidad se extrae exclusivamente del JWT (regla dura #8).

        ``get_current_user`` solo recibe ``credentials`` como parámetro, no
        tiene acceso a query params, body ni headers arbitrarios. Este test
        verifica que el user_id devuelto es el del token y no otro valor.
        """
        user_id = uuid4()
        other_user_id = uuid4()
        assert user_id != other_user_id

        token = create_access_token(user_id, uuid4(), secret_key=SECRET)
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        result = await get_current_user(credentials=credentials)

        assert result.user_id == user_id
        assert result.user_id != other_user_id
