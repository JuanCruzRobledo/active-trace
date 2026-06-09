"""Schemas Pydantic v2 (DTOs) para Usuario (C-07 usuarios-y-asignaciones).

Todos los schemas usan ``model_config = ConfigDict(extra='forbid')``
(REGLA DURA #5).

Los campos PII (email, dni, cuil, cbu, alias_cbu) se retornan enmascarados
en los schemas de respuesta para no exponer datos sensibles.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UsuarioCreate(BaseModel):
    """Body para crear un usuario."""

    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1, max_length=100)
    apellidos: str = Field(min_length=1, max_length=200)
    email: EmailStr
    dni: Optional[str] = Field(default=None, max_length=20)
    cuil: Optional[str] = Field(default=None, max_length=20)
    cbu: Optional[str] = Field(default=None, max_length=30)
    alias_cbu: Optional[str] = Field(default=None, max_length=100)
    banco: Optional[str] = Field(default=None, max_length=100)
    regional: Optional[str] = Field(default=None, max_length=100)
    legajo: Optional[str] = Field(default=None, max_length=50)
    legajo_profesional: Optional[str] = Field(default=None, max_length=50)
    facturador: Optional[str] = Field(default=None, max_length=200)
    estado: str = Field(default="Activo", pattern=r"^(Activo|Inactivo)$")


class UsuarioUpdate(BaseModel):
    """Body para actualizar parcialmente un usuario."""

    model_config = ConfigDict(extra="forbid")

    nombre: Optional[str] = Field(default=None, min_length=1, max_length=100)
    apellidos: Optional[str] = Field(default=None, min_length=1, max_length=200)
    email: Optional[EmailStr] = None
    dni: Optional[str] = Field(default=None, max_length=20)
    cuil: Optional[str] = Field(default=None, max_length=20)
    cbu: Optional[str] = Field(default=None, max_length=30)
    alias_cbu: Optional[str] = Field(default=None, max_length=100)
    banco: Optional[str] = Field(default=None, max_length=100)
    regional: Optional[str] = Field(default=None, max_length=100)
    legajo: Optional[str] = Field(default=None, max_length=50)
    legajo_profesional: Optional[str] = Field(default=None, max_length=50)
    facturador: Optional[str] = Field(default=None, max_length=200)
    estado: Optional[str] = Field(
        default=None, pattern=r"^(Activo|Inactivo)$"
    )


class UsuarioResponse(BaseModel):
    """Respuesta con datos de un usuario (PII enmascarada)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    tenant_id: str
    nombre: str
    apellidos: str
    email: str
    dni: Optional[str] = None
    cuil: Optional[str] = None
    cbu: Optional[str] = None
    alias_cbu: Optional[str] = None
    banco: Optional[str] = None
    regional: Optional[str] = None
    legajo: Optional[str] = None
    legajo_profesional: Optional[str] = None
    facturador: Optional[str] = None
    estado: str
    created_at: datetime
    updated_at: datetime


class UsuarioListResponse(BaseModel):
    """Respuesta paginada de usuarios."""

    model_config = ConfigDict(extra="forbid")

    items: list[UsuarioResponse]
    total: int
    page: int
    page_size: int
