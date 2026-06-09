"""Schemas Pydantic para el panel de auditoría y métricas (C-19).

Todos los schemas usan ``extra='forbid'`` (REGLAS DURAS #5).
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# ── Panel de interacciones (F9.1) ──────────────────────────────────


class AccionesPorDiaItem(BaseModel):
    """Agregación de acciones por día."""

    model_config = ConfigDict(extra="forbid")

    fecha: date
    total: int


class ComunicacionesPorDocenteItem(BaseModel):
    """Distribución de estados de comunicación por docente."""

    model_config = ConfigDict(extra="forbid")

    usuario_id: UUID
    nombre: str
    Pendiente: int = 0
    Enviando: int = 0
    OK: int = 0
    Fallido: int = 0
    Cancelado: int = 0


class InteraccionesItem(BaseModel):
    """Agregación de interacciones por docente y materia."""

    model_config = ConfigDict(extra="forbid")

    usuario_id: UUID
    nombre: str
    materia_id: UUID
    materia_nombre: str
    acciones: dict[str, int]
    total: int


class UltimasAccionesItem(BaseModel):
    """Últimas acciones registradas en el sistema."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    fecha_hora: datetime
    actor_nombre: str
    accion: str
    materia_nombre: str | None = None
    detalle: dict | None = None
    ip: str | None = None


# ── Log completo de auditoría (F9.2) ───────────────────────────────


class LogItem(BaseModel):
    """Registro individual del log completo de auditoría."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    fecha_hora: datetime
    actor_id: UUID
    actor_nombre: str
    materia_id: UUID | None = None
    materia_nombre: str | None = None
    accion: str
    detalle: dict | None = None
    filas_afectadas: int | None = None
    ip: str | None = None
    user_agent: str | None = None


class LogPaginado(BaseModel):
    """Respuesta paginada del log de auditoría."""

    model_config = ConfigDict(extra="forbid")

    items: list[LogItem]
    total: int
    offset: int
    limit: int


# ── Filtros ────────────────────────────────────────────────────────


class FiltrosAuditoria(BaseModel):
    """Filtros combinables para consultas de auditoría.

    Todos los campos son opcionales — solo se aplican los presentes.
    """

    model_config = ConfigDict(extra="forbid")

    fecha_desde: date | None = None
    fecha_hasta: date | None = None
    materia_id: UUID | None = None
    usuario_id: UUID | None = None
    accion: str | None = None
