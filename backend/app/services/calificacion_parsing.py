"""Helpers de parseo para calificaciones — xlsx, csv, deteccion de columnas.

Extraido de calificacion_service.py para cumplir con el limite de 500 LOC.
"""

from __future__ import annotations

import csv
import hashlib
import io
from typing import Any

from app.core.exceptions import BusinessError


# ── Cache de previews en memoria ─────────────────────────────────────

_preview_cache: dict[str, dict[str, Any]] = {}


def _generar_preview_token(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ── Helpers de parseo ────────────────────────────────────────────────


def parsear_xlsx(data: bytes) -> tuple[list[str], list[list[str]]]:
    """Retorna (headers, filas) desde un archivo xlsx."""
    try:
        import openpyxl  # noqa: PLC0415
    except ImportError:
        raise BusinessError("openpyxl no esta instalado")

    workbook = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    sheet = workbook.active
    if sheet is None:
        raise BusinessError("El archivo xlsx no contiene ninguna hoja")

    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        raise BusinessError("El archivo xlsx esta vacio")

    headers = [str(h) if h is not None else "" for h in rows[0]]
    filas: list[list[str]] = []
    for row in rows[1:]:
        fila = [str(cell) if cell is not None else "" for cell in row]
        filas.append(fila)
    return headers, filas


def parsear_csv(data: bytes) -> tuple[list[str], list[list[str]]]:
    """Retorna (headers, filas) desde un archivo csv."""
    content = data.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)
    if not rows:
        raise BusinessError("El archivo csv esta vacio")

    headers = [h.strip() for h in rows[0]]
    filas: list[list[str]] = []
    for row in rows[1:]:
        fila = [cell.strip() for cell in row]
        filas.append(fila)
    return headers, filas


# ── Deteccion de columnas ────────────────────────────────────────────

_VALORES_TEXTUALES_CONOCIDOS = {
    "Satisfactorio", "No satisfactorio", "Supera lo esperado",
    "Aprobado", "Desaprobado", "Promocionado", "Regular",
    "Ausente", "No presentado",
}


def detectar_columnas(headers: list[str], filas_muestra: list[list[str]]) -> dict:
    """Detecta columnas numericas (terminan en '(Real)') y textuales.

    Returns:
        Dict con listas ``numericas``, ``textuales``, ``ignoradas``.
    """
    numericas: list[str] = []
    textuales: list[str] = []
    ignoradas: list[str] = []

    for i, header in enumerate(headers):
        if header.lower().strip().endswith("(real)"):
            numericas.append(header)
            continue

        if filas_muestra:
            valores = {
                fila[i].strip().lower()
                for fila in filas_muestra
                if i < len(fila) and fila[i].strip()
            }
            if valores & {v.lower() for v in _VALORES_TEXTUALES_CONOCIDOS}:
                textuales.append(header)
                continue

        ignoradas.append(header)

    return {
        "numericas": numericas,
        "textuales": textuales,
        "ignoradas": ignoradas,
    }


def columnas_identidad() -> set[str]:
    """Columnas del archivo que identifican al alumno."""
    return {"nombre", "apellido", "apellidos", "email", "dni", "legajo"}
