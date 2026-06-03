"""Modelo RolPermiso — tenant-scoped role-permission matrix.

NO tiene updated_at ni deleted_at (es datos de configuracion).
"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RolPermiso(Base):
    __tablename__ = "rol_permiso"

    id = Column(
        PGUUID(as_uuid=True),
        primary_key=True,
    )
    tenant_id = Column(
        PGUUID(as_uuid=True),
        nullable=False,
    )
    rol_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("rol.id", ondelete="CASCADE"),
        nullable=False,
    )
    permiso_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("permiso.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )

    rol = relationship("Rol", back_populates="rol_permisos")
    permiso = relationship("Permiso")

    __table_args__ = (
        Index("ix_rol_permiso_tenant_id", "tenant_id"),
        Index("ix_rol_permiso_rol_id", "rol_id"),
        Index("ix_rol_permiso_permiso_id", "permiso_id"),
        UniqueConstraint(
            "tenant_id", "rol_id", "permiso_id",
            name="uq_rol_permiso_tenant_rol_permiso",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<RolPermiso id={self.id} tenant_id={self.tenant_id} "
            f"rol_id={self.rol_id} permiso_id={self.permiso_id}>"
        )
