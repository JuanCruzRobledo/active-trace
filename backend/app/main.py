"""Punto de entrada de activia-trace API.

Uso en desarrollo (con ``--factory``):
    ``uvicorn app.main:create_app --factory --reload``

Uso en producción (Dockerfile):
    ``uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000``
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.routers.admin_estructura import router as admin_estructura_router
from app.api.v1.routers.asignaciones import router as asignaciones_router
from app.api.v1.routers.analisis import router as analisis_router
from app.api.v1.routers.auth import router as auth_router
from app.api.v1.routers.calificaciones import router as calificaciones_router
from app.api.v1.routers.comunicaciones import router as comunicaciones_router
from app.api.v1.routers.equipos import router as equipos_router
from app.api.v1.routers.health import router as health_router
from app.api.v1.routers.impersonation import router as impersonation_router
from app.api.v1.routers.padron import router as padron_router
from app.api.v1.routers.usuarios import router as usuarios_router
from app.api.v1.routers.encuentros import router as encuentros_router
from app.api.v1.routers.guardias import router as guardias_router
from app.api.v1.routers.coloquios import router as coloquios_router
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
        debug=False,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(impersonation_router)
    app.include_router(admin_estructura_router)
    app.include_router(usuarios_router)
    app.include_router(equipos_router)
    app.include_router(asignaciones_router)
    app.include_router(padron_router)
    app.include_router(calificaciones_router)
    app.include_router(analisis_router)
    app.include_router(comunicaciones_router)
    app.include_router(encuentros_router)
    app.include_router(guardias_router)
    app.include_router(coloquios_router)

    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )