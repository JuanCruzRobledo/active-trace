"""Modelos del dominio.

Importar este paquete fuerza la registración de todas las tablas en
``Base.metadata`` (necesario para ``alembic`` autogenerate y para
``Base.metadata.create_all`` en tests).
"""

from app.models.audit_log import AuditLog
from app.models.base import BaseMixin
from app.models.carrera import Carrera
from app.models.cohorte import Cohorte
from app.models.materia import Materia
from app.models.password_reset_token import PasswordResetToken
from app.models.permiso import Permiso
from app.models.refresh_token import RefreshToken
from app.models.rol import Rol
from app.models.rol_permiso import RolPermiso
from app.models.tenant import Tenant
from app.models.user_rol import UserRol
from app.models.two_factor_challenge import TwoFactorChallenge
from app.models.user import User
from app.models.usuario import Usuario
from app.models.asignacion import Asignacion

__all__ = [
    "Asignacion",
    "AuditLog",
    "BaseMixin",
    "Carrera",
    "Cohorte",
    "Materia",
    "PasswordResetToken",
    "Permiso",
    "RefreshToken",
    "Rol",
    "RolPermiso",
    "Tenant",
    "Usuario",
    "UserRol",
    "TwoFactorChallenge",
    "User",
]
