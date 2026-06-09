"""Schemas Pydantic para el modulo de perfil propio (C-20).

PerfilResponse: lectura del perfil con PII enmascarada.
PerfilUpdate: edicion parcial — cuil excluido estructuralmente.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PerfilResponse(BaseModel):
    """Respuesta de GET /api/perfil — todos los campos del usuario con PII enmascarada."""

    id: UUID
    tenant_id: UUID
    nombre: str
    apellidos: str
    email: str | None = None
    dni: str | None = None
    cuil: str | None = None
    banco: str | None = None
    cbu: str | None = None
    alias_cbu: str | None = None
    regional: str | None = None
    legajo_profesional: str | None = None
    facturador: str | None = None
    estado: str

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class PerfilUpdate(BaseModel):
    """Body de PATCH /api/perfil — campos editables; cuil excluido.

    ConfigDict(extra='forbid') garantiza que cualquier request que incluya
    un campo no declarado (ej. cuil) recibe 422 automaticamente.
    """

    nombre: str | None = None
    apellidos: str | None = None
    email: str | None = None
    dni: str | None = None
    banco: str | None = None
    cbu: str | None = None
    alias_cbu: str | None = None
    regional: str | None = None
    legajo_profesional: str | None = None
    facturador: str | None = None

    model_config = ConfigDict(extra="forbid")
