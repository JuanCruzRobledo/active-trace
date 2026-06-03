"""Schemas Pydantic v2 (DTOs) para Asignacion (C-07 usuarios-y-asignaciones).

Todos los schemas usan ``model_config = ConfigDict(extra='forbid')``
(REGLA DURA #5).

Incluye validación de vigencia (desde ≤ hasta) y campo derivado
``estado_vigencia`` en las respuestas.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AsignacionCreate(BaseModel):
    """Body para crear una asignación."""

    model_config = ConfigDict(extra="forbid")

    usuario_id: str = Field(min_length=36, max_length=36)
    rol: str = Field(min_length=1, max_length=50)
    materia_id: Optional[str] = Field(default=None, min_length=36, max_length=36)
    carrera_id: Optional[str] = Field(default=None, min_length=36, max_length=36)
    cohorte_id: Optional[str] = Field(default=None, min_length=36, max_length=36)
    comisiones: Optional[list[str]] = None
    responsable_id: Optional[str] = Field(default=None, min_length=36, max_length=36)
    desde: datetime
    hasta: Optional[datetime] = None

    @field_validator("hasta")
    @classmethod
    def validate_vigencia(cls, v: Optional[datetime], info) -> Optional[datetime]:
        if v is not None:
            desde = info.data.get("desde")
            if desde and v <= desde:
                raise ValueError("hasta debe ser posterior a desde")
        return v


class AsignacionUpdate(BaseModel):
    """Body para actualizar parcialmente una asignación."""

    model_config = ConfigDict(extra="forbid")

    rol: Optional[str] = Field(default=None, min_length=1, max_length=50)
    materia_id: Optional[str] = Field(default=None, min_length=36, max_length=36)
    carrera_id: Optional[str] = Field(default=None, min_length=36, max_length=36)
    cohorte_id: Optional[str] = Field(default=None, min_length=36, max_length=36)
    comisiones: Optional[list[str]] = None
    responsable_id: Optional[str] = Field(default=None, min_length=36, max_length=36)
    desde: Optional[datetime] = None
    hasta: Optional[datetime] = None

    @field_validator("hasta")
    @classmethod
    def validate_vigencia(cls, v: Optional[datetime], info) -> Optional[datetime]:
        if v is not None:
            desde = info.data.get("desde")
            if desde and v <= desde:
                raise ValueError("hasta debe ser posterior a desde")
        return v


class AsignacionResponse(BaseModel):
    """Respuesta con datos de una asignación."""

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
    created_at: datetime
    updated_at: datetime
