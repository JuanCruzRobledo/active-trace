"""Tests de rate limiting en endpoints sensibles (C-03).

Verifica que 5 requests desde la misma IP son aceptadas y la 6ª recibe 429.
Cada endpoint (login, refresh, forgot) tiene su propio límite.

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


class TestLoginRateLimit:
    """Rate limit 5/60s en POST /api/auth/login."""

    async def _create_user(self, db_session: AsyncSession):
        repo = UserRepository(session=db_session, tenant_id=_DEV_TENANT_ID)
        user = await repo.create(
            email="rate@example.com",
            password_hash=hash_password("RateLimit123!"),
            is_active=True,
        )
        await db_session.commit()
        return user

    @pytest.mark.flaky(reruns=2)
    async def test_login_5_ok_then_6th_429(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """5 requests OK, 6ª 429 (misma IP)."""
        await self._create_user(db_session)
        payload = {"email": "rate@example.com", "password": "RateLimit123!"}

        for i in range(5):
            r = await client.post("/api/auth/login", json=payload)
            assert r.status_code == 200, (
                f"Request {i + 1} debería ser 200, obtuvo {r.status_code}"
            )

        r6 = await client.post("/api/auth/login", json=payload)
        assert r6.status_code == 429

    @pytest.mark.xfail(
        strict=False,
        reason=(
            "ASGITransport no modifica remote_addr. La IP del cliente "
            "siempre es '127.0.0.1' independientemente del base_url; "
            "el rate limit de 5/60s se excede. Requiere inyectar "
            "X-Forwarded-For o usar un transport personalizado."
        ),
    )
    async def test_different_ip_not_affected_by_other_ip(
        self, db_session: AsyncSession
    ) -> None:
        """IP distinta NO comparte contador con IP original."""
        from httpx import ASGITransport, AsyncClient
        from app.main import create_app
        from app.core.config import Settings

        settings = Settings(
            DATABASE_URL="placeholder",
            SECRET_KEY="a" * 64,
            ENCRYPTION_KEY="b" * 32,
            ENVIRONMENT="development",
        )
        app = create_app(settings)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://other-client",
        ) as other_client:
            await self._create_user(db_session)
            payload = {"email": "rate@example.com", "password": "RateLimit123!"}

            for i in range(6):
                r = await other_client.post("/api/auth/login", json=payload)
                assert r.status_code == 200, (
                    f"Request {i + 1} con IP distinta debería ser 200, "
                    f"obtuvo {r.status_code}"
                )


class TestRefreshRateLimit:
    """Rate limit 5/60s en POST /api/auth/refresh."""

    async def _create_user_and_login(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> dict:
        repo = UserRepository(session=db_session, tenant_id=_DEV_TENANT_ID)
        await repo.create(
            email="refresh-rate@example.com",
            password_hash=hash_password("Refresh123!"),
            is_active=True,
        )
        await db_session.commit()

        r = await client.post(
            "/api/auth/login",
            json={
                "email": "refresh-rate@example.com",
                "password": "Refresh123!",
            },
        )
        assert r.status_code == 200
        return r.json()

    async def test_refresh_5_ok_then_6th_429(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """5 refreshes OK, 6ª 429."""
        pair = await self._create_user_and_login(client, db_session)

        for i in range(5):
            r = await client.post(
                "/api/auth/refresh",
                json={"refresh_token": pair["refresh_token"]},
            )
            assert r.status_code == 200, (
                f"Refresh {i + 1} debería ser 200, obtuvo {r.status_code}"
            )
            pair = r.json()

        r6 = await client.post(
            "/api/auth/refresh",
            json={"refresh_token": pair["refresh_token"]},
        )
        assert r6.status_code == 429


class TestForgotRateLimit:
    """Rate limit 5/60s en POST /api/auth/forgot."""

    async def test_forgot_5_ok_then_6th_429(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """5 forgot OK, 6ª 429."""
        payload = {"email": "nobody@example.com"}

        for i in range(5):
            r = await client.post("/api/auth/forgot", json=payload)
            assert r.status_code == 204, (
                f"Forgot {i + 1} debería ser 204, obtuvo {r.status_code}"
            )

        r6 = await client.post("/api/auth/forgot", json=payload)
        assert r6.status_code == 429
