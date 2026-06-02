"""Configuración de Alembic para engine async (asyncpg).

Genera migraciones que corren sobre el engine asíncrono definido en
``app.core.database``.  Sin migraciones de dominio en C-01 — la 001
se crea en C-02.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import Settings
from app.core.database import Base

# Alembic Config object
config = context.config

# Configurar logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata de los modelos para autogenerate
target_metadata = Base.metadata

# Excluir tablas de Alembic del autogenerate
# (no incluir tables internas de Alembic en las migraciones)
target_metadata.namespace = None


def get_database_url() -> str:
    """Obtiene DATABASE_URL desde la configuración tipada."""
    settings = Settings()  # type: ignore[call-arg]
    return settings.DATABASE_URL


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Configura el contexto con solo la URL y el script genera SQL en
    lugar de ejecutarlo contra la base de datos.
    """
    url = config.get_main_option("sqlalchemy.url", get_database_url())
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """Ejecuta migraciones sobre una conexión dada."""
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode con engine async.

    Crea un engine async, obtiene una conexión y ejecuta las migraciones.
    """
    url = config.get_main_option("sqlalchemy.url", get_database_url())
    engine = create_async_engine(url)

    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await engine.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (async wrapper)."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
