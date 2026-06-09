"""Modelo InstanciaEncuentro — encuentro concreto con estado propio.

Cada instancia representa una ocurrencia real de un encuentro sincrónico.
Puede originarse de un SlotEncuentro (slot_id no nulo) o ser independiente.
Cada instancia tiene estado propio (Programado/Realizado/Cancelado) independiente
del slot que la originó (RN-14).
"""

from __future__ import annotations

from sqlalchemy import Column, Date, Enum, ForeignKey, String, Text, Time
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.database import Base
from app.models.base import BaseMixin
from app.models.enums import EstadoEncuentro


class InstanciaEncuentro(Base, BaseMixin):
    __tablename__ = "instancia_encuentro"

    slot_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("slot_encuentro.id", ondelete="SET NULL"),
        nullable=True,
    )
    materia_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("materia.id", ondelete="SET NULL"),
        nullable=True,
    )
    fecha = Column(Date, nullable=False)
    hora = Column(Time(timezone=False), nullable=False)
    titulo = Column(String(200), nullable=False)
    estado = Column(
        Enum(EstadoEncuentro, name="estado_encuentro", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=EstadoEncuentro.PROGRAMADO,
        server_default="Programado",
    )
    meet_url = Column(String(500), nullable=True)
    video_url = Column(String(500), nullable=True)
    comentario = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<InstanciaEncuentro id={self.id} titulo={self.titulo!r} "
            f"fecha={self.fecha} estado={self.estado}>"
        )
