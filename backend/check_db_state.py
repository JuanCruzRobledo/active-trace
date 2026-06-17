"""Quick script to check DB state."""
import asyncio
from app.core.config import Settings
from app.core.database import init_engine, close_engine, get_session_maker
from sqlalchemy import text


async def check():
    settings = Settings()
    init_engine(settings.DATABASE_URL)
    session_maker = get_session_maker()
    async with session_maker() as session:
        # Check alembic version
        r = await session.execute(text("SELECT version_num FROM alembic_version"))
        alembic = r.scalar()
        print(f"Alembic version: {alembic}")

        # Count tables
        r = await session.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' ORDER BY table_name"
        ))
        tables = [row[0] for row in r]
        print(f"Tables ({len(tables)}):")
        for t in tables:
            print(f"  - {t}")

        # Check users table (auth)
        r = await session.execute(text("SELECT count(*) FROM users"))
        users_count = r.scalar()
        print(f"\nUsers in auth table: {users_count}")

        # Check usuario table (profile)
        r = await session.execute(text("SELECT count(*) FROM usuario"))
        usuarios_count = r.scalar()
        print(f"Usuarios in profile table: {usuarios_count}")

        # Check if admin@trace.dev exists
        r = await session.execute(
            text("SELECT id, email FROM users WHERE email = 'admin@trace.dev'")
        )
        admin = r.fetchone()
        if admin:
            print(f"\nAdmin user exists: id={admin[0]}, email={admin[1]}")
        else:
            print("\nAdmin user NOT FOUND!")

        # Check tareas
        r = await session.execute(text("SELECT count(*) FROM tarea"))
        print(f"Tareas: {r.scalar()}")

        # Check avisos
        r = await session.execute(text("SELECT count(*) FROM aviso"))
        print(f"Avisos: {r.scalar()}")

    close_engine()


asyncio.run(check())
