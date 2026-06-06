"""Schemas Pydantic para el modulo de fechas academicas (C-17).

Define los contratos de request/response para la API REST de fechas
academicas. Todos los schemas usan ``extra='forbid'``.
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import TipoFechaAcademica


class FechaAcademicaCreate(BaseModel):
    """Schema para crear una fecha academica.

    Attributes:
        materia_id: UUID de la materia asociada.
        cohorte_id: UUID de la cohorte asociada.
        tipo: Tipo de fecha (Parcial, TP, Coloquio, Recuperatorio).
        numero: Numero de instancia (1er parcial, 2do parcial, etc.).
        periodo: Periodo lectivo (ej. "2026-1").
        fecha: Fecha de la instancia evaluativa.
        titulo: Titulo descriptivo.
    """

    materia_id: UUID
    cohorte_id: UUID
    tipo: TipoFechaAcademica
    numero: int
    periodo: str
    fecha: date
    titulo: str

    model_config = ConfigDict(extra="forbid")


class FechaAcademicaUpdate(BaseModel):
    """Schema para actualizar una fecha academica (todos los campos opcionales)."""

    tipo: TipoFechaAcademica | None = None
    numero: int | None = None
    periodo: str | None = None
    fecha: date | None = None
    titulo: str | None = None

    model_config = ConfigDict(extra="forbid")


class FechaAcademicaResponse(BaseModel):
    """Schema de respuesta para una fecha academica."""

    id: UUID
    materia_id: UUID
    cohorte_id: UUID
    tipo: TipoFechaAcademica
    numero: int
    periodo: str
    fecha: date
    titulo: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class FechaAcademicaListResponse(BaseModel):
    """Schema de respuesta para listado de fechas academicas."""

    items: list[FechaAcademicaResponse]
    total: int

    model_config = ConfigDict(extra="forbid")


class LmsExportResponse(BaseModel):
    """Schema de respuesta para exportacion LMS.

    Attributes:
        contenido_html: Fragmento HTML listo para copiar en el LMS.
    """

    contenido_html: str

    model_config = ConfigDict(extra="forbid")
