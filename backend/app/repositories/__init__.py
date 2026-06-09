"""Repositorios del dominio — acceso a datos con scope de tenant obligatorio."""

from app.repositories.base import BaseRepository
from app.repositories.carrera_repository import CarreraRepository
from app.repositories.cohorte_repository import CohorteRepository
from app.repositories.entrada_padron_repository import EntradaPadronRepository
from app.repositories.materia_repository import MateriaRepository
from app.repositories.password_reset_token_repository import PasswordResetTokenRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.two_factor_challenge_repository import TwoFactorChallengeRepository
from app.repositories.user_repository import UserRepository
from app.repositories.calificacion_repository import CalificacionRepository
from app.repositories.umbral_materia_repository import UmbralMateriaRepository
from app.repositories.version_padron_repository import VersionPadronRepository

__all__ = [
    "BaseRepository",
    "CalificacionRepository",
    "CarreraRepository",
    "CohorteRepository",
    "EntradaPadronRepository",
    "MateriaRepository",
    "VersionPadronRepository",
    "PasswordResetTokenRepository",
    "RefreshTokenRepository",
    "TwoFactorChallengeRepository",
    "UmbralMateriaRepository",
    "UserRepository",
]
