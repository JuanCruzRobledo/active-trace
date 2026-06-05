"""Modelo Comunicacion — comunicaciones masivas con destinatario cifrado y ciclo de estados.

El modelo sigue el patrón BaseMixin de todo el dominio:
- ``id`` (UUID PK), ``tenant_id`` (UUID, índice), timestamps, soft delete.
- ``destinatario`` cifrado con AES-256 vía ``EncryptedColumn``.
- ``estado`` enum: Pendiente → Enviando → Enviado/Error/Cancelado.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.encryption import EncryptedColumn
from app.models.base import BaseMixin


class EstadoComunicacion(str, enum.Enum):
    Pendiente = "Pendiente"
    Enviando = "Enviando"
    Enviado = "Enviado"
    Error = "Error"
    Cancelado = "Cancelado"


class Comunicacion(Base, BaseMixin):
    """Comunicación masiva con destinatario cifrado y trazabilidad de envío.

    Attributes:
        enviado_por_id: Usuario que creó la comunicación.
        materia_id: Materia asociada (opcional).
        destinatario: Email del destinatario, cifrado AES-256 en reposo.
        asunto: Asunto del mensaje.
        cuerpo: Cuerpo del mensaje.
        estado: Estado actual del ciclo de vida.
        lote_id: UUID que agrupa comunicaciones de un mismo envío masivo.
        enviado_at: Momento en que el worker marcó como Enviado.
    """

    __tablename__ = "comunicaciones"

    enviado_por_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="SET NULL"),
        nullable=False,
    )
    materia_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("materia.id", ondelete="SET NULL"),
        nullable=True,
    )
    destinatario = Column(
        EncryptedColumn(key="placeholder_for_comunicaciones_destinatario"),
        nullable=False,
    )
    asunto = Column(String(200), nullable=False)
    cuerpo = Column(Text, nullable=False)
    estado = Column(
        Enum(EstadoComunicacion),
        nullable=False,
        default=EstadoComunicacion.Pendiente,
        server_default="Pendiente",
    )
    lote_id = Column(
        PGUUID(as_uuid=True),
        nullable=False,
        default=uuid4,
    )
    enviado_at = Column(DateTime(timezone=True), nullable=True)
    necesita_aprobacion = Column(
        PGUUID(as_uuid=True),
        nullable=True,
    )
    aprobado_at = Column(DateTime(timezone=True), nullable=True)
    aprobado_por_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Relationships ────────────────────────────────────────────────

    remitente = relationship(
        "Usuario", foreign_keys=[enviado_por_id], lazy="selectin"
    )
    aprobador = relationship(
        "Usuario", foreign_keys=[aprobado_por_id], lazy="selectin"
    )
