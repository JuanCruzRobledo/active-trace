"""Modelo Evaluacion — convocatoria de evaluacion formal (coloquio, parcial, etc.).

Cada Evaluacion representa una convocatoria a una instancia de evaluacion
(parcial, TP, coloquio o recuperatorio) con dias disponibles y cupos por dia.
Los alumnos pueden reservar turnos dentro de la ventana definida.
"""

from __future__ import annotations

from sqlalchemy import Column, Date, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.database import Base
from app.models.base import BaseMixin
from app.models.enums import EstadoEvaluacion, TipoEvaluacion


class Evaluacion(Base, BaseMixin):
    __tablename__ = "evaluacion"

    materia_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("materia.id", ondelete="CASCADE"),
        nullable=False,
    )
    cohorte_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("cohorte.id", ondelete="CASCADE"),
        nullable=False,
    )
    tipo = Column(
        Enum(TipoEvaluacion, name="tipo_evaluacion", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    instancia = Column(String(200), nullable=False)
    dias_disponibles = Column(Integer, nullable=False, default=1)
    cupos_por_dia = Column(Integer, nullable=False, default=1)
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=False)
    estado = Column(
        Enum(EstadoEvaluacion, name="estado_evaluacion", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=EstadoEvaluacion.ACTIVA,
    )

    def __repr__(self) -> str:
        return (
            f"<Evaluacion id={self.id} tipo={self.tipo} "
            f"instancia={self.instancia!r} estado={self.estado}>"
        )
