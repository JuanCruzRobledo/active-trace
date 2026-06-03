"""Tests E2E de password recovery (C-03): POST /forgot y POST /reset.

Requiere PostgreSQL real (DATABASE_URL_TEST en el entorno).
"""

from __future__ import annotations

from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user_repository import UserRepository
from app.repositories.password_reset_token_repository import (
    PasswordResetTokenRepository,
)
from app.core.security import hash_password, hash_opaque_token, generate_opaque_token
from tests.conftest import db_available

pytestmark = [
    pytest.mark.skipif(
        not db_available(),
        reason="Requiere PostgreSQL: definir DATABASE_URL_TEST en el entorno",
    ),
]

_DEV_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")

_STRONG_PASSWORD = "NewSecurePass789!"
_WEAK_PASSWORD = "short"


@pytest.fixture(autouse=True)
def _patch_env(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "a" * 64)
    monkeypatch.setenv("ENCRYPTION_KEY", "b" * 32)
    monkeypatch.setenv("DATABASE_URL", "placeholder")


class TestForgotPassword:
    """POST /api/auth/forgot — solicitud de reset de contraseña."""

    async def _create_user(
        self, db_session: AsyncSession, email: str = "frank@example.com"
    ):
        repo = UserRepository(session=db_session, tenant_id=_DEV_TENANT_ID)
        user = await repo.create(
            email=email,
            password_hash=hash_password("FrankPass123!"),
            is_active=True,
        )
        await db_session.commit()
        return user

    async def test_forgot_existing_email_returns_204(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        seed_dev_tenant: None,
    ) -> None:
        """GIVEN email existente WHEN /forgot THEN 204."""
        await self._create_user(db_session)

        resp = await client.post(
            "/api/auth/forgot",
            json={"email": "frank@example.com"},
        )
        assert resp.status_code == 204

    async def test_forgot_nonexistent_email_returns_204(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GIVEN email que no existe WHEN /forgot THEN 204 (no-op, no revelar)."""
        resp = await client.post(
            "/api/auth/forgot",
            json={"email": "ghost@example.com"},
        )
        assert resp.status_code == 204


class TestResetPassword:
    """POST /api/auth/reset — confirmación de reset de contraseña."""

    async def _create_user_and_reset_token(
        self, db_session: AsyncSession
    ) -> tuple[UUID, str]:
        repo = UserRepository(session=db_session, tenant_id=_DEV_TENANT_ID)
        user = await repo.create(
            email="grace@example.com",
            password_hash=hash_password("GracePass123!"),
            is_active=True,
        )
        await db_session.flush()

        reset_repo = PasswordResetTokenRepository(
            session=db_session, tenant_id=_DEV_TENANT_ID
        )
        raw = generate_opaque_token()
        from datetime import datetime, timedelta, timezone

        await reset_repo.create(
            user_id=user.id,
            token_hash=hash_opaque_token(raw),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        )
        await db_session.commit()
        return user.id, raw

    async def test_reset_valid_token_returns_204(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        seed_dev_tenant: None,
    ) -> None:
        """GIVEN token + password fuerte válidos WHEN /reset THEN 204."""
        await self._create_user_and_reset_token(db_session)
        from app.core.security import generate_opaque_token

        reset_repo = PasswordResetTokenRepository(
            session=db_session, tenant_id=_DEV_TENANT_ID
        )
        raw = generate_opaque_token()
        user_repo = UserRepository(session=db_session, tenant_id=_DEV_TENANT_ID)
        user = await user_repo.get_by_email("grace@example.com")
        from datetime import datetime, timedelta, timezone

        await reset_repo.create(
            user_id=user.id,
            token_hash=hash_opaque_token(raw),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        )
        await db_session.commit()

        resp = await client.post(
            "/api/auth/reset",
            json={"token": raw, "new_password": _STRONG_PASSWORD},
        )
        assert resp.status_code == 204

    async def test_reset_invalid_token_returns_400(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GIVEN token que no existe WHEN /reset THEN 400."""
        resp = await client.post(
            "/api/auth/reset",
            json={"token": "x" * 43, "new_password": _STRONG_PASSWORD},
        )
        assert resp.status_code == 400

    async def test_reset_already_used_token_returns_400(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        seed_dev_tenant: None,
    ) -> None:
        """GIVEN token ya usado WHEN /reset THEN 400."""
        _, token_raw = await self._create_user_and_reset_token(db_session)

        resp1 = await client.post(
            "/api/auth/reset",
            json={"token": token_raw, "new_password": _STRONG_PASSWORD},
        )
        assert resp1.status_code == 204

        resp2 = await client.post(
            "/api/auth/reset",
            json={"token": token_raw, "new_password": _STRONG_PASSWORD},
        )
        assert resp2.status_code == 400

    async def test_reset_weak_password_returns_422(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        seed_dev_tenant: None,
    ) -> None:
        """GIVEN password débil (< 12 chars, sin mayúscula, etc.) WHEN /reset THEN 422."""
        await self._create_user_and_reset_token(db_session)
        from app.core.security import generate_opaque_token

        reset_repo = PasswordResetTokenRepository(
            session=db_session, tenant_id=_DEV_TENANT_ID
        )
        raw = generate_opaque_token()
        user_repo = UserRepository(session=db_session, tenant_id=_DEV_TENANT_ID)
        user = await user_repo.get_by_email("grace@example.com")
        from datetime import datetime, timedelta, timezone

        await reset_repo.create(
            user_id=user.id,
            token_hash=hash_opaque_token(raw),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        )
        await db_session.commit()

        resp = await client.post(
            "/api/auth/reset",
            json={"token": raw, "new_password": _WEAK_PASSWORD},
        )
        assert resp.status_code == 422

    async def test_login_after_reset_with_new_password(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        seed_dev_tenant: None,
    ) -> None:
        """GIVEN reseteo exitoso WHEN login con nueva password THEN 200."""
        await self._create_user_and_reset_token(db_session)
        from app.core.security import generate_opaque_token

        reset_repo = PasswordResetTokenRepository(
            session=db_session, tenant_id=_DEV_TENANT_ID
        )
        raw = generate_opaque_token()
        user_repo = UserRepository(session=db_session, tenant_id=_DEV_TENANT_ID)
        user = await user_repo.get_by_email("grace@example.com")
        from datetime import datetime, timedelta, timezone

        await reset_repo.create(
            user_id=user.id,
            token_hash=hash_opaque_token(raw),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        )
        await db_session.commit()

        await client.post(
            "/api/auth/reset",
            json={"token": raw, "new_password": _STRONG_PASSWORD},
        )

        resp = await client.post(
            "/api/auth/login",
            json={"email": "grace@example.com", "password": _STRONG_PASSWORD},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
