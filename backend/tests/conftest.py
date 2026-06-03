"""Fixtures compartidas para los tests del backend.

Requiere una base de datos PostgreSQL de test accesible via ``DATABASE_URL_TEST``
(o ``DATABASE_URL`` como fallback) en el entorno.

Las tablas se crean al conectar y se dropean al cerrar la sesión de tests
(scope ``session``), garantizando un estado limpio para cada corrida.
"""

import logging
import os
from collections.abc import AsyncGenerator
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.database import Base, init_engine, close_engine, get_session_maker

# UUID del tenant de desarrollo — usado en toda la suite de C-03.
# Coincide con _DEV_TENANT_ID en routers/auth.py.
_DEV_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture(autouse=True)
def _reset_isolated_loggers() -> None:
    """Resetea loggers aislados (audit, mail) antes de cada test.

    Previene contaminación entre tests cuando el root logger se modifica
    (ej. via ``configure_json_logging`` en ``create_app()``), lo que deja
    a ``caplog`` sin capturar logs en loggers específicos como "audit" o "mail".
    """
    for name in ("audit", "mail"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.setLevel(logging.NOTSET)
        logger.propagate = True


@pytest.fixture(autouse=True)
def _reset_rate_limiter_storage() -> None:
    """Resetea el storage del rate limiter entre tests.

    El limiter es singleton a nivel de módulo — sin este reset, los tests
    que llaman endpoints rate-limited comparten el contador y explotan con
    429 falsos positivos.
    """
    try:
        from app.core.rate_limit import limiter  # noqa: PLC0415
        from limits.storage import MemoryStorage  # noqa: PLC0415

        for attr in ("_limiter", "limiter"):
            obj = getattr(limiter, attr, None)
            if obj is not None:
                if hasattr(obj, "storage"):
                    obj.storage = MemoryStorage()
                    return
    except Exception:
        pass


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

    # Importar TODOS los modelos para que se registren en Base.metadata
    # ANTES de create_all. Si no, las tablas nuevas (C-03 en adelante)
    # no existen y los tests explotan con "no such table".
    import app.models  # noqa: PLC0415, F401

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
async def seed_dev_tenant(db_session: AsyncSession) -> None:
    """Inserta el tenant de desarrollo si no existe.

    Varios modelos (password_reset_token, two_factor_challenge) tienen FK
    ``tenant_id → tenant.id`` — sin este seed, cualquier test que cree
    esos registros explota con ``ForeignKeyViolationError``.

    NO es autouse. Los tests E2E que crean tokens (refresh, 2FA, recovery)
    deben pedirlo explícitamente::

        async def test_foo(seed_dev_tenant: None, ...):
    """
    from app.models.tenant import Tenant  # noqa: PLC0415

    exists = await db_session.get(Tenant, _DEV_TENANT_ID)
    if exists is None:
        db_session.add(
            Tenant(
                id=_DEV_TENANT_ID,
                tenant_id=_DEV_TENANT_ID,
                nombre="Dev Tenant",
            )
        )
        await db_session.commit()


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
