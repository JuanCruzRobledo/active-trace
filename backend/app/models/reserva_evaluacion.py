"""Modelo ReservaEvaluacion — reserva de turno de un alumno en una evaluacion.

Cada reserva vincula un alumno a una evaluacion en una fecha_hora especifica.
El estado controla si la reserva esta Activa o Cancelada. Al crear una reserva
se verifica el cupo disponible de forma atomica.
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.database import Base
from app.models.base import BaseMixin
from app.models.enums import EstadoReserva


class ReservaEvaluacion(Base, BaseMixin):
    __tablename__ = "reserva_evaluacion"

    evaluacion_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("evaluacion.id", ondelete="CASCADE"),
        nullable=False,
    )
    alumno_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="CASCADE"),
        nullable=False,
    )
    fecha_hora = Column(DateTime(timezone=True), nullable=False)
    estado = Column(
        Enum(EstadoReserva, name="estado_reserva", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=EstadoReserva.ACTIVA,
    )

    def __repr__(self) -> str:
        return (
            f"<ReservaEvaluacion id={self.id} alumno_id={self.alumno_id} "
            f"estado={self.estado}>"
        )
