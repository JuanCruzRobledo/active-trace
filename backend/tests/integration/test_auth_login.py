"""Tests E2E de POST /api/auth/login (C-03).

Requiere PostgreSQL real (DATABASE_URL_TEST en el entorno).
"""

from __future__ import annotations

from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user_repository import UserRepository
from app.core.security import hash_password
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


class TestAuthLogin:
    """POST /api/auth/login — autenticación por email+password."""

    async def _create_user(
        self,
        db_session: AsyncSession,
        email: str = "alice@example.com",
        password: str = "AlicePass123!",
        is_active: bool = True,
    ):
        repo = UserRepository(session=db_session, tenant_id=_DEV_TENANT_ID)
        user = await repo.create(
            email=email,
            password_hash=hash_password(password),
            is_active=is_active,
        )
        await db_session.commit()
        return user

    async def test_login_success_without_2fa(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GIVEN usuario activo sin 2FA WHEN login con credenciales válidas
        THEN 200 + TokenPair (access_token, refresh_token, expires_in)."""
        await self._create_user(db_session)

        resp = await client.post(
            "/api/auth/login",
            json={"email": "alice@example.com", "password": "AlicePass123!"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"
        assert body["expires_in"] > 0

    async def test_login_nonexistent_email_returns_401(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GIVEN ningún usuario con ese email WHEN login THEN 401."""
        resp = await client.post(
            "/api/auth/login",
            json={"email": "ghost@example.com", "password": "x" * 12},
        )
        assert resp.status_code == 401

    async def test_login_wrong_password_returns_401(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GIVEN usuario existe WHEN password incorrecto THEN 401."""
        await self._create_user(db_session)

        resp = await client.post(
            "/api/auth/login",
            json={"email": "alice@example.com", "password": "WrongPass123!"},
        )
        assert resp.status_code == 401

    async def test_login_inactive_user_returns_401(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GIVEN usuario inactivo WHEN login THEN 401."""
        await self._create_user(db_session, is_active=False)

        resp = await client.post(
            "/api/auth/login",
            json={"email": "alice@example.com", "password": "AlicePass123!"},
        )
        assert resp.status_code == 401

    async def test_login_with_2fa_returns_challenge(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        seed_dev_tenant: None,
    ) -> None:
        """GIVEN usuario con 2FA activo WHEN login THEN 200 + challenge."""
        user = await self._create_user(db_session)

        repo = UserRepository(session=db_session, tenant_id=_DEV_TENANT_ID)
        await repo.enable_totp(user_id=user.id, encrypted_secret="placeholder")
        await db_session.commit()

        resp = await client.post(
            "/api/auth/login",
            json={"email": "alice@example.com", "password": "AlicePass123!"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["twofa_required"] is True
        assert "challenge_token" in body
        assert len(body["challenge_token"]) >= 32

    async def test_login_extra_fields_returns_422(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GIVEN body con campos extra WHEN login THEN 422 (extra='forbid')."""
        resp = await client.post(
            "/api/auth/login",
            json={
                "email": "alice@example.com",
                "password": "AlicePass123!",
                "role": "admin",
            },
        )
        assert resp.status_code == 422

    async def test_login_malformed_email_returns_422(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GIVEN email malformado WHEN login THEN 422."""
        resp = await client.post(
            "/api/auth/login",
            json={"email": "not-an-email", "password": "AlicePass123!"},
        )
        assert resp.status_code == 422
