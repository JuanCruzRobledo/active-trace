"""Modelos MensajeHilo + Mensaje — mensajería interna entre usuarios (C-20).

MensajeHilo agrupa una conversación entre dos usuarios (usuario_a, usuario_b)
con un asunto. Hereda BaseMixin para soft-delete administrativo futuro.

Mensaje es append-only: id, tenant_id, hilo_id, autor_id, cuerpo, creado_at,
leido_at (nullable). Sin updated_at ni deleted_at — igual que ComentarioTarea.

El inbox de un usuario = hilos donde es usuario_a O usuario_b,
filtrados por tenant_id.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import BaseMixin


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MensajeHilo(Base, BaseMixin):
    """Hilo de mensajería interna entre dos usuarios del mismo tenant.

    Attributes:
        asunto: Asunto/título del hilo.
        usuario_a_id: FK del primer participante (quien inicia).
        usuario_b_id: FK del segundo participante (destinatario).
        mensajes: Relación uno-a-muchos con Mensaje.
    """

    __tablename__ = "mensaje_hilo"

    asunto = Column(String(255), nullable=False)
    usuario_a_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="CASCADE"),
        nullable=False,
    )
    usuario_b_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Relationships ──────────────────────────────────────────────────
    mensajes = relationship(
        "Mensaje",
        back_populates="hilo",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    usuario_a = relationship(
        "Usuario",
        foreign_keys=[usuario_a_id],
        lazy="selectin",
    )
    usuario_b = relationship(
        "Usuario",
        foreign_keys=[usuario_b_id],
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_mensaje_hilo_tenant_id", "tenant_id"),
        Index("ix_mensaje_hilo_usuario_a_id", "usuario_a_id"),
        Index("ix_mensaje_hilo_usuario_b_id", "usuario_b_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<MensajeHilo id={self.id} tenant_id={self.tenant_id} "
            f"asunto={self.asunto!r}>"
        )


class Mensaje(Base):
    """Mensaje individual dentro de un hilo — append-only.

    Solo almacena id, tenant_id, hilo_id, autor_id, cuerpo, creado_at,
    leido_at. Sin updated_at ni deleted_at (trazabilidad de conversaciones).

    Attributes:
        hilo_id: FK al MensajeHilo.
        autor_id: FK al Usuario que envió el mensaje.
        cuerpo: Contenido del mensaje.
        creado_at: Timestamp de creación (UTC).
        leido_at: Timestamp de lectura por el destinatario (nullable).
    """

    __tablename__ = "mensaje"

    id = Column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    tenant_id = Column(
        PGUUID(as_uuid=True),
        nullable=False,
    )
    hilo_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("mensaje_hilo.id", ondelete="CASCADE"),
        nullable=False,
    )
    autor_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="CASCADE"),
        nullable=False,
    )
    cuerpo = Column(Text, nullable=False)
    creado_at = Column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )
    leido_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ── Relationships ──────────────────────────────────────────────────
    hilo = relationship("MensajeHilo", back_populates="mensajes")
    autor = relationship(
        "Usuario",
        foreign_keys=[autor_id],
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_mensaje_tenant_id", "tenant_id"),
        Index("ix_mensaje_hilo_id", "hilo_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<Mensaje id={self.id} hilo_id={self.hilo_id} "
            f"autor_id={self.autor_id}>"
        )
