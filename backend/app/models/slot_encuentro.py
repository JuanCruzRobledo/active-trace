"""Modelo SlotEncuentro — plantilla de recurrencia semanal de encuentros sincrónicos.

Cada slot define un encuentro que se repite semanalmente (dia_semana + hora)
durante una cantidad de semanas (cant_semanas) a partir de una fecha_inicio.
Soporta también modo "único" mediante fecha_unica (excluyente con cant_semanas).
"""

from __future__ import annotations

from sqlalchemy import Column, Date, Enum, ForeignKey, Integer, String, Time
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.database import Base
from app.models.base import BaseMixin
from app.models.enums import DiaSemana


class SlotEncuentro(Base, BaseMixin):
    __tablename__ = "slot_encuentro"

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
    titulo = Column(String(200), nullable=False)
    hora = Column(Time(timezone=False), nullable=False)
    dia_semana = Column(
        Enum(DiaSemana, name="dia_semana", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    fecha_inicio = Column(Date, nullable=False)
    cant_semanas = Column(Integer, nullable=False, default=0)
    fecha_unica = Column(Date, nullable=True)
    meet_url = Column(String(500), nullable=True)
    vig_desde = Column(Date, nullable=True)
    vig_hasta = Column(Date, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<SlotEncuentro id={self.id} titulo={self.titulo!r} "
            f"dia={self.dia_semana} hora={self.hora}>"
        )
