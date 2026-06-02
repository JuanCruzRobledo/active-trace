"""Fixtures compartidas para los tests del backend.

Requiere una base de datos PostgreSQL de test accesible via ``DATABASE_URL_TEST``
(o ``DATABASE_URL`` como fallback) en el entorno.

Las tablas se crean al conectar y se dropean al cerrar la sesión de tests
(scope ``session``), garantizando un estado limpio para cada corrida.
"""

import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.database import Base, init_engine, close_engine, get_session_maker


def _load_env_settings() -> Settings:
    """Carga Settings desde .env + defaults mínimos."""
    return Settings(
        DATABASE_URL="placeholder",
        SECRET_KEY="a" * 64,
        ENCRYPTION_KEY="b" * 32,
        ENVIRONMENT="development",
        LOG_LEVEL="DEBUG",
    )


def _build_test_settings() -> Settings:
    """Construye un objeto Settings para el entorno de test.

    Usa ``DATABASE_URL_TEST`` si está definida en el entorno o en ``.env``,
    o ``DATABASE_URL`` como fallback.  Si ninguna está presente, el test que
    dependa de DB real se omite (no se mockea — la DB real es parte del contrato).
    """
    env = _load_env_settings()

    test_db_url = (
        os.environ.get("DATABASE_URL_TEST")
        or env.DATABASE_URL_TEST
        or os.environ.get("DATABASE_URL")
        or env.DATABASE_URL
        or "postgresql+asyncpg://trace:trace@localhost:5432/trace_test"
    )

    return Settings(
        DATABASE_URL=test_db_url,
        SECRET_KEY="a" * 64,
        ENCRYPTION_KEY="b" * 32,
        ENVIRONMENT="development",
        LOG_LEVEL="DEBUG",
    )


def db_available() -> bool:
    """Indica si hay una base de datos PostgreSQL configurada para tests."""
    if os.environ.get("DATABASE_URL_TEST") or os.environ.get("DATABASE_URL"):
        return True
    try:
        env = _load_env_settings()
        return bool(env.DATABASE_URL_TEST or env.DATABASE_URL)
    except Exception:
        return False


@pytest.fixture(scope="session")
def settings() -> Settings:
    """Settings del entorno de test (sesión)."""
    return _build_test_settings()


@pytest_asyncio.fixture
async def db_engine(settings: Settings):
    """Inicializa el engine async, crea tablas y las destruye al finalizar."""
    await close_engine()
    init_engine(settings.DATABASE_URL, encryption_key=settings.ENCRYPTION_KEY)

    # Crear todas las tablas de los modelos registrados en Base
    from app.core.database import _engine  # type: ignore[attr-defined]  # noqa: PLC0415

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Drop todas las tablas al finalizar el test
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await close_engine()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Sesión async fresca para cada test."""
    maker = get_session_maker()
    async with maker() as session:
        yield session


@pytest_asyncio.fixture
async def client(
    settings: Settings, db_engine: None
) -> AsyncGenerator[AsyncClient, None]:
    """Cliente HTTP async contra la app FastAPI (sin servidor real).

    Depende de ``db_engine`` para que el engine esté inicializado antes
    de que el router de health intente usar ``get_session_maker()``.
    """
    from app.main import create_app  # noqa: PLC0415

    application = create_app(settings)
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
