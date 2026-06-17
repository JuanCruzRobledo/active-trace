"""Check login credentials after migration fix."""
import asyncio
from app.core.config import Settings
from app.core.database import init_engine, get_session_maker
from app.core.security import verify_password

async def check():
    settings = Settings()
    print(f"DB URL: {settings.DATABASE_URL}")
    await init_engine(settings.DATABASE_URL, settings.ENCRYPTION_KEY)
    maker = get_session_maker()
    async with maker() as session:
        from app.repositories.user_repository import UserRepository
        from uuid import UUID
        repo = UserRepository(session, UUID("00000000-0000-0000-0000-000000000001"))
        user = await repo.get_by_email("admin@trace.dev")
        if user:
            print(f"User found: {user.email}")
            print(f"Password hash: {user.password_hash[:30]}...")
            for pw in ["admin", "admin123", "password", "123456"]:
                result = verify_password(pw, user.password_hash)
                print(f"Password '{pw}' matches: {result}")
        else:
            print("User NOT found!")

asyncio.run(check())
