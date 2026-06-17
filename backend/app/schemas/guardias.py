"""Schemas Pydantic para el módulo de Guardias (C-13).

Todos los schemas usan ``extra='forbid'`` (REGLAS DURAS #5).
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GuardiaCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    materia_id: UUID | None = None
    carrera_id: UUID | None = None
    cohorte_id: UUID | None = None
    dia: str
    horario: str = Field(..., max_length=50)
    comentarios: str | None = None


class GuardiaUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    estado: str | None = None
    comentarios: str | None = None


class GuardiaResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    asignacion_id: UUID | None = None
    materia_id: UUID | None = None
    carrera_id: UUID | None = None
    cohorte_id: UUID | None = None
    dia: str
    horario: str
    estado: str
    comentarios: str | None = None
    creada_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    # Datos del docente asignado
    docente_nombre: str | None = None


class GuardiaListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[GuardiaResponse]
    total: int
