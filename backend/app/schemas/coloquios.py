"""Schemas Pydantic para el modulo de Coloquios (C-14).

Todos los schemas usan ``extra='forbid'`` (REGLAS DURAS #5).
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ── Evaluacion (convocatoria) schemas ────────────────────────────────────


class EvaluacionCreate(BaseModel):
    """Datos para crear una nueva convocatoria de evaluacion."""

    model_config = ConfigDict(extra="forbid")

    materia_id: UUID
    cohorte_id: UUID
    tipo: str
    instancia: str = Field(..., min_length=1, max_length=200)
    dias_disponibles: int = Field(default=1, ge=1)
    cupos_por_dia: int = Field(default=1, ge=1)
    fecha_inicio: date
    fecha_fin: date


class EvaluacionUpdate(BaseModel):
    """Datos para actualizar una convocatoria."""

    model_config = ConfigDict(extra="forbid")

    instancia: str | None = Field(None, min_length=1, max_length=200)
    dias_disponibles: int | None = Field(None, ge=1)
    cupos_por_dia: int | None = Field(None, ge=1)
    fecha_inicio: date | None = None
    fecha_fin: date | None = None


class EvaluacionResponse(BaseModel):
    """Respuesta completa de una convocatoria con metricas."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    materia_id: UUID
    cohorte_id: UUID
    tipo: str
    instancia: str
    dias_disponibles: int
    cupos_por_dia: int
    fecha_inicio: date
    fecha_fin: date
    estado: str
    created_at: str | None = None
    updated_at: str | None = None
    convocados: int = 0
    reservas_activas: int = 0
    cupos_libres: int = 0
    resultados: int = 0


# ── Reserva schemas ─────────────────────────────────────────────────────


class ReservaCreate(BaseModel):
    """Datos para reservar un turno de coloquio."""

    model_config = ConfigDict(extra="forbid")

    evaluacion_id: UUID
    fecha_hora: datetime


class ReservaResponse(BaseModel):
    """Respuesta de una reserva."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    evaluacion_id: UUID
    alumno_id: UUID
    fecha_hora: datetime
    estado: str
    created_at: str | None = None
    updated_at: str | None = None
    alumno_nombre: str | None = None
    alumno_email: str | None = None


# ── Resultado schemas ───────────────────────────────────────────────────


class ResultadoCreate(BaseModel):
    """Datos para registrar el resultado de un alumno."""

    model_config = ConfigDict(extra="forbid")

    evaluacion_id: UUID
    alumno_id: UUID
    nota_final: str = Field(..., min_length=1, max_length=100)


class ResultadoResponse(BaseModel):
    """Respuesta de un resultado de evaluacion."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    evaluacion_id: UUID
    alumno_id: UUID
    nota_final: str
    created_at: str | None = None
    updated_at: str | None = None


# ── Importacion schemas ─────────────────────────────────────────────────


class ImportarAlumnosRequest(BaseModel):
    """Lista de IDs de alumnos a importar a una convocatoria."""

    model_config = ConfigDict(extra="forbid")

    alumno_ids: list[UUID]


class ImportarAlumnosResponse(BaseModel):
    """Respuesta de la importacion de alumnos."""

    model_config = ConfigDict(extra="forbid")

    importados: int
    omitidos: int


# ── Metricas schemas ────────────────────────────────────────────────────


class MetricasColoquiosResponse(BaseModel):
    """Metricas globales del modulo de coloquios."""

    model_config = ConfigDict(extra="forbid")

    total_convocatorias: int = 0
    total_alumnos_importados: int = 0
    reservas_activas: int = 0
    resultados_registrados: int = 0


# ── Agenda schema ───────────────────────────────────────────────────────


class AgendaItemResponse(BaseModel):
    """Item de la agenda consolidada de reservas."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    evaluacion_id: UUID
    alumno_id: UUID
    alumno_nombre: str | None = None
    materia_nombre: str | None = None
    cohorte_nombre: str | None = None
    instancia: str | None = None
    fecha_hora: datetime
    estado: str


class AgendaResponse(BaseModel):
    """Agenda consolidada de reservas activas."""

    model_config = ConfigDict(extra="forbid")

    items: list[AgendaItemResponse]
    total: int
