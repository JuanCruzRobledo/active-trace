"""Tests de REGLA DURA #8: identidad SIEMPRE del JWT (C-03).

Ningún query param, body, header o cualquier otro dato de la petición
puede modificar la identidad del usuario autenticado. La identidad se
deriva EXCLUSIVAMENTE del token JWT verificado.

Requiere PostgreSQL real (DATABASE_URL_TEST en el entorno).
"""

from __future__ import annotations

from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user_repository import UserRepository
from app.core.security import (
    create_access_token,
    hash_password,
)
from tests.conftest import db_available

pytestmark = [
    pytest.mark.skipif(
        not db_available(),
        reason="Requiere PostgreSQL: definir DATABASE_URL_TEST en el entorno",
    ),
]

_DEV_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")

_TEST_SECRET_KEY = "a" * 64


@pytest.fixture(autouse=True)
def _patch_env(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", _TEST_SECRET_KEY)
    monkeypatch.setenv("ENCRYPTION_KEY", "b" * 32)
    monkeypatch.setenv("DATABASE_URL", "placeholder")


class TestIdentityImmutable:
    """La identidad del usuario autenticado SIEMPRE viene del JWT."""

    @pytest.fixture(autouse=True)
    async def _setup_users(self, db_session: AsyncSession):
        repo = UserRepository(session=db_session, tenant_id=_DEV_TENANT_ID)
        alice = await repo.create(
            email="alice@example.com",
            password_hash=hash_password("AlicePass123!"),
            is_active=True,
        )
        bob = await repo.create(
            email="bob@example.com",
            password_hash=hash_password("BobPass123!"),
            is_active=True,
        )
        await db_session.commit()
        return alice, bob

    async def test_login_returns_token_pair(
        self, client: AsyncClient, _setup_users
    ) -> None:
        """GIVEN credenciales válidas WHEN login THEN obtengo TokenPair."""
        resp = await client.post(
            "/api/auth/login",
            json={"email": "alice@example.com", "password": "AlicePass123!"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body

    async def test_me_returns_user_id_from_token(
        self, client: AsyncClient, _setup_users
    ) -> None:
        """GIVEN token de Alice WHEN /me THEN user_id es de Alice."""
        pair_resp = await client.post(
            "/api/auth/login",
            json={"email": "alice@example.com", "password": "AlicePass123!"},
        )
        pair = pair_resp.json()

        resp = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {pair['access_token']}"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == "alice@example.com"

    async def test_me_with_query_param_returns_own_identity(
        self, client: AsyncClient, _setup_users, db_session: AsyncSession
    ) -> None:
        """GIVEN token de Alice + query param ``?user_id=bob`` WHEN /me
        THEN user_id sigue siendo el del token (REGLA DURA #8)."""
        pair_resp = await client.post(
            "/api/auth/login",
            json={"email": "alice@example.com", "password": "AlicePass123!"},
        )
        pair = pair_resp.json()

        bob_repo = UserRepository(session=db_session, tenant_id=_DEV_TENANT_ID)
        bob = await bob_repo.get_by_email("bob@example.com")
        assert bob is not None

        resp = await client.get(
            f"/api/auth/me?user_id={bob.id}",
            headers={"Authorization": f"Bearer {pair['access_token']}"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == "alice@example.com", (
            "A pesar del query param ?user_id=..., la identidad debe ser "
            "la del JWT (Alice), no Bob"
        )

    async def test_me_without_token_returns_401(
        self, client: AsyncClient, _setup_users
    ) -> None:
        """GIVEN sin token WHEN /me THEN 401."""
        resp = await client.get("/api/auth/me")
        assert resp.status_code == 401

    async def test_me_with_expired_token_returns_401(
        self, client: AsyncClient, _setup_users
    ) -> None:
        """GIVEN token expirado WHEN /me THEN 401."""
        user_id = UUID("00000000-0000-0000-0000-000000000000")
        token = create_access_token(
            user_id=user_id,
            tenant_id=_DEV_TENANT_ID,
            secret_key=_TEST_SECRET_KEY,
            expires_minutes=-1,
        )

        resp = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401

    async def test_me_with_malformed_token_returns_401(
        self, client: AsyncClient, _setup_users
    ) -> None:
        """GIVEN token malformado WHEN /me THEN 401."""
        resp = await client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer not-a-valid-token"},
        )
        assert resp.status_code == 401

    async def test_logout_with_valid_token_returns_204(
        self, client: AsyncClient, _setup_users
    ) -> None:
        """GIVEN token válido + refresh token WHEN /logout THEN 204."""
        pair_resp = await client.post(
            "/api/auth/login",
            json={"email": "alice@example.com", "password": "AlicePass123!"},
        )
        pair = pair_resp.json()

        resp = await client.post(
            "/api/auth/logout",
            json={"refresh_token": pair["refresh_token"]},
            headers={"Authorization": f"Bearer {pair['access_token']}"},
        )
        assert resp.status_code == 204
