"""Debug script para entender por qué falla el refresh."""
import asyncio
import os
from uuid import UUID

import sys
sys.path.insert(0, os.path.dirname(__file__))

os.environ["DATABASE_URL_TEST"] = "postgresql+asyncpg://postgres:tutuca05@localhost:5432/trace_test"
os.environ["DATABASE_URL"] = "placeholder"
os.environ["SECRET_KEY"] = "a" * 64
os.environ["ENCRYPTION_KEY"] = "b" * 32

from app.core.config import Settings
from app.core.database import Base, init_engine, close_engine, get_session_maker
from app.repositories.user_repository import UserRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.core.security import hash_password, hash_opaque_token
from app.main import create_app
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

_DEV_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")


async def debug():
    settings = Settings(
        DATABASE_URL="postgresql+asyncpg://postgres:tutuca05@localhost:5432/trace_test",
        SECRET_KEY="a" * 64,
        ENCRYPTION_KEY="b" * 32,
    )

    await close_engine()
    init_engine(settings.DATABASE_URL, encryption_key=settings.ENCRYPTION_KEY)
    from app.core.database import _engine
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            text(
                "INSERT INTO tenant (id, tenant_id, nombre, created_at, updated_at) "
                "VALUES ('00000000-0000-0000-0000-000000000001', "
                "'00000000-0000-0000-0000-000000000001', 'Dev', NOW(), NOW()) "
                "ON CONFLICT (id) DO NOTHING"
            )
        )

    maker = get_session_maker()
    async with maker() as session:
        repo = UserRepository(session=session, tenant_id=_DEV_TENANT_ID)
        user = await repo.get_by_email("refresh-rate@example.com")
        if not user:
            user = await repo.create(
                email="refresh-rate@example.com",
                password_hash=hash_password("Refresh123!"),
                is_active=True,
            )
            await session.commit()
            print(f"Created user {user.id}")
        else:
            print(f"Found existing user {user.id}")

        app = create_app(settings)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.post(
                "/api/auth/login",
                json={"email": "refresh-rate@example.com", "password": "Refresh123!"},
            )
            print(f"Login status: {r.status_code}")
            print(f"Login body (first 500): {r.text[:500]}")
            if r.status_code == 200:
                pair = r.json()
                rt = pair.get("refresh_token", "MISSING")
                print(f"Refresh token (len={len(rt)}): {rt[:30]}...")

                # Check if the token exists in DB
                rt_hash = hash_opaque_token(rt)
                refresh_repo = RefreshTokenRepository(
                    session=session, tenant_id=_DEV_TENANT_ID
                )
                stored = await refresh_repo.get_by_token_hash(rt_hash)
                if stored:
                    print(
                        f"Token found in DB: id={stored.id}, "
                        f"revoked={stored.is_revoked()}, "
                        f"expired={stored.is_expired()}"
                    )
                else:
                    print("TOKEN NOT FOUND IN DB!")
                    print(f"Hash used: {rt_hash}")

                r2 = await client.post(
                    "/api/auth/refresh",
                    json={"refresh_token": rt},
                )
                print(f"\nRefresh status: {r2.status_code}")
                print(f"Refresh body: {r2.text[:500]}")
            else:
                print("Login failed — can't proceed")

    await close_engine()


asyncio.run(debug())
