"""Schemas Pydantic para el módulo de Encuentros (C-13).

Todos los schemas usan ``extra='forbid'`` (REGLAS DURAS #5).
"""

from __future__ import annotations

from datetime import date, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ── Slot schemas ──────────────────────────────────────────────────────


class SlotEncuentroCreate(BaseModel):
    """Modo recurrente: genera N instancias semanales."""

    model_config = ConfigDict(extra="forbid")

    materia_id: UUID
    titulo: str = Field(..., min_length=1, max_length=200)
    hora: time
    dia_semana: str
    fecha_inicio: date
    cant_semanas: int = Field(..., ge=1)
    meet_url: str | None = None


class SlotEncuentroCreateUnico(BaseModel):
    """Modo único: genera 1 instancia con fecha_unica."""

    model_config = ConfigDict(extra="forbid")

    materia_id: UUID
    titulo: str = Field(..., min_length=1, max_length=200)
    hora: time
    fecha_unica: date
    meet_url: str | None = None


class SlotEncuentroUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titulo: str | None = Field(None, min_length=1, max_length=200)
    hora: time | None = None
    meet_url: str | None = None


class SlotEncuentroResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    materia_id: UUID | None = None
    titulo: str
    hora: time
    dia_semana: str
    fecha_inicio: date
    cant_semanas: int
    fecha_unica: date | None = None
    meet_url: str | None = None
    vig_desde: date | None = None
    vig_hasta: date | None = None
    created_at: str | None = None
    updated_at: str | None = None
    cantidad_instancias: int = 0


# ── Instancia schemas ─────────────────────────────────────────────────


class InstanciaEncuentroCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    materia_id: UUID
    titulo: str = Field(..., min_length=1, max_length=200)
    fecha: date
    hora: time
    meet_url: str | None = None


class InstanciaEncuentroUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    estado: str | None = None
    meet_url: str | None = None
    video_url: str | None = None
    comentario: str | None = None


class InstanciaEncuentroResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    slot_id: UUID | None = None
    materia_id: UUID | None = None
    fecha: date
    hora: time
    titulo: str
    estado: str
    meet_url: str | None = None
    video_url: str | None = None
    comentario: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    # Datos del slot (si aplica)
    slot_titulo: str | None = None


# ── Response wrappers ─────────────────────────────────────────────────


class ExportarAulaResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    html: str


class EncuentroListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list
    total: int
