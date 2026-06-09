"""Modelo Cohorte — camada/ingreso de estudiantes dentro de una carrera.

Cada cohorte pertenece a un tenant y esta vinculada a una carrera.
El nombre es unico dentro de (tenant_id, carrera_id).
"""

from sqlalchemy import Column, Date, ForeignKey, Index, Integer, String, text

from app.core.database import Base
from app.models.base import BaseMixin


class Cohorte(Base, BaseMixin):
    __tablename__ = "cohorte"

    carrera_id = Column(
        ForeignKey("carrera.id", ondelete="CASCADE"),
        nullable=False,
    )
    nombre = Column(String(100), nullable=False)
    anio = Column(Integer, nullable=False)
    vig_desde = Column(Date, nullable=False)
    vig_hasta = Column(Date, nullable=True)
    estado = Column(String(20), nullable=False, default="Activa")

    __table_args__ = (
        Index("ix_cohorte_tenant_id", "tenant_id"),
        Index("ix_cohorte_carrera_id", "carrera_id"),
        Index(
            "uq_cohorte_tenant_carrera_nombre_active",
            "tenant_id",
            "carrera_id",
            "nombre",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Cohorte id={self.id} tenant_id={self.tenant_id} "
            f"carrera_id={self.carrera_id} nombre={self.nombre!r} "
            f"anio={self.anio} estado={self.estado!r}>"
        )
