"""Modelos del dominio.

Importar este paquete fuerza la registración de todas las tablas en
``Base.metadata`` (necesario para ``alembic`` autogenerate y para
``Base.metadata.create_all`` en tests).
"""

from app.models.audit_log import AuditLog
from app.models.base import BaseMixin
from app.models.calificacion import Calificacion
from app.models.carrera import Carrera
from app.models.cohorte import Cohorte
from app.models.comunicacion import Comunicacion, EstadoComunicacion
from app.models.enums import (
    DiaSemana,
    EstadoEncuentro,
    EstadoGuardia,
    EstadoEvaluacion,
    EstadoReserva,
    TipoEvaluacion,
    AlcanceAviso,
    SeveridadAviso,
)
from app.models.materia import Materia
from app.models.password_reset_token import PasswordResetToken
from app.models.permiso import Permiso
from app.models.refresh_token import RefreshToken
from app.models.rol import Rol
from app.models.rol_permiso import RolPermiso
from app.models.tenant import Tenant
from app.models.umbral_materia import UmbralMateria
from app.models.user_rol import UserRol
from app.models.two_factor_challenge import TwoFactorChallenge
from app.models.user import User
from app.models.usuario import Usuario
from app.models.asignacion import Asignacion
from app.models.version_padron import VersionPadron
from app.models.entrada_padron import EntradaPadron
from app.models.slot_encuentro import SlotEncuentro
from app.models.instancia_encuentro import InstanciaEncuentro
from app.models.guardia import Guardia
from app.models.evaluacion import Evaluacion
from app.models.reserva_evaluacion import ReservaEvaluacion
from app.models.resultado_evaluacion import ResultadoEvaluacion
from app.models.aviso import Aviso
from app.models.acknowledgment_aviso import AcknowledgmentAviso

__all__ = [
    "AcknowledgmentAviso",
    "AlcanceAviso",
    "Asignacion",
    "AuditLog",
    "Aviso",
    "BaseMixin",
    "Calificacion",
    "Carrera",
    "Cohorte",
    "Comunicacion",
    "EntradaPadron",
    "EstadoComunicacion",
    "EstadoEncuentro",
    "EstadoGuardia",
    "EstadoEvaluacion",
    "EstadoReserva",
    "DiaSemana",
    "Evaluacion",
    "Guardia",
    "InstanciaEncuentro",
    "Materia",
    "ReservaEvaluacion",
    "ResultadoEvaluacion",
    "SeveridadAviso",
    "SlotEncuentro",
    "TipoEvaluacion",
    "VersionPadron",
    "PasswordResetToken",
    "Permiso",
    "RefreshToken",
    "Rol",
    "RolPermiso",
    "Tenant",
    "Usuario",
    "UmbralMateria",
    "UserRol",
    "TwoFactorChallenge",
    "User",
]
