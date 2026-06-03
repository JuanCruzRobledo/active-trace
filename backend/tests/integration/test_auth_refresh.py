"""Tests E2E de POST /api/auth/refresh y POST /api/auth/logout (C-03).

Requiere PostgreSQL real (DATABASE_URL_TEST en el entorno).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user_repository import UserRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.core.security import (
    hash_password,
    hash_opaque_token,
    generate_opaque_token,
)
from tests.conftest import db_available

pytestmark = [
    pytest.mark.skipif(
        not db_available(),
        reason="Requiere PostgreSQL: definir DATABASE_URL_TEST en el entorno",
    ),
]

_DEV_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture(autouse=True)
def _patch_env(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "a" * 64)
    monkeypatch.setenv("ENCRYPTION_KEY", "b" * 32)
    monkeypatch.setenv("DATABASE_URL", "placeholder")


class TestAuthRefresh:
    """POST /api/auth/refresh — rotación de refresh token."""

    async def _create_user(
        self,
        db_session: AsyncSession,
        email: str = "bob@example.com",
        password: str = "BobPass123!",
    ):
        repo = UserRepository(session=db_session, tenant_id=_DEV_TENANT_ID)
        user = await repo.create(
            email=email,
            password_hash=hash_password(password),
            is_active=True,
        )
        await db_session.commit()
        return user

    async def _login(
        self, client: AsyncClient, email: str = "bob@example.com", password: str = "BobPass123!"
    ) -> dict:
        resp = await client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
        )
        assert resp.status_code == 200
        return resp.json()

    async def _create_refresh_token(
        self, db_session: AsyncSession, user_id: UUID
    ) -> str:
        repo = RefreshTokenRepository(session=db_session, tenant_id=_DEV_TENANT_ID)
        raw = generate_opaque_token()
        await repo.create(
            user_id=user_id,
            token_hash=hash_opaque_token(raw),
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        await db_session.commit()
        return raw

    async def test_refresh_valid_token_returns_new_pair(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GIVEN refresh token válido WHEN /refresh THEN 200 + nuevo TokenPair."""
        await self._create_user(db_session)
        pair = await self._login(client)

        resp = await client.post(
            "/api/auth/refresh",
            json={"refresh_token": pair["refresh_token"]},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["refresh_token"] != pair["refresh_token"]
        assert body["token_type"] == "bearer"

    async def test_refresh_nonexistent_token_returns_401(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GIVEN token que no existe en DB WHEN /refresh THEN 401."""
        resp = await client.post(
            "/api/auth/refresh",
            json={"refresh_token": "a" * 43},
        )
        assert resp.status_code == 401

    async def test_refresh_revoked_token_returns_401(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GIVEN token ya rotado WHEN /refresh otra vez THEN 401 (reuso)."""
        await self._create_user(db_session)
        pair = await self._login(client)

        resp1 = await client.post(
            "/api/auth/refresh",
            json={"refresh_token": pair["refresh_token"]},
        )
        assert resp1.status_code == 200

        resp2 = await client.post(
            "/api/auth/refresh",
            json={"refresh_token": pair["refresh_token"]},
        )
        assert resp2.status_code == 401

    async def test_refresh_token_of_another_user(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GIVEN token de usuario B WHEN /refresh THEN 200 (no checkea identidad)."""
        await self._create_user(db_session, email="alice@example.com", password="AlicePass123!")
        await self._create_user(db_session, email="bob@example.com", password="BobPass123!")

        pair_a = await self._login(client, email="alice@example.com", password="AlicePass123!")

        resp = await client.post(
            "/api/auth/refresh",
            json={"refresh_token": pair_a["refresh_token"]},
        )
        assert resp.status_code == 200


class TestAuthLogout:
    """POST /api/auth/logout — revocación de refresh token."""

    async def _create_user_and_login(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> tuple[dict, UUID]:
        repo = UserRepository(session=db_session, tenant_id=_DEV_TENANT_ID)
        user = await repo.create(
            email="carol@example.com",
            password_hash=hash_password("CarolPass123!"),
            is_active=True,
        )
        await db_session.commit()

        pair = await self._login(client)
        return pair, user.id

    async def _login(
        self, client: AsyncClient, email: str = "carol@example.com", password: str = "CarolPass123!"
    ) -> dict:
        resp = await client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
        )
        assert resp.status_code == 200
        return resp.json()

    async def test_logout_valid_token_returns_204(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GIVEN usuario autenticado + refresh token válido WHEN /logout THEN 204."""
        pair, _ = await self._create_user_and_login(client, db_session)

        resp = await client.post(
            "/api/auth/logout",
            json={"refresh_token": pair["refresh_token"]},
            headers={"Authorization": f"Bearer {pair['access_token']}"},
        )
        assert resp.status_code == 204

    async def test_logout_without_auth_returns_401(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GIVEN sin token de acceso WHEN /logout THEN 401."""
        resp = await client.post(
            "/api/auth/logout",
            json={"refresh_token": "some-refresh-token"},
        )
        assert resp.status_code == 401

    async def test_logout_other_user_token_returns_204(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GIVEN token de usuario B pero autenticado como A WHEN /logout THEN 204 (no-op)."""
        repo = UserRepository(session=db_session, tenant_id=_DEV_TENANT_ID)
        user_a = await repo.create(
            email="alice@example.com",
            password_hash=hash_password("AlicePass123!"),
            is_active=True,
        )
        user_b = await repo.create(
            email="bob@example.com",
            password_hash=hash_password("BobPass123!"),
            is_active=True,
        )
        await db_session.commit()

        pair_a = await self._login(client, email="alice@example.com", password="AlicePass123!")
        pair_b = await self._login(client, email="bob@example.com", password="BobPass123!")

        resp = await client.post(
            "/api/auth/logout",
            json={"refresh_token": pair_b["refresh_token"]},
            headers={"Authorization": f"Bearer {pair_a['access_token']}"},
        )
        assert resp.status_code == 204
