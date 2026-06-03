"""Punto de entrada de activia-trace API.

Uso en desarrollo (con ``--factory``):
    ``uvicorn app.main:create_app --factory --reload``

Uso en producción (Dockerfile):
    ``uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000``
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.routers.auth import router as auth_router
from app.api.v1.routers.health import router as health_router
from app.api.v1.routers.impersonation import router as impersonation_router
from app.core.config import Settings
from app.core.database import close_engine, init_engine
from app.core.logging import configure_json_logging
from app.core.observability import init_opentelemetry


def create_app(settings: Settings | None = None) -> FastAPI:
    """Factory de la aplicación FastAPI.

    Args:
        settings: Opcional.  Si no se provee, se crea desde el entorno.

    Returns:
        Instancia de FastAPI configurada y lista para servir.
    """
    if settings is None:
        settings = Settings()  # type: ignore[call-arg]

    configure_json_logging(settings.LOG_LEVEL)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        """Inicializa engine y OTel al arrancar; cierra al detener."""
        init_engine(settings.DATABASE_URL)
        init_opentelemetry()
        yield
        await close_engine()

    app = FastAPI(
        title="activia-trace",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(impersonation_router)

    return app
