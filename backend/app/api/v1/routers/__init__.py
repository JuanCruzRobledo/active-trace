"""API v1 routers package."""

from app.api.v1.routers.admin_estructura import router as admin_estructura_router
from app.api.v1.routers.asignaciones import router as asignaciones_router
from app.api.v1.routers.auth import router as auth_router
from app.api.v1.routers.equipos import router as equipos_router
from app.api.v1.routers.health import router as health_router
from app.api.v1.routers.impersonation import router as impersonation_router
from app.api.v1.routers.padron import router as padron_router
from app.api.v1.routers.usuarios import router as usuarios_router

__all__ = [
    "admin_estructura_router",
    "asignaciones_router",
    "auth_router",
    "equipos_router",
    "health_router",
    "impersonation_router",
    "padron_router",
    "usuarios_router",
]
