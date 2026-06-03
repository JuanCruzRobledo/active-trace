"""Schemas Pydantic v2 (DTOs) para Cohorte (C-06 estructura-academica).

Todos los schemas usan ``model_config = ConfigDict(extra='forbid')``
(REGLA DURA #5).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CohorteCreate(BaseModel):
    """Body para crear una cohorte."""

    model_config = ConfigDict(extra="forbid")

    carrera_id: str = Field(min_length=36, max_length=36)
    nombre: str = Field(min_length=1, max_length=100)
    anio: int = Field(ge=1900, le=2150)
    vig_desde: date
    vig_hasta: Optional[date] = None
    estado: str = Field(default="Activa", pattern=r"^(Activa|Inactiva)$")

    @field_validator("vig_hasta")
    @classmethod
    def validate_vig_hasta(cls, v: Optional[date], info) -> Optional[date]:
        if v is not None:
            vig_desde = info.data.get("vig_desde")
            if vig_desde and v <= vig_desde:
                raise ValueError(
                    "vig_hasta must be after vig_desde"
                )
        return v


class CohorteUpdate(BaseModel):
    """Body para actualizar parcialmente una cohorte."""

    model_config = ConfigDict(extra="forbid")

    nombre: Optional[str] = Field(default=None, min_length=1, max_length=100)
    vig_desde: Optional[date] = None
    vig_hasta: Optional[date] = None
    estado: Optional[str] = Field(
        default=None, pattern=r"^(Activa|Inactiva)$"
    )


class CohorteResponse(BaseModel):
    """Respuesta con datos de una cohorte."""

    model_config = ConfigDict(extra="forbid")

    id: str
    tenant_id: str
    carrera_id: str
    nombre: str
    anio: int
    vig_desde: date
    vig_hasta: Optional[date] = None
    estado: str
    created_at: datetime
    updated_at: datetime
