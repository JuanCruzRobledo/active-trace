"""Schemas Pydantic v2 (DTOs) para Liquidaciones y Honorarios (C-18).

Todos los schemas usan ``model_config = ConfigDict(extra='forbid')``
(REGLA DURA #5).

Incluye schemas de:
  - ClavePlus (catálogo configurable por tenant)
  - SalarioBase (grilla salarial por rol)
  - SalarioPlus (plus salarial por grupo × rol)
  - Liquidacion (cálculo mensual por docente)
  - Factura (factura de honorarios)
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ═══════════════════════════════════════════════════════════════════════════
# ClavePlus
# ═══════════════════════════════════════════════════════════════════════════


class ClavePlusCreate(BaseModel):
    """Body para crear una ClavePlus."""

    model_config = ConfigDict(extra="forbid")

    codigo: str = Field(min_length=1, max_length=20)
    nombre: str = Field(min_length=1, max_length=200)
    activa: bool = True


class ClavePlusUpdate(BaseModel):
    """Body para actualizar una ClavePlus."""

    model_config = ConfigDict(extra="forbid")

    codigo: Optional[str] = Field(default=None, min_length=1, max_length=20)
    nombre: Optional[str] = Field(default=None, min_length=1, max_length=200)
    activa: Optional[bool] = None


class ClavePlusResponse(BaseModel):
    """Respuesta con datos de una ClavePlus."""

    model_config = ConfigDict(extra="forbid")

    id: str
    tenant_id: str
    codigo: str
    nombre: str
    activa: bool
    created_at: datetime
    updated_at: datetime


# ═══════════════════════════════════════════════════════════════════════════
# SalarioBase
# ═══════════════════════════════════════════════════════════════════════════


class SalarioBaseCreate(BaseModel):
    """Body para crear un SalarioBase."""

    model_config = ConfigDict(extra="forbid")

    rol: str = Field(min_length=1, max_length=50)
    monto: Decimal = Field(max_digits=12, decimal_places=2)
    desde: date
    hasta: Optional[date] = None


class SalarioBaseUpdate(BaseModel):
    """Body para actualizar un SalarioBase."""

    model_config = ConfigDict(extra="forbid")

    rol: Optional[str] = Field(default=None, min_length=1, max_length=50)
    monto: Optional[Decimal] = Field(default=None, max_digits=12, decimal_places=2)
    desde: Optional[date] = None
    hasta: Optional[date] = None


class SalarioBaseResponse(BaseModel):
    """Respuesta con datos de un SalarioBase."""

    model_config = ConfigDict(extra="forbid")

    id: str
    tenant_id: str
    rol: str
    monto: Decimal
    desde: date
    hasta: Optional[date] = None
    created_at: datetime
    updated_at: datetime


# ═══════════════════════════════════════════════════════════════════════════
# SalarioPlus
# ═══════════════════════════════════════════════════════════════════════════


class SalarioPlusCreate(BaseModel):
    """Body para crear un SalarioPlus."""

    model_config = ConfigDict(extra="forbid")

    grupo: str = Field(min_length=1, max_length=20)
    rol: str = Field(min_length=1, max_length=50)
    descripcion: Optional[str] = Field(default=None, max_length=200)
    monto: Decimal = Field(max_digits=12, decimal_places=2)
    desde: date
    hasta: Optional[date] = None


class SalarioPlusUpdate(BaseModel):
    """Body para actualizar un SalarioPlus."""

    model_config = ConfigDict(extra="forbid")

    grupo: Optional[str] = Field(default=None, min_length=1, max_length=20)
    rol: Optional[str] = Field(default=None, min_length=1, max_length=50)
    descripcion: Optional[str] = Field(default=None, max_length=200)
    monto: Optional[Decimal] = Field(default=None, max_digits=12, decimal_places=2)
    desde: Optional[date] = None
    hasta: Optional[date] = None


class SalarioPlusResponse(BaseModel):
    """Respuesta con datos de un SalarioPlus."""

    model_config = ConfigDict(extra="forbid")

    id: str
    tenant_id: str
    grupo: str
    rol: str
    descripcion: Optional[str] = None
    monto: Decimal
    desde: date
    hasta: Optional[date] = None
    created_at: datetime
    updated_at: datetime


# ═══════════════════════════════════════════════════════════════════════════
# Liquidacion
# ═══════════════════════════════════════════════════════════════════════════


class LiquidacionCalcularRequest(BaseModel):
    """Body para solicitar el cálculo de una liquidación."""

    model_config = ConfigDict(extra="forbid")

    cohorte_id: str = Field(min_length=36, max_length=36)
    periodo: str = Field(pattern=r"^\d{4}-\d{2}$")
    usuario_id: str = Field(min_length=36, max_length=36)
    rol: str = Field(min_length=1, max_length=50)
    comisiones: Optional[list[str]] = None


class LiquidacionCerrarRequest(BaseModel):
    """Body para cerrar una liquidación."""

    model_config = ConfigDict(extra="forbid")

    audit_log_id: Optional[str] = Field(default=None, min_length=36, max_length=36)


class LiquidacionResponse(BaseModel):
    """Respuesta con datos de una Liquidacion."""

    model_config = ConfigDict(extra="forbid")

    id: str
    tenant_id: str
    cohorte_id: str
    periodo: str
    usuario_id: str
    rol: str
    comisiones: Optional[list[str]] = None
    monto_base: Decimal
    monto_plus: Decimal
    total: Decimal
    es_nexo: bool = False
    excluido_por_factura: bool = False
    estado: str
    cerrada_at: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class LiquidacionListResponse(BaseModel):
    """Lista paginada de liquidaciones."""

    model_config = ConfigDict(extra="forbid")

    items: list[LiquidacionResponse]
    total: int


# ═══════════════════════════════════════════════════════════════════════════
# Factura
# ═══════════════════════════════════════════════════════════════════════════


class FacturaCreate(BaseModel):
    """Body para crear una Factura."""

    model_config = ConfigDict(extra="forbid")

    usuario_id: str = Field(min_length=36, max_length=36)
    periodo: str = Field(pattern=r"^\d{4}-\d{2}$")
    detalle: Optional[str] = Field(default=None, max_length=1000)
    referencia_archivo: Optional[str] = Field(default=None, max_length=500)
    tamano_kb: Optional[int] = None


class FacturaUpdate(BaseModel):
    """Body para actualizar una Factura."""

    model_config = ConfigDict(extra="forbid")

    detalle: Optional[str] = Field(default=None, max_length=1000)
    referencia_archivo: Optional[str] = Field(default=None, max_length=500)
    tamano_kb: Optional[int] = None


class FacturaAbonarRequest(BaseModel):
    """Body para marcar una factura como abonada."""

    model_config = ConfigDict(extra="forbid")

    audit_log_id: Optional[str] = Field(default=None, min_length=36, max_length=36)


class FacturaResponse(BaseModel):
    """Respuesta con datos de una Factura."""

    model_config = ConfigDict(extra="forbid")

    id: str
    tenant_id: str
    usuario_id: str
    periodo: str
    detalle: Optional[str] = None
    referencia_archivo: Optional[str] = None
    tamano_kb: Optional[int] = None
    estado: str
    cargada_at: datetime
    abonada_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
