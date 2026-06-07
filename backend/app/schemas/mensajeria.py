"""Schemas Pydantic para el modulo de mensajeria interna (C-20).

HiloCreate: crear un nuevo hilo con primer mensaje.
MensajeCreate: responder en un hilo existente.
MensajeResponse / HiloResponse / HiloConMensajesResponse / HiloListResponse: lectura.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class HiloCreate(BaseModel):
    """Body para POST /api/inbox — crear hilo con primer mensaje."""

    destinatario_id: UUID
    asunto: str
    cuerpo: str

    model_config = ConfigDict(extra="forbid")


class MensajeCreate(BaseModel):
    """Body para POST /api/inbox/{id}/mensajes — responder en un hilo."""

    cuerpo: str

    model_config = ConfigDict(extra="forbid")


class MensajeResponse(BaseModel):
    """Mensaje individual dentro de un hilo."""

    id: UUID
    hilo_id: UUID
    autor_id: UUID
    cuerpo: str
    creado_at: datetime
    leido_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class ParticipanteResponse(BaseModel):
    """Participante del hilo con nombre enmascarado."""

    id: UUID
    nombre: str
    apellidos: str

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class HiloResponse(BaseModel):
    """Hilo en el listado del inbox — sin mensajes completos."""

    id: UUID
    tenant_id: UUID
    asunto: str
    usuario_a_id: UUID
    usuario_b_id: UUID
    tiene_no_leidos: bool = False
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class HiloConMensajesResponse(BaseModel):
    """Hilo completo con todos sus mensajes (GET /api/inbox/{id})."""

    id: UUID
    tenant_id: UUID
    asunto: str
    usuario_a_id: UUID
    usuario_b_id: UUID
    mensajes: list[MensajeResponse] = []
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class HiloListResponse(BaseModel):
    """Respuesta paginada de GET /api/inbox."""

    items: list[HiloResponse]
    total: int

    model_config = ConfigDict(extra="forbid")
