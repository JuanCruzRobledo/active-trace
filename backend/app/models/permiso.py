"""Modelo Permiso — global permission catalog.

NO tiene tenant_id ni soft delete. El catalogo de permisos es unico
para todo el sistema.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Permiso(Base):
    __tablename__ = "permiso"

    id = Column(
        PGUUID(as_uuid=True),
        primary_key=True,
    )
    codigo = Column(String(100), nullable=False)
    descripcion = Column(String(255), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("codigo", name="uq_permiso_codigo"),
    )

    def __repr__(self) -> str:
        return (
            f"<Permiso id={self.id} codigo={self.codigo!r}>"
        )
