"""Modelo Guardia — registro de atención a alumnos (tutorías/consultas).

La guardia es una entidad independiente del módulo de encuentros (D4).
Representa un bloque de atención: un docente/tutor en un día y horario
específicos, con estado propio (Pendiente/Realizada/Cancelada).
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.database import Base
from app.models.base import BaseMixin
from app.models.enums import DiaSemana, EstadoGuardia


class Guardia(Base, BaseMixin):
    __tablename__ = "guardia"

    asignacion_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("asignacion.id", ondelete="SET NULL"),
        nullable=True,
    )
    materia_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("materia.id", ondelete="SET NULL"),
        nullable=True,
    )
    carrera_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("carrera.id", ondelete="SET NULL"),
        nullable=True,
    )
    cohorte_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("cohorte.id", ondelete="SET NULL"),
        nullable=True,
    )
    dia = Column(
        Enum(DiaSemana, name="dia_semana", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    horario = Column(String(50), nullable=False)
    estado = Column(
        Enum(EstadoGuardia, name="estado_guardia", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=EstadoGuardia.PENDIENTE,
        server_default="Pendiente",
    )
    comentarios = Column(Text, nullable=True)
    creada_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<Guardia id={self.id} dia={self.dia} "
            f"horario={self.horario!r} estado={self.estado}>"
        )
