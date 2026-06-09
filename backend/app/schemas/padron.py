"""Schemas Pydantic v2 (DTOs) para Padron de Alumnos (C-09 padron-ingesta).

Todos los schemas usan ``model_config = ConfigDict(extra='forbid')``
(REGLA DURA #5).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PadronPreviewResponse(BaseModel):
    """Respuesta de la vista previa de importacion."""

    model_config = ConfigDict(extra="forbid")

    preview: bool = Field(default=True, description="Indica que es una respuesta de preview")
    preview_token: str
    filas_leidas: int = Field(description="Cantidad de filas detectadas en el archivo")
    columnas_mapeadas: list[str]
    filas: list[dict[str, str | None]] = Field(description="Primeras filas del archivo como preview")


class PadronConfirmRequest(BaseModel):
    """Body para confirmar una importacion."""

    model_config = ConfigDict(extra="forbid")

    preview_token: str = Field(min_length=1)


class PadronImportResponse(BaseModel):
    """Respuesta de una importacion confirmada."""

    model_config = ConfigDict(extra="forbid")

    version_id: str
    materia_id: str
    cohorte_id: str
    cantidad_entradas: int
    cargado_at: datetime


class EntradaPadronResponse(BaseModel):
    """Respuesta con datos de una entrada del padron."""

    model_config = ConfigDict(extra="forbid")

    id: str
    version_id: str
    usuario_id: Optional[str] = None
    nombre: str
    apellidos: str
    email: str
    comision: Optional[str] = None
    regional: Optional[str] = None


class VersionPadronResponse(BaseModel):
    """Respuesta con datos de una version de padron."""

    model_config = ConfigDict(extra="forbid")

    id: str
    materia_id: str
    cohorte_id: str
    cargado_por: Optional[str] = None
    cargado_at: datetime
    activa: bool
    entradas: list[EntradaPadronResponse]
    created_at: datetime
    updated_at: datetime


class PadronVaciarResponse(BaseModel):
    """Respuesta de la operacion de vaciado."""

    model_config = ConfigDict(extra="forbid")

    materia_id: str
    versiones_desactivadas: int
    entradas_eliminadas: int
