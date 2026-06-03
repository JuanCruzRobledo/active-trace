"""API v1 routers package."""

from app.api.v1.routers.admin_estructura import router as admin_estructura_router
from app.api.v1.routers.auth import router as auth_router
from app.api.v1.routers.health import router as health_router
from app.api.v1.routers.impersonation import router as impersonation_router

__all__ = [
    "admin_estructura_router",
    "auth_router",
    "health_router",
    "impersonation_router",
]
