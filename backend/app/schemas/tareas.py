"""Schemas Pydantic para el modulo de tareas internas (C-16).

Define los contratos de request/response para la API REST de tareas
y comentarios. Todos los schemas usan ``extra='forbid'``.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# ── Tarea ──────────────────────────────────────────────────────────────────


class TareaCreate(BaseModel):
    """Schema para crear una tarea interna.

    Attributes:
        materia_id: UUID de la materia asociada (opcional).
        asignado_a: UUID del usuario asignado.
        descripcion: Descripcion textual de la tarea.
        contexto_id: UUID de contexto polimorfico (opcional, sin FK).
    """

    materia_id: UUID | None = None
    asignado_a: UUID
    descripcion: str
    contexto_id: UUID | None = None

    model_config = ConfigDict(extra="forbid")


class TareaUpdate(BaseModel):
    """Schema para actualizar una tarea (todos los campos opcionales)."""

    materia_id: UUID | None = None
    descripcion: str | None = None
    contexto_id: UUID | None = None

    model_config = ConfigDict(extra="forbid")


class TareaEstadoUpdate(BaseModel):
    """Schema para cambiar el estado de una tarea."""

    nuevo_estado: str

    model_config = ConfigDict(extra="forbid")


class TareaResponse(BaseModel):
    """Schema de respuesta para una tarea."""

    id: UUID
    tenant_id: UUID
    materia_id: UUID | None = None
    asignado_a: UUID
    asignado_por: UUID
    estado: str
    descripcion: str
    contexto_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True, extra="forbid")


# ── Comentario ─────────────────────────────────────────────────────────────


class ComentarioCreate(BaseModel):
    """Schema para crear un comentario en una tarea."""

    texto: str

    model_config = ConfigDict(extra="forbid")


class ComentarioResponse(BaseModel):
    """Schema de respuesta para un comentario."""

    id: UUID
    tarea_id: UUID
    autor_id: UUID
    texto: str
    creado_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True, extra="forbid")


# ── Compuestos ─────────────────────────────────────────────────────────────


class TareaConComentariosResponse(BaseModel):
    """Schema de respuesta para una tarea con sus comentarios."""

    id: UUID
    tenant_id: UUID
    materia_id: UUID | None = None
    asignado_a: UUID
    asignado_por: UUID
    estado: str
    descripcion: str
    contexto_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    comentarios: list[ComentarioResponse] = []

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class TareaListResponse(BaseModel):
    """Schema de respuesta para listados de tareas."""

    items: list[TareaResponse]
    total: int

    model_config = ConfigDict(extra="forbid")
