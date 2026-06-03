"""Modelos del dominio.

Importar este paquete fuerza la registración de todas las tablas en
``Base.metadata`` (necesario para ``alembic`` autogenerate y para
``Base.metadata.create_all`` en tests).
"""

from app.models.base import BaseMixin
from app.models.password_reset_token import PasswordResetToken
from app.models.permiso import Permiso
from app.models.refresh_token import RefreshToken
from app.models.rol import Rol
from app.models.rol_permiso import RolPermiso
from app.models.tenant import Tenant
from app.models.user_rol import UserRol
from app.models.two_factor_challenge import TwoFactorChallenge
from app.models.user import User

__all__ = [
    "BaseMixin",
    "PasswordResetToken",
    "Permiso",
    "RefreshToken",
    "Rol",
    "RolPermiso",
    "Tenant",
    "UserRol",
    "TwoFactorChallenge",
    "User",
]
