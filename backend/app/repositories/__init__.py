"""Repositorios del dominio — acceso a datos con scope de tenant obligatorio."""

from app.repositories.base import BaseRepository
from app.repositories.carrera_repository import CarreraRepository
from app.repositories.cohorte_repository import CohorteRepository
from app.repositories.materia_repository import MateriaRepository
from app.repositories.password_reset_token_repository import PasswordResetTokenRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.two_factor_challenge_repository import TwoFactorChallengeRepository
from app.repositories.user_repository import UserRepository

__all__ = [
    "BaseRepository",
    "CarreraRepository",
    "CohorteRepository",
    "MateriaRepository",
    "PasswordResetTokenRepository",
    "RefreshTokenRepository",
    "TwoFactorChallengeRepository",
    "UserRepository",
]
