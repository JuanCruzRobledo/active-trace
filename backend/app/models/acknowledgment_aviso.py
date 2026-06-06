"""Modelo AcknowledgmentAviso — acuse de recibo de un aviso (C-15).

Cada registro representa la confirmacion explicita de un usuario
de haber leido un aviso que requiere acuse (requiere_ack = true).
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.database import Base
from app.models.base import BaseMixin


class AcknowledgmentAviso(Base, BaseMixin):
    __tablename__ = "acknowledgment_aviso"

    aviso_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("aviso.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    usuario_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="CASCADE"),
        nullable=False,
    )
    confirmado_at = Column(
        DateTime(timezone=True), nullable=False, default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "aviso_id", "usuario_id", name="uq_acknowledgment_aviso_usuario"
        ),
        {"extend_existing": True},
    )

    def __repr__(self) -> str:
        return (
            f"<AcknowledgmentAviso id={self.id} "
            f"aviso_id={self.aviso_id} usuario_id={self.usuario_id}>"
        )
