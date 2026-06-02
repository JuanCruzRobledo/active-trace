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


def init_engine(
    database_url: str, encryption_key: str | None = None
) -> None:
    """Crea el engine async y la factory de sesiones.

    Debe llamarse una sola vez durante el lifespan de la aplicación.

    Args:
        database_url: DSN PostgreSQL con driver asyncpg,
            ej. ``postgresql+asyncpg://user:pass@localhost:5432/db``.
        encryption_key: Clave Fernet para las columnas ``EncryptedColumn``.
            Si no se pasa, se lee de ``Settings()`` (cargada de ``.env``).
            En tests se debe pasar explícitamente para no depender del
            entorno.
    """
    global _engine, async_session_maker  # noqa: PLW0603
    _engine = create_async_engine(database_url, echo=False, pool_pre_ping=True)
    async_session_maker = async_sessionmaker(
        _engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    # Asegurar que las columnas cifradas usen la clave real (no el placeholder).
    # Importación local para evitar circular import en tiempo de carga del módulo.
    from app.core.encryption import inject_encryption_keys  # noqa: PLC0415

    if encryption_key is None:
        from app.core.config import Settings  # noqa: PLC0415

        encryption_key = Settings().ENCRYPTION_KEY  # type: ignore[call-arg]
    inject_encryption_keys(encryption_key)


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
