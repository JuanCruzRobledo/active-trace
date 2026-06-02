"""Modelos del dominio.

Importar este paquete fuerza la registración de todas las tablas en
``Base.metadata`` (necesario para ``alembic`` autogenerate y para
``Base.metadata.create_all`` en tests).
"""

from app.models.base import BaseMixin
from app.models.password_reset_token import PasswordResetToken
from app.models.refresh_token import RefreshToken
from app.models.tenant import Tenant
from app.models.two_factor_challenge import TwoFactorChallenge
from app.models.user import User

__all__ = [
    "BaseMixin",
    "PasswordResetToken",
    "RefreshToken",
    "Tenant",
    "TwoFactorChallenge",
    "User",
]
