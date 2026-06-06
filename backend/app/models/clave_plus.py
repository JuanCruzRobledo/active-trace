"""Modelo ClavePlus — catálogo configurable de claves de plus salarial.

Cada tenant define sus propias claves (PROG, BD, ING, MAT, RED, WEB, GES, IDI, PRA, etc.).
Las materias se vinculan a una clave via ``clave_plus_id``.

Relaciones:
    - ``Materia.clave_plus_id`` → FK nullable a este modelo.
"""

from sqlalchemy import Boolean, Column, Index, String, text

from app.core.database import Base
from app.models.base import BaseMixin


class ClavePlus(Base, BaseMixin):
    __tablename__ = "clave_plus"

    codigo = Column(String(20), nullable=False)
    nombre = Column(String(200), nullable=False)
    activa = Column(Boolean, nullable=False, default=True)

    __table_args__ = (
        Index("ix_clave_plus_tenant_id", "tenant_id"),
        Index(
            "uq_clave_plus_tenant_codigo_active",
            "tenant_id",
            "codigo",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<ClavePlus id={self.id} tenant_id={self.tenant_id} "
            f"codigo={self.codigo!r} nombre={self.nombre!r} "
            f"activa={self.activa}>"
        )
