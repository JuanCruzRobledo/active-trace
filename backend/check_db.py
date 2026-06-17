"""Check database tables."""
import asyncio
from app.core.database import get_session_maker
from sqlalchemy import text

async def check():
    from app.core.database import init_engine
    await init_engine()
    maker = get_session_maker()
    async with maker() as session:
        result = await session.execute(text("SELECT version_num FROM alembic_version"))
        print("Alembic version:", result.scalar())

        result = await session.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users')"
        ))
        print("Users table exists:", result.scalar())

        result = await session.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'usuario')"
        ))
        print("Usuario table exists:", result.scalar())

        result = await session.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"
        ))
        tables = result.scalars().all()
        print("Tables:", tables)

asyncio.run(check())
