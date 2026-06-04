"""Schemas Pydantic v2 (DTOs) para Calificaciones y Umbrales (C-10).

Todos los schemas usan ``model_config = ConfigDict(extra='forbid')``
(REGLA DURA #5).
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PreviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actividades_detectadas: list[str]
    filas: int
    alumnos_detectados: int
    preview_token: str


class ConfirmResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    calificaciones_importadas: int
    actividades: list[dict]


class ActividadSinCorregir(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alumno: str
    actividad: str
    entregado_en: str


class FinalizacionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    posibles_sin_corregir: list[ActividadSinCorregir]


class UmbralResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    umbral_pct: int
    valores_aprobatorios: list[str]


class UmbralConfigRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    materia_id: UUID
    asignacion_id: UUID
    umbral_pct: int | None = None
    valores_aprobatorios: list[str] | None = None


class UmbralMateriaResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    materia_id: UUID
    asignacion_id: UUID
    umbral_pct: int
    valores_aprobatorios: list[str] | None
    calificaciones_recalculadas: int
