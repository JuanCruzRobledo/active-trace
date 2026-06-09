"""Router de analisis academico — atrasados, ranking, reportes, monitores (C-11).

Endpoints protegidos con ``require_permission("atrasados:ver")``:
- ``GET /api/analisis/atrasados`` — alumnos atrasados (RN-06)
- ``GET /api/analisis/ranking`` — ranking de actividades aprobadas (RN-09)
- ``GET /api/analisis/reporte-rapido`` — metricas consolidadas
- ``GET /api/analisis/notas-finales`` — notas finales agrupadas
- ``GET /api/analisis/tps-sin-corregir`` — TPs textuales sin calificar (RN-07/08)
- ``GET /api/analisis/monitor-general`` — monitor transversal (F2.7)
- ``GET /api/analisis/monitor-seguimiento`` — monitor de seguimiento (F2.8 / F2.9)
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    UserContext,
    get_current_user,
    get_db,
    require_permission,
)
from app.schemas.analisis import (
    AtrasadosResponse,
    MonitorGeneralResponse,
    MonitorSeguimientoResponse,
    NotasFinalesResponse,
    RankingResponse,
    ReporteResponse,
    TpsPendientesResponse,
)
from app.services.analisis_service import AnalisisService

router = APIRouter(
    prefix="/api/analisis",
    tags=["analisis"],
)


# ── Helpers ──────────────────────────────────────────────────────────


def _build_service(db: AsyncSession, tenant_id: UUID) -> AnalisisService:
    return AnalisisService(session=db, tenant_id=tenant_id)


# ── Endpoints ────────────────────────────────────────────────────────


@router.get("/atrasados", response_model=AtrasadosResponse)
async def get_atrasados(
    materia_id: UUID = Query(..., description="ID de la materia"),
    cohorte_id: UUID | None = Query(None, description="ID de la cohorte"),
    comision: str | None = Query(None, description="Comision (opcional)"),
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("atrasados:ver")),
) -> AtrasadosResponse:
    """Retorna listado de alumnos atrasados para una materia (RN-06)."""
    service = _build_service(db, ctx.tenant_id)
    try:
        result = await service.obtener_atrasados(
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            comision=comision,
        )
        return AtrasadosResponse(**result)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/ranking", response_model=RankingResponse)
async def get_ranking(
    materia_id: UUID = Query(..., description="ID de la materia"),
    cohorte_id: UUID | None = Query(None, description="ID de la cohorte"),
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("atrasados:ver")),
) -> RankingResponse:
    """Ranking de actividades aprobadas (RN-09). Solo >= 1 aprobada."""
    service = _build_service(db, ctx.tenant_id)
    ranking = await service.obtener_ranking(
        materia_id=materia_id,
        cohorte_id=cohorte_id,
    )
    return RankingResponse(ranking=ranking)


@router.get("/reporte-rapido", response_model=ReporteResponse)
async def get_reporte_rapido(
    materia_id: UUID = Query(..., description="ID de la materia"),
    cohorte_id: UUID | None = Query(None, description="ID de la cohorte"),
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("atrasados:ver")),
) -> ReporteResponse:
    """Metricas consolidadas de una materia."""
    service = _build_service(db, ctx.tenant_id)
    result = await service.obtener_reporte_rapido(
        materia_id=materia_id,
        cohorte_id=cohorte_id,
    )
    return ReporteResponse(**result)


@router.get("/notas-finales", response_model=NotasFinalesResponse)
async def get_notas_finales(
    materia_id: UUID = Query(..., description="ID de la materia"),
    cohorte_id: UUID | None = Query(None, description="ID de la cohorte"),
    actividades: list[str] | None = Query(None, description="Actividades a promediar"),
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("atrasados:ver")),
) -> NotasFinalesResponse:
    """Notas finales agrupadas por alumno con promedio y bandera aprobado."""
    service = _build_service(db, ctx.tenant_id)
    notas = await service.obtener_notas_finales(
        materia_id=materia_id,
        cohorte_id=cohorte_id,
        actividades=actividades,
    )
    return NotasFinalesResponse(notas=notas)


@router.get("/tps-sin-corregir", response_model=TpsPendientesResponse)
async def get_tps_sin_corregir(
    materia_id: UUID = Query(..., description="ID de la materia"),
    cohorte_id: UUID | None = Query(None, description="ID de la cohorte"),
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("atrasados:ver")),
) -> TpsPendientesResponse:
    """TPs textuales finalizados sin calificacion (RN-07/08)."""
    service = _build_service(db, ctx.tenant_id)
    pendientes = await service.obtener_tps_sin_corregir(
        materia_id=materia_id,
        cohorte_id=cohorte_id,
    )
    return TpsPendientesResponse(pendientes=pendientes)


@router.get("/monitor-general", response_model=MonitorGeneralResponse)
async def get_monitor_general(
    materia_id: UUID | None = Query(None, description="ID de la materia"),
    regional: str | None = Query(None, description="Regional"),
    comision: str | None = Query(None, description="Comision"),
    q: str | None = Query(None, description="Busqueda libre por nombre"),
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("atrasados:ver")),
) -> MonitorGeneralResponse:
    """Monitor general transversal (F2.7) — COORDINADOR/ADMIN."""
    service = _build_service(db, ctx.tenant_id)
    result = await service.obtener_monitor_general(
        materia_id=materia_id,
        regional=regional,
        comision=comision,
        q=q,
    )
    return MonitorGeneralResponse(**result)


@router.get("/monitor-seguimiento", response_model=MonitorSeguimientoResponse)
async def get_monitor_seguimiento(
    actividad: str | None = Query(None, description="Filtrar por actividad"),
    min_aprobadas: int | None = Query(None, description="Minimo de aprobadas"),
    fecha_desde: str | None = Query(None, description="Fecha inicio (ISO)"),
    fecha_hasta: str | None = Query(None, description="Fecha fin (ISO)"),
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("atrasados:ver")),
) -> MonitorSeguimientoResponse:
    """Monitor de seguimiento (F2.8 / F2.9).

    Para TUTOR/PROFESOR: solo alumnos de sus materias.
    Para COORDINADOR/ADMIN: con rango de fechas opcional.
    """
    service = _build_service(db, ctx.tenant_id)

    from datetime import datetime

    desde: datetime | None = None
    hasta: datetime | None = None
    if fecha_desde:
        desde = datetime.fromisoformat(fecha_desde)
    if fecha_hasta:
        hasta = datetime.fromisoformat(fecha_hasta)

    result = await service.obtener_monitor_seguimiento(
        usuario_id=ctx.user_id,
        actividad=actividad,
        min_aprobadas=min_aprobadas,
        fecha_desde=desde,
        fecha_hasta=hasta,
    )
    return MonitorSeguimientoResponse(**result)
