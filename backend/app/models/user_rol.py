"""Modelo UserRol — asociación usuario ↔ rol (tenant-scoped).

Cada fila asigna un usuario a un rol dentro de un tenant.
Es inmutable (no tiene updated_at ni deleted_at) porque la
asignación es un hecho consumado — si se revoca, se borra la fila.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserRol(Base):
    __tablename__ = "user_rol"

    id = Column(
        PGUUID(as_uuid=True),
        primary_key=True,
    )
    user_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    rol_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("rol.id", ondelete="CASCADE"),
        nullable=False,
    )
    tenant_id = Column(
        PGUUID(as_uuid=True),
        nullable=False,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )

    user = relationship("User")
    rol = relationship("Rol")

    __table_args__ = (
        Index("ix_user_rol_tenant_id", "tenant_id"),
        Index("ix_user_rol_user_id", "user_id"),
        Index("ix_user_rol_rol_id", "rol_id"),
        UniqueConstraint(
            "user_id", "rol_id",
            name="uq_user_rol_user_rol",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<UserRol id={self.id} user_id={self.user_id} "
            f"rol_id={self.rol_id} tenant_id={self.tenant_id}>"
        )
