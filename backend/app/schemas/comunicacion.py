"""Schemas Pydantic para el módulo de comunicaciones (C-12).

Todos los schemas usan ``extra='forbid'`` (REGLAS DURAS #5).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ── Request schemas ────────────────────────────────────────────────


class DestinatarioItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo: str = Field(..., description="Tipo de destinatario: email, usuario_id")
    valor: str = Field(..., description="Valor del destinatario")


class PreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asunto: str = Field(..., min_length=1, max_length=200)
    cuerpo: str = Field(..., min_length=1)
    destinatarios: list[DestinatarioItem] = Field(..., min_length=1)


class EnvioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preview_token: str
    asunto: str = Field(..., min_length=1, max_length=200)
    cuerpo: str = Field(..., min_length=1)
    materia_id: UUID
    destinatarios: list[DestinatarioItem] = Field(..., min_length=1)
    acepta_terminos: bool = True
    requiere_aprobacion: bool = False


class EnvioIndividualRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preview_token: str
    asunto: str = Field(..., min_length=1, max_length=200)
    cuerpo: str = Field(..., min_length=1)
    materia_id: UUID
    entrada_padron_id: UUID
    acepta_terminos: bool = True


class AprobarRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accion: str = Field(..., pattern=r"^(aprobar|rechazar)$")


# ── Response schemas ───────────────────────────────────────────────


class PreviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preview_token: str
    preview_html: str
    cantidad_destinatarios: int


class ComunicacionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    estado: str
    destinatario: str
    asunto: str
    enviado_at: datetime | None = None


class LoteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lote_id: UUID
    estado: str
    total: int
    enviados: int = 0
    fallidos: int = 0
    cancelados: int = 0
    pendientes: int = 0
    necesita_aprobacion: bool = False


class MisEnviosItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lote_id: UUID
    materia_nombre: str | None = None
    created_at: datetime
    total: int
    estado: str


class MisEnviosResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[MisEnviosItem]
    total: int
    pagina: int


class CancelarResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    comunicacion_id: UUID
    estado: str


class EnvioResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lote_id: UUID
    estado: str
    total_mensajes: int
    requiere_aprobacion: bool = False


class EnvioIndividualResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    comunicacion_id: UUID
    estado: str
