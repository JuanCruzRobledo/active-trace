"""Router del panel de auditoría y métricas (C-19).

Endpoints de solo lectura bajo ``/api/auditoria/*`` con permisos finos:
- ``auditoria:ver``: todos los endpoints del panel.
- ``require_role("ADMIN")``: solo el log completo (F9.2).

Scope ``(propio)`` para COORDINADOR: filtra automáticamente por las
materias donde tiene asignaciones activas como COORDINADOR.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    UserContext,
    get_db,
    require_permission,
)
from app.schemas.auditoria import (
    AccionesPorDiaItem,
    ComunicacionesPorDocenteItem,
    InteraccionesItem,
    LogItem,
    LogPaginado,
    UltimasAccionesItem,
)
from app.services.auditoria_service import AuditoriaService

router = APIRouter(
    prefix="/api/auditoria",
    tags=["Auditoría"],
)


# ── Helpers ──────────────────────────────────────────────────────────


def _build_service(db: AsyncSession, tenant_id: UUID) -> AuditoriaService:
    return AuditoriaService(session=db, tenant_id=tenant_id)


async def _get_scope(
    service: AuditoriaService,
    ctx: UserContext,
) -> list[UUID] | None:
    """Retorna scope de materias para COORDINADOR, None para ADMIN."""
    return await service._scope_materias(ctx.user_id, ctx.roles)


# ── Panel de interacciones (F9.1) ────────────────────────────────────


@router.get(
    "/acciones-por-dia",
    response_model=list[AccionesPorDiaItem],
)
async def get_acciones_por_dia(
    fecha_desde: date | None = Query(None, description="Fecha inicio (ISO)"),
    fecha_hasta: date | None = Query(None, description="Fecha fin (ISO)"),
    materia_id: UUID | None = Query(None, description="ID de la materia"),
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("auditoria:ver")),
) -> list[AccionesPorDiaItem]:
    """Agregación de acciones por día (F9.1)."""
    service = _build_service(db, ctx.tenant_id)
    scope = await _get_scope(service, ctx)
    try:
        result = await service.acciones_por_dia(
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            materia_id=materia_id,
            scope_materias=scope,
        )
        return [AccionesPorDiaItem(**r) for r in result]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/comunicaciones-por-docente",
    response_model=list[ComunicacionesPorDocenteItem],
)
async def get_comunicaciones_por_docente(
    materia_id: UUID | None = Query(None, description="ID de la materia"),
    fecha_desde: date | None = Query(None, description="Fecha inicio (ISO)"),
    fecha_hasta: date | None = Query(None, description="Fecha fin (ISO)"),
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("auditoria:ver")),
) -> list[ComunicacionesPorDocenteItem]:
    """Distribución de estados de comunicación por docente (F9.1)."""
    service = _build_service(db, ctx.tenant_id)
    scope = await _get_scope(service, ctx)
    try:
        result = await service.comunicaciones_por_docente(
            materia_id=materia_id,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            scope_materias=scope,
        )
        return [ComunicacionesPorDocenteItem(**r) for r in result]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/interacciones-por-docente-materia",
    response_model=list[InteraccionesItem],
)
async def get_interacciones_por_docente_materia(
    fecha_desde: date | None = Query(None, description="Fecha inicio (ISO)"),
    fecha_hasta: date | None = Query(None, description="Fecha fin (ISO)"),
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("auditoria:ver")),
) -> list[InteraccionesItem]:
    """Agregación de interacciones por docente × materia (F9.1)."""
    service = _build_service(db, ctx.tenant_id)
    scope = await _get_scope(service, ctx)
    try:
        result = await service.interacciones_por_docente_materia(
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            scope_materias=scope,
        )
        return [InteraccionesItem(**r) for r in result]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/ultimas-acciones",
    response_model=list[UltimasAccionesItem],
)
async def get_ultimas_acciones(
    limit: int = Query(200, description="Cantidad máxima (techo: 1000)", ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("auditoria:ver")),
) -> list[UltimasAccionesItem]:
    """Últimas acciones registradas (F9.1)."""
    service = _build_service(db, ctx.tenant_id)
    scope = await _get_scope(service, ctx)
    try:
        result = await service.ultimas_acciones(
            limit=limit,
            scope_materias=scope,
        )
        return [UltimasAccionesItem(**r) for r in result]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ── Log completo de auditoría (F9.2) — solo ADMIN ────────────────────


@router.get(
    "/log",
    response_model=LogPaginado,
)
async def get_log(
    fecha_desde: date | None = Query(None, description="Fecha inicio (ISO)"),
    fecha_hasta: date | None = Query(None, description="Fecha fin (ISO)"),
    materia_id: UUID | None = Query(None, description="ID de la materia"),
    usuario_id: UUID | None = Query(None, description="ID del usuario"),
    accion: str | None = Query(None, description="Código de acción"),
    offset: int = Query(0, description="Desplazamiento", ge=0),
    limit: int = Query(50, description="Máximo por página", ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("auditoria:ver")),
) -> LogPaginado:
    """Log completo de auditoría (F9.2). Solo ADMIN."""
    # Guard adicional: solo ADMIN puede ver el log completo
    if "ADMIN" not in ctx.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo ADMIN puede acceder al log completo de auditoría",
        )

    service = _build_service(db, ctx.tenant_id)
    scope = await _get_scope(service, ctx)
    try:
        result = await service.log_completo(
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            materia_id=materia_id,
            usuario_id=usuario_id,
            accion=accion,
            offset=offset,
            limit=limit,
            scope_materias=scope,
        )
        return LogPaginado(**result)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
