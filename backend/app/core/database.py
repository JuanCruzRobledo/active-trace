"""Configuración del engine async y factory de sesiones SQLAlchemy 2.0.

El engine se inicializa mediante :func:`init_engine` al arrancar la aplicación
(lifespan). La factory :data:`async_session_maker` produce sesiones async
aisladas — una por request — con :func:`~app.core.dependencies.get_db`.
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base declarativa para todos los modelos del dominio."""


# Inicializados por init_engine() en el arranque (lifespan).
_engine = None
async_session_maker: async_sessionmaker[AsyncSession] | None = None


def init_engine(database_url: str) -> None:
    """Crea el engine async y la factory de sesiones.

    Debe llamarse una sola vez durante el lifespan de la aplicación.

    Args:
        database_url: DSN PostgreSQL con driver asyncpg,
            ej. ``postgresql+asyncpg://user:pass@localhost:5432/db``.
    """
    global _engine, async_session_maker  # noqa: PLW0603
    _engine = create_async_engine(database_url, echo=False, pool_pre_ping=True)
    async_session_maker = async_sessionmaker(
        _engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )


async def close_engine() -> None:
    """Dispose del engine. Llamar en el shutdown del lifespan."""
    global _engine  # noqa: PLW0603
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        global async_session_maker  # noqa: PLW0603
        async_session_maker = None


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """Devuelve la factory de sesiones activa.

    Raises:
        RuntimeError: Si ``init_engine`` no fue llamada antes.
    """
    if async_session_maker is None:
        raise RuntimeError(
            "Engine no inicializado. Llama a init_engine() antes de usar la sesión."
        )
    return async_session_maker
