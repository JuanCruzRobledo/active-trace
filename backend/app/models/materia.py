"""Modelo Materia — catalogo unico de materias del tenant.

Segun ADR-006, Materia es la definicion unica en el catalogo del tenant;
la instancia concreta (Dictado) en una carrera x cohorte se modela aparte
en changes posteriores (C-07+).
"""

from sqlalchemy import Column, ForeignKey, Index, String, text

from app.core.database import Base
from app.models.base import BaseMixin


class Materia(Base, BaseMixin):
    __tablename__ = "materia"

    codigo = Column(String(50), nullable=False)
    nombre = Column(String(200), nullable=False)
    estado = Column(String(20), nullable=False, default="Activa")
    clave_plus_id = Column(
        ForeignKey("clave_plus.id", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (
        Index("ix_materia_tenant_id", "tenant_id"),
        Index(
            "uq_materia_tenant_codigo_active",
            "tenant_id",
            "codigo",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Materia id={self.id} tenant_id={self.tenant_id} "
            f"codigo={self.codigo!r} nombre={self.nombre!r} "
            f"estado={self.estado!r}>"
        )
