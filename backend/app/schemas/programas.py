"""Schemas Pydantic para el modulo de programas de materia (C-17).

Define los contratos de request/response para la API REST de programas
de materia. Todos los schemas usan ``extra='forbid'``.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProgramaMateriaCreate(BaseModel):
    """Schema para subir un programa de materia.

    Attributes:
        materia_id: UUID de la materia asociada.
        carrera_id: UUID de la carrera asociada.
        cohorte_id: UUID de la cohorte asociada.
        titulo: Titulo descriptivo del programa.
        referencia_archivo: UUID opaco que referencia el archivo en storage.
    """

    materia_id: UUID
    carrera_id: UUID
    cohorte_id: UUID
    titulo: str
    referencia_archivo: UUID

    model_config = ConfigDict(extra="forbid")


class ProgramaMateriaResponse(BaseModel):
    """Schema de respuesta para un programa de materia.

    Nota: la referencia_archivo solo se incluye en el detalle individual.
    """

    id: UUID
    titulo: str
    materia_id: UUID
    carrera_id: UUID
    cohorte_id: UUID
    referencia_archivo: UUID
    cargado_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class ProgramaMateriaListItem(BaseModel):
    """Schema de item para listado de programas (sin referencia_archivo)."""

    id: UUID
    titulo: str
    materia_id: UUID
    carrera_id: UUID
    cohorte_id: UUID
    cargado_at: datetime | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class ProgramaMateriaListResponse(BaseModel):
    """Schema de respuesta para listado de programas."""

    items: list[ProgramaMateriaListItem]
    total: int

    model_config = ConfigDict(extra="forbid")
