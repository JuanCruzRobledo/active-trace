"""Modelo Carrera — programa académico del tenant.

Cada carrera pertenece a un tenant y tiene un codigo unico dentro del mismo.
Una carrera inactiva no admite cohortes abiertas.
"""

from sqlalchemy import Column, Index, Integer, String, text

from app.core.database import Base
from app.models.base import BaseMixin


class Carrera(Base, BaseMixin):
    __tablename__ = "carrera"

    codigo = Column(String(50), nullable=False)
    nombre = Column(String(200), nullable=False)
    estado = Column(String(20), nullable=False, default="Activa")

    __table_args__ = (
        Index("ix_carrera_tenant_id", "tenant_id"),
        Index(
            "uq_carrera_tenant_codigo_active",
            "tenant_id",
            "codigo",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Carrera id={self.id} tenant_id={self.tenant_id} "
            f"codigo={self.codigo!r} nombre={self.nombre!r} "
            f"estado={self.estado!r}>"
        )
