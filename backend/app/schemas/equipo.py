"""Schemas Pydantic v2 (DTOs) para Equipo Docente (C-08).

Todos los schemas usan ``model_config = ConfigDict(extra='forbid')``
(REGLA DURA #5).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.asignacion import AsignacionResponse


# ── Request Schemas ────────────────────────────────────────────────────


class AsignacionMasivaRequest(BaseModel):
    """Body para asignación masiva de N usuarios a un contexto académico."""

    model_config = ConfigDict(extra="forbid")

    usuario_ids: list[UUID] = Field(min_length=1)
    materia_id: str = Field(min_length=36, max_length=36)
    carrera_id: str = Field(min_length=36, max_length=36)
    cohorte_id: str = Field(min_length=36, max_length=36)
    rol: str = Field(min_length=1, max_length=50)
    comisiones: Optional[list[str]] = None
    responsable_id: Optional[str] = Field(
        default=None, min_length=36, max_length=36
    )
    desde: datetime
    hasta: Optional[datetime] = None


class ClonarEquipoRequest(BaseModel):
    """Body para clonar un equipo docente de origen a destino."""

    model_config = ConfigDict(extra="forbid")

    origen_materia_id: str = Field(min_length=36, max_length=36)
    origen_carrera_id: str = Field(min_length=36, max_length=36)
    origen_cohorte_id: str = Field(min_length=36, max_length=36)
    destino_materia_id: str = Field(min_length=36, max_length=36)
    destino_carrera_id: str = Field(min_length=36, max_length=36)
    destino_cohorte_id: str = Field(min_length=36, max_length=36)
    destino_desde: datetime
    destino_hasta: Optional[datetime] = None


class VigenciaRequest(BaseModel):
    """Body para modificar vigencia de todas las asignaciones de un equipo."""

    model_config = ConfigDict(extra="forbid")

    materia_id: str = Field(min_length=36, max_length=36)
    carrera_id: str = Field(min_length=36, max_length=36)
    cohorte_id: str = Field(min_length=36, max_length=36)
    desde: datetime
    hasta: Optional[datetime] = None


# ── Response Schemas ───────────────────────────────────────────────────


class EquipoResponse(BaseModel):
    """Respuesta con datos de una asignación en contexto de equipo docente.

    Incluye nombres de materia/carrera/cohorte desde joins.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    tenant_id: str
    usuario_id: str
    rol: str
    materia_id: Optional[str] = None
    carrera_id: Optional[str] = None
    cohorte_id: Optional[str] = None
    comisiones: Optional[list[str]] = None
    responsable_id: Optional[str] = None
    desde: datetime
    hasta: Optional[datetime] = None
    estado_vigencia: str = Field(default="Vigente")
    materia_nombre: Optional[str] = None
    carrera_nombre: Optional[str] = None
    cohorte_nombre: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class VigenciaResponse(BaseModel):
    """Respuesta de modificación de vigencia."""

    model_config = ConfigDict(extra="forbid")

    afectadas: int
    desde: datetime
    hasta: Optional[datetime] = None


class ClonarResponse(BaseModel):
    """Respuesta de clonación de equipo docente."""

    model_config = ConfigDict(extra="forbid")

    creadas: int
    origen: str
    destino: str
    asignaciones: list[AsignacionResponse]
