"""Schemas Pydantic v2 (DTOs) para Carrera (C-06 estructura-academica).

Todos los schemas usan ``model_config = ConfigDict(extra='forbid')``
(REGLA DURA #5).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CarreraCreate(BaseModel):
    """Body para crear una carrera."""

    model_config = ConfigDict(extra="forbid")

    codigo: str = Field(min_length=1, max_length=50)
    nombre: str = Field(min_length=1, max_length=200)
    estado: str = Field(default="Activa", pattern=r"^(Activa|Inactiva)$")


class CarreraUpdate(BaseModel):
    """Body para actualizar parcialmente una carrera."""

    model_config = ConfigDict(extra="forbid")

    nombre: Optional[str] = Field(default=None, min_length=1, max_length=200)
    estado: Optional[str] = Field(
        default=None, pattern=r"^(Activa|Inactiva)$"
    )


class CarreraResponse(BaseModel):
    """Respuesta con datos de una carrera."""

    model_config = ConfigDict(extra="forbid")

    id: str
    tenant_id: str
    codigo: str
    nombre: str
    estado: str
    created_at: datetime
    updated_at: datetime
