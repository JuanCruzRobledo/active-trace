"""Fixtures compartidas para los tests del backend.

Requiere una base de datos PostgreSQL de test accesible via ``DATABASE_URL_TEST``
(o ``DATABASE_URL`` como fallback) en el entorno.
"""

import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.database import async_session_maker, init_engine, close_engine


def _build_test_settings() -> Settings:
    """Construye un objeto Settings para el entorno de test.

    Usa ``DATABASE_URL_TEST`` si está definida, o ``DATABASE_URL`` como
    fallback.  Si ninguna está presente, el test que dependa de DB real
    se omite (no se mockea — la DB real es parte del contrato).
    """
    return Settings(  # type: ignore[call-arg]
        DATABASE_URL=os.environ.get(
            "DATABASE_URL_TEST",
            os.environ.get("DATABASE_URL", "postgresql+asyncpg://trace:trace@localhost:5432/trace_test"),
        ),
        SECRET_KEY=os.environ.get("SECRET_KEY", "a" * 64),
        ENCRYPTION_KEY=os.environ.get("ENCRYPTION_KEY", "b" * 32),
        ENVIRONMENT="development",
        LOG_LEVEL="DEBUG",
    )


def db_available() -> bool:
    """Indica si hay una base de datos PostgreSQL configurada para tests.

    Retorna ``True`` si ``DATABASE_URL`` o ``DATABASE_URL_TEST`` están
    presentes en el entorno.
    """
    return bool(os.environ.get("DATABASE_URL_TEST") or os.environ.get("DATABASE_URL"))


@pytest.fixture(scope="session")
def settings() -> Settings:
    """Settings del entorno de test (sesión)."""
    return _build_test_settings()


@pytest_asyncio.fixture
async def db_engine(settings: Settings):
    """Inicializa el engine async y lo destruye al finalizar la sesión."""
    await close_engine()
    init_engine(settings.DATABASE_URL)
    yield
    await close_engine()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Sesión async fresca para cada test."""
    maker = async_session_maker
    assert maker is not None
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
