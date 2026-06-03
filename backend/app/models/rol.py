"""Modelo Rol — tenant-specific role.

Cada rol pertenece a un tenant y agrupa un conjunto de permisos
a traves de la tabla rol_permiso.
"""

from sqlalchemy import Column, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import BaseMixin


class Rol(Base, BaseMixin):
    __tablename__ = "rol"

    codigo = Column(String(50), nullable=False)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(Text, nullable=True)

    rol_permisos = relationship("RolPermiso", back_populates="rol", passive_deletes=True)

    __table_args__ = (
        Index("ix_rol_tenant_id", "tenant_id"),
        UniqueConstraint("tenant_id", "codigo", name="uq_rol_tenant_codigo"),
        UniqueConstraint("tenant_id", "nombre", name="uq_rol_tenant_nombre"),
    )

    def __repr__(self) -> str:
        return (
            f"<Rol id={self.id} tenant_id={self.tenant_id} "
            f"codigo={self.codigo!r} nombre={self.nombre!r}>"
        )
