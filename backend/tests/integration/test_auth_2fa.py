"""Tests E2E de 2FA TOTP (C-03): enroll, confirm, login challenge, verify.

Requiere PostgreSQL real (DATABASE_URL_TEST en el entorno).
"""

from __future__ import annotations

from uuid import UUID

import pyotp
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


class TestTwoFactorEnroll:
    """POST /api/auth/2fa/enroll y /2fa/confirm — enrollment 2FA."""

    async def _create_user_and_login(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> tuple[dict, UUID]:
        repo = UserRepository(session=db_session, tenant_id=_DEV_TENANT_ID)
        user = await repo.create(
            email="dave@example.com",
            password_hash=hash_password("DavePass123!"),
            is_active=True,
        )
        await db_session.commit()

        resp = await client.post(
            "/api/auth/login",
            json={"email": "dave@example.com", "password": "DavePass123!"},
        )
        assert resp.status_code == 200
        pair = resp.json()
        return pair, user.id

    async def test_enroll_without_auth_returns_401(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GIVEN sin autenticación WHEN /2fa/enroll THEN 401."""
        resp = await client.post("/api/auth/2fa/enroll")
        assert resp.status_code == 401

    async def test_enroll_authenticated_returns_secret_qr(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GIVEN usuario autenticado WHEN /2fa/enroll THEN 200 + secret/uri/qr."""
        pair, _ = await self._create_user_and_login(client, db_session)

        resp = await client.post(
            "/api/auth/2fa/enroll",
            headers={"Authorization": f"Bearer {pair['access_token']}"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert "secret" in body
        assert "otpauth_uri" in body
        assert "qr_png_base64" in body
        assert body["otpauth_uri"].startswith("otpauth://")

    async def test_confirm_with_valid_code_returns_204(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GIVEN código TOTP válido para el secret WHEN /2fa/confirm THEN 204."""
        pair, _ = await self._create_user_and_login(client, db_session)

        enroll_resp = await client.post(
            "/api/auth/2fa/enroll",
            headers={"Authorization": f"Bearer {pair['access_token']}"},
        )
        assert enroll_resp.status_code == 200
        secret = enroll_resp.json()["secret"]

        totp = pyotp.TOTP(secret)
        code = totp.now()

        confirm_resp = await client.post(
            "/api/auth/2fa/confirm",
            json={"code": code},
            headers={"Authorization": f"Bearer {pair['access_token']}"},
        )
        assert confirm_resp.status_code == 204

    async def test_confirm_with_invalid_code_returns_400(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GIVEN código TOTP inválido WHEN /2fa/confirm THEN 400."""
        pair, _ = await self._create_user_and_login(client, db_session)

        await client.post(
            "/api/auth/2fa/enroll",
            headers={"Authorization": f"Bearer {pair['access_token']}"},
        )

        confirm_resp = await client.post(
            "/api/auth/2fa/confirm",
            json={"code": "000000"},
            headers={"Authorization": f"Bearer {pair['access_token']}"},
        )
        assert confirm_resp.status_code == 400


class TestTwoFactorLogin:
    """Login con 2FA activo + POST /api/auth/2fa/verify."""

    async def _setup_user_with_2fa(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> tuple[str, str, UUID]:
        repo = UserRepository(session=db_session, tenant_id=_DEV_TENANT_ID)
        user = await repo.create(
            email="eve@example.com",
            password_hash=hash_password("EvePass123!"),
            is_active=True,
        )
        await db_session.commit()

        resp = await client.post(
            "/api/auth/login",
            json={"email": "eve@example.com", "password": "EvePass123!"},
        )
        assert resp.status_code == 200
        pair = resp.json()

        enroll_resp = await client.post(
            "/api/auth/2fa/enroll",
            headers={"Authorization": f"Bearer {pair['access_token']}"},
        )
        assert enroll_resp.status_code == 200
        secret = enroll_resp.json()["secret"]

        totp = pyotp.TOTP(secret)
        code = totp.now()
        await client.post(
            "/api/auth/2fa/confirm",
            json={"code": code},
            headers={"Authorization": f"Bearer {pair['access_token']}"},
        )

        return secret, pair["access_token"], user.id

    async def test_login_with_2fa_returns_challenge(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        seed_dev_tenant: None,
    ) -> None:
        """GIVEN usuario con 2FA activo WHEN login THEN 200 + challenge_token."""
        await self._setup_user_with_2fa(client, db_session)

        resp = await client.post(
            "/api/auth/login",
            json={"email": "eve@example.com", "password": "EvePass123!"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["twofa_required"] is True
        assert "challenge_token" in body

    async def test_verify_2fa_valid_code_returns_token_pair(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        seed_dev_tenant: None,
    ) -> None:
        """GIVEN challenge + TOTP válido WHEN /2fa/verify THEN 200 + TokenPair."""
        secret, _, _ = await self._setup_user_with_2fa(client, db_session)

        login_resp = await client.post(
            "/api/auth/login",
            json={"email": "eve@example.com", "password": "EvePass123!"},
        )
        assert login_resp.status_code == 200
        challenge = login_resp.json()["challenge_token"]

        totp = pyotp.TOTP(secret)
        code = totp.now()

        verify_resp = await client.post(
            "/api/auth/2fa/verify",
            json={"challenge_token": challenge, "code": code},
        )

        assert verify_resp.status_code == 200
        body = verify_resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"

    async def test_verify_2fa_invalid_challenge_returns_401(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        seed_dev_tenant: None,
    ) -> None:
        """GIVEN challenge inválido WHEN /2fa/verify THEN 401."""
        await self._setup_user_with_2fa(client, db_session)
        await client.post(
            "/api/auth/login",
            json={"email": "eve@example.com", "password": "EvePass123!"},
        )

        resp = await client.post(
            "/api/auth/2fa/verify",
            json={"challenge_token": "x" * 43, "code": "123456"},
        )
        assert resp.status_code == 401

    async def test_verify_2fa_wrong_code_returns_401(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        seed_dev_tenant: None,
    ) -> None:
        """GIVEN challenge válido + código incorrecto WHEN /2fa/verify THEN 401."""
        await self._setup_user_with_2fa(client, db_session)

        login_resp = await client.post(
            "/api/auth/login",
            json={"email": "eve@example.com", "password": "EvePass123!"},
        )
        assert login_resp.status_code == 200
        challenge = login_resp.json()["challenge_token"]

        resp = await client.post(
            "/api/auth/2fa/verify",
            json={"challenge_token": challenge, "code": "000000"},
        )
        assert resp.status_code == 401
