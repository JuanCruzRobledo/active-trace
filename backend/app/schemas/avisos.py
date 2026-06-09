"""Schemas Pydantic para el modulo de Avisos (C-15).

Todos los schemas usan ``extra='forbid'`` (REGLAS DURAS #5).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ── Aviso schemas ──────────────────────────────────────────────────────


class AvisoCreate(BaseModel):
    """Datos para crear un nuevo aviso institucional."""

    model_config = ConfigDict(extra="forbid")

    alcance: str
    materia_id: UUID | None = None
    cohorte_id: UUID | None = None
    rol_destino: str | None = None
    severidad: str
    titulo: str = Field(..., min_length=1, max_length=200)
    cuerpo: str = Field(..., min_length=1)
    inicio_en: datetime
    fin_en: datetime
    orden: int = Field(default=0, ge=0)
    requiere_ack: bool = False


class AvisoUpdate(BaseModel):
    """Datos para actualizar un aviso existente."""

    model_config = ConfigDict(extra="forbid")

    alcance: str | None = None
    materia_id: UUID | None = None
    cohorte_id: UUID | None = None
    rol_destino: str | None = None
    severidad: str | None = None
    titulo: str | None = Field(None, min_length=1, max_length=200)
    cuerpo: str | None = Field(None, min_length=1)
    inicio_en: datetime | None = None
    fin_en: datetime | None = None
    orden: int | None = Field(None, ge=0)
    activo: bool | None = None
    requiere_ack: bool | None = None


class AvisoResponse(BaseModel):
    """Respuesta completa de un aviso con metricas de tracking."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    alcance: str
    materia_id: UUID | None = None
    cohorte_id: UUID | None = None
    rol_destino: str | None = None
    severidad: str
    titulo: str
    cuerpo: str
    inicio_en: datetime
    fin_en: datetime
    orden: int
    activo: bool
    requiere_ack: bool
    created_at: str | None = None
    updated_at: str | None = None
    total_ack: int = 0
    total_usuarios_alcance: int = 0
    porcentaje_ack: float = 0.0


# ── Acknowledgment schemas ─────────────────────────────────────────────


class AcknowledgmentCreate(BaseModel):
    """Datos para confirmar lectura de un aviso."""

    model_config = ConfigDict(extra="forbid")

    aviso_id: UUID


class AcknowledgmentResponse(BaseModel):
    """Respuesta de un acknowledgment."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    aviso_id: UUID
    usuario_id: UUID
    confirmado_at: datetime
    usuario_nombre: str | None = None
    usuario_email: str | None = None


# ── List/Tracking schemas ──────────────────────────────────────────────


class AvisoTimelineItem(BaseModel):
    """Item de la timeline de avisos para un usuario."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    alcance: str
    severidad: str
    titulo: str
    cuerpo: str
    inicio_en: datetime
    fin_en: datetime
    orden: int
    requiere_ack: bool
    acknowledged: bool = False
    created_at: str | None = None


class AvisoTimelineResponse(BaseModel):
    """Timeline de avisos activos para el usuario autenticado."""

    model_config = ConfigDict(extra="forbid")

    items: list[AvisoTimelineItem]
    total: int


class TrackingAckItem(BaseModel):
    """Item del tracking de acknowledgments."""

    model_config = ConfigDict(extra="forbid")

    usuario_id: UUID
    usuario_nombre: str | None = None
    confirmado_at: datetime | None = None


class TrackingAvisoResponse(BaseModel):
    """Tracking de acknowledgments de un aviso."""

    model_config = ConfigDict(extra="forbid")

    total_usuarios: int = 0
    total_ack: int = 0
    porcentaje: float = 0.0
    acknowledgments: list[TrackingAckItem] = []
