"""Modelo Aviso — notificacion institucional segmentable (C-15).

Cada Aviso representa una comunicacion institucional con alcance,
severidad, vigencia programada y opcion de requerir acuse de recibo.
La audiencia se define mediante alcance + contexto (materia/cohorte/rol).
"""

from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.database import Base
from app.models.base import BaseMixin
from app.models.enums import AlcanceAviso, SeveridadAviso


class Aviso(Base, BaseMixin):
    __tablename__ = "aviso"

    alcance = Column(
        Enum(AlcanceAviso, name="alcance_aviso", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    materia_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("materia.id", ondelete="SET NULL"),
        nullable=True,
    )
    cohorte_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("cohorte.id", ondelete="SET NULL"),
        nullable=True,
    )
    rol_destino = Column(String(50), nullable=True)
    severidad = Column(
        Enum(SeveridadAviso, name="severidad_aviso", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    titulo = Column(String(200), nullable=False)
    cuerpo = Column(Text, nullable=False)
    inicio_en = Column(DateTime(timezone=True), nullable=False)
    fin_en = Column(DateTime(timezone=True), nullable=False)
    orden = Column(Integer, nullable=False, default=0)
    activo = Column(Boolean, nullable=False, default=True)
    requiere_ack = Column(Boolean, nullable=False, default=False)

    def __repr__(self) -> str:
        return (
            f"<Aviso id={self.id} titulo={self.titulo!r} "
            f"alcance={self.alcance} severidad={self.severidad}>"
        )
