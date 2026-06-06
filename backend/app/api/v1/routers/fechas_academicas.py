"""Router de Fechas Academicas — CRUD de instancias evaluativas (C-17).

Endpoints:
- POST /api/fechas-academicas — crear fecha (estructura:gestionar).
- GET /api/fechas-academicas — listar fechas con filtros.
- GET /api/fechas-academicas/{id} — obtener detalle.
- PATCH /api/fechas-academicas/{id} — actualizar fecha (estructura:gestionar).
- DELETE /api/fechas-academicas/{id} — eliminar (soft delete, estructura:gestionar).
- GET /api/fechas-academicas/lms-export — exportar HTML para LMS (estructura:gestionar).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    UserContext,
    get_db,
    require_permission,
)
from app.core.exceptions import BusinessError
from app.models.enums import TipoFechaAcademica
from app.schemas.fechas_academicas import (
    FechaAcademicaCreate,
    FechaAcademicaUpdate,
)
from app.services.fecha_academica_service import FechaAcademicaService

router = APIRouter(
    prefix="/api/fechas-academicas",
    tags=["fechas-academicas"],
)


def _build_service(
    db: AsyncSession, ctx: UserContext
) -> FechaAcademicaService:
    """Construye FechaAcademicaService.

    Args:
        db: Sesion de base de datos.
        ctx: Contexto de usuario (JWT).
    """
    return FechaAcademicaService(
        session=db,
        tenant_id=ctx.tenant_id,
        actor_id=ctx.user_id,
        roles=ctx.roles,
    )


# ── LMS Export (MUST be before /{fecha_id}) ──────────────────────────────


@router.get("/lms-export")
async def exportar_lms(
    materia_id: UUID = Query(...),
    cohorte_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("estructura:gestionar")),
) -> dict:
    """Genera fragmento HTML con fechas para publicar en LMS.

    Requiere permiso ``estructura:gestionar``.
    Retorna JSON con ``contenido_html`` (texto plano HTML).
    """
    svc = _build_service(db, ctx)
    return await svc.generar_lms_export(
        materia_id=materia_id,
        cohorte_id=cohorte_id,
    )


# ── CRUD ─────────────────────────────────────────────────────────────────


@router.post("", status_code=status.HTTP_201_CREATED)
async def crear_fecha(
    body: FechaAcademicaCreate,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("estructura:gestionar")),
) -> dict:
    """Crea una nueva fecha academica.

    Requiere permiso ``estructura:gestionar``.
    """
    svc = _build_service(db, ctx)
    try:
        return await svc.crear_fecha(body)
    except BusinessError as exc:
        msg = str(exc)
        if "ya existe" in msg.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=msg,
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        ) from exc


@router.get("")
async def listar_fechas(
    materia_id: UUID | None = Query(None),
    cohorte_id: UUID | None = Query(None),
    tipo: TipoFechaAcademica | None = Query(None),
    periodo: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("estructura:gestionar")),
) -> dict:
    """Lista fechas academicas con filtros combinables.

    Requiere permiso ``estructura:gestionar``.
    Ordenadas por fecha ASC.
    """
    svc = _build_service(db, ctx)
    return await svc.listar_fechas(
        materia_id=materia_id,
        cohorte_id=cohorte_id,
        tipo=tipo,
        periodo=periodo,
    )


@router.get("/{fecha_id}")
async def obtener_fecha(
    fecha_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("estructura:gestionar")),
) -> dict:
    """Obtiene el detalle de una fecha academica.

    Requiere permiso ``estructura:gestionar``.
    """
    svc = _build_service(db, ctx)
    try:
        return await svc.obtener_fecha(fecha_id)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.patch("/{fecha_id}")
async def actualizar_fecha(
    fecha_id: UUID,
    body: FechaAcademicaUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("estructura:gestionar")),
) -> dict:
    """Actualiza una fecha academica.

    Requiere permiso ``estructura:gestionar``.
    Valida unicidad si cambia tipo/numero.
    """
    svc = _build_service(db, ctx)
    try:
        return await svc.actualizar_fecha(fecha_id, body)
    except BusinessError as exc:
        msg = str(exc)
        if "ya existe" in msg.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=msg,
            ) from exc
        if "no encontrada" in msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=msg,
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        ) from exc


@router.delete("/{fecha_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_fecha(
    fecha_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("estructura:gestionar")),
) -> None:
    """Elimina (soft delete) una fecha academica.

    Requiere permiso ``estructura:gestionar``.
    Registra audit log ``FECHA_ACADEMICA_ELIMINAR``.
    """
    svc = _build_service(db, ctx)
    try:
        await svc.eliminar_fecha(fecha_id)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
