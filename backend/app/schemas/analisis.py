"""Schemas Pydantic v2 (DTOs) para Analisis de Calificaciones (C-11).

Todos los schemas usan ``model_config = ConfigDict(extra='forbid')``
(REGLA DURA #5).
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


# ── Atrasados ────────────────────────────────────────────────────────


class AlumnoAtrasadoEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alumno_id: UUID
    nombre: str
    apellidos: str
    legajo: str | None = None
    actividades_faltantes: int
    actividades_bajo_umbral: int
    comision: str | None = None


class AtrasadosResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alumnos_atrasados: list[AlumnoAtrasadoEntry]
    total_alumnos: int
    porcentaje: float


# ── Ranking ──────────────────────────────────────────────────────────


class RankingEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alumno_id: UUID
    nombre: str
    apellidos: str
    cantidad_aprobadas: int
    total_actividades: int


class RankingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ranking: list[RankingEntry]


# ── Reporte Rapido ───────────────────────────────────────────────────


class ReporteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_alumnos: int
    aprobados: int
    atrasados: int
    porcentaje_aprobacion: float
    cantidad_actividades: int


# ── Notas Finales ────────────────────────────────────────────────────


class NotaFinalEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alumno_id: UUID
    nombre: str
    apellidos: str
    promedio: float | None
    aprobado: bool


class NotasFinalesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notas: list[NotaFinalEntry]


# ── TPs sin corregir ─────────────────────────────────────────────────


class TpPendienteEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alumno_id: UUID
    nombre: str
    apellidos: str
    actividad: str
    entregado_en: str | None = None


class TpsPendientesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pendientes: list[TpPendienteEntry]


# ── Monitores ────────────────────────────────────────────────────────


class ActividadEstado(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actividad: str
    nota_numerica: float | None = None
    nota_textual: str | None = None
    aprobado: bool | None = None
    materia_nombre: str | None = None


class AlumnoMonitorEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alumno_id: UUID
    nombre: str
    apellidos: str
    comision: str | None = None
    email: str | None = None
    actividades: list[ActividadEstado]


class MonitorGeneralResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alumnos: list[AlumnoMonitorEntry]
    total: int


class MonitorSeguimientoResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alumnos: list[AlumnoMonitorEntry]
    total: int
