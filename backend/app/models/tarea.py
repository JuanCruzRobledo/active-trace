"""Modelo Tarea — tarea interna asignable con trazabilidad (C-16).

Cada Tarea representa una accion interna asignada a un miembro del equipo
docente. Soporta un workflow de estados (Pendiente → En progreso → Resuelta
| Cancelada), materia opcional y comentarios asincronicos.

ComentarioTarea es append-only: solo almacena id, tenant_id, tarea_id,
autor_id, texto y creado_at. No tiene updated_at ni deleted_at.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import BaseMixin
from app.models.enums import EstadoTarea


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Tarea(Base, BaseMixin):
    __tablename__ = "tarea"

    materia_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("materia.id", ondelete="SET NULL"),
        nullable=True,
    )
    asignado_a = Column(
        PGUUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="CASCADE"),
        nullable=False,
    )
    asignado_por = Column(
        PGUUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="SET NULL"),
        nullable=False,
    )
    estado = Column(
        Enum(
            EstadoTarea,
            name="estado_tarea",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=EstadoTarea.PENDIENTE,
    )
    descripcion = Column(Text, nullable=False)
    contexto_id = Column(PGUUID(as_uuid=True), nullable=True)

    # ── Relationships ──────────────────────────────────────────────────
    comentarios = relationship(
        "ComentarioTarea",
        back_populates="tarea",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    asignado = relationship(
        "Usuario",
        foreign_keys=[asignado_a],
        lazy="selectin",
    )
    asignador = relationship(
        "Usuario",
        foreign_keys=[asignado_por],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<Tarea id={self.id} estado={self.estado} "
            f"asignado_a={self.asignado_a}>"
        )


class ComentarioTarea(Base):
    """Comentario asincronico en una tarea — append-only.

    Solo almacena id, tenant_id, tarea_id, autor_id, texto y creado_at.
    Sin updated_at ni deleted_at (escribir una vez, leer muchas).
    """

    __tablename__ = "comentario_tarea"

    id = Column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    tenant_id = Column(
        PGUUID(as_uuid=True),
        nullable=False,
    )
    tarea_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("tarea.id", ondelete="CASCADE"),
        nullable=False,
    )
    autor_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="CASCADE"),
        nullable=False,
    )
    texto = Column(Text, nullable=False)
    creado_at = Column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )

    # ── Relationships ──────────────────────────────────────────────────
    tarea = relationship("Tarea", back_populates="comentarios")
    autor = relationship(
        "Usuario",
        foreign_keys=[autor_id],
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_comentario_tarea_tenant_id", "tenant_id"),
        Index("ix_comentario_tarea_tarea_id", "tarea_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<ComentarioTarea id={self.id} tarea_id={self.tarea_id} "
            f"autor_id={self.autor_id}>"
        )
