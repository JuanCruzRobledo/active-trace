"""Router de equipos docentes (C-08).

Endpoints protegidos con ``require_permission``:
- ``equipos:ver`` — GET /api/equipos/mis-equipos
- ``equipos:asignar`` — resto de operaciones.
"""

from __future__ import annotations

import csv
import io
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    UserContext,
    get_current_user,
    get_db,
    require_permission,
)
from app.core.exceptions import BusinessError
from app.schemas.equipo import (
    AsignacionMasivaRequest,
    ClonarEquipoRequest,
    ClonarResponse,
    EquipoResponse,
    VigenciaRequest,
    VigenciaResponse,
)
from app.services.equipo_service import EquipoService

router = APIRouter(
    prefix="/api",
    tags=["equipos"],
)


# ── Helpers ──────────────────────────────────────────────────────────


def _build_service(
    db: AsyncSession, tenant_id: UUID, actor_id: UUID
) -> EquipoService:
    return EquipoService(session=db, tenant_id=tenant_id, actor_id=actor_id)


# ═══════════════════════════════════════════════════════════════════════
# GET /api/equipos/mis-equipos — Docente ve sus asignaciones
# ═══════════════════════════════════════════════════════════════════════


@router.get(
    "/equipos/mis-equipos",
    dependencies=[Depends(require_permission("equipos:ver"))],
)
async def mis_equipos(
    materia_id: UUID | None = None,
    carrera_id: UUID | None = None,
    cohorte_id: UUID | None = None,
    rol: str | None = None,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[EquipoResponse]:
    """Retorna las asignaciones del usuario autenticado.

    La identidad se deriva del JWT (REGLA DURA #8) — nunca de
    parametros de consulta.
    """
    svc = _build_service(db, current_user.tenant_id, current_user.user_id)
    filtros: dict = {}
    if materia_id:
        filtros["materia_id"] = materia_id
    if carrera_id:
        filtros["carrera_id"] = carrera_id
    if cohorte_id:
        filtros["cohorte_id"] = cohorte_id
    if rol:
        filtros["rol"] = rol

    asignaciones = await svc.mis_equipos(current_user.user_id, filtros)
    return [EquipoResponse(**a) for a in asignaciones]


# ═══════════════════════════════════════════════════════════════════════
# GET /api/equipos — Listar todas (gestion)
# ═══════════════════════════════════════════════════════════════════════


@router.get(
    "/equipos",
    dependencies=[Depends(require_permission("equipos:asignar"))],
)
async def listar_equipos(
    materia_id: UUID | None = None,
    carrera_id: UUID | None = None,
    cohorte_id: UUID | None = None,
    usuario_id: UUID | None = None,
    rol: str | None = None,
    vigente: bool | None = None,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[EquipoResponse]:
    """Lista todas las asignaciones del tenant con nombres de contexto."""
    svc = _build_service(db, current_user.tenant_id, current_user.user_id)
    asignaciones = await svc.listar_equipos(
        materia_id=materia_id,
        carrera_id=carrera_id,
        cohorte_id=cohorte_id,
        usuario_id=usuario_id,
        rol=rol,
    )
    return [EquipoResponse(**a) for a in asignaciones]


# ═══════════════════════════════════════════════════════════════════════
# POST /api/equipos/asignacion-masiva
# ═══════════════════════════════════════════════════════════════════════


@router.post(
    "/equipos/asignacion-masiva",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("equipos:asignar"))],
)
async def crear_asignacion_masiva(
    body: AsignacionMasivaRequest,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[EquipoResponse]:
    """Asigna N usuarios a un contexto academico en bloque."""
    svc = _build_service(db, current_user.tenant_id, current_user.user_id)
    try:
        asignaciones = await svc.asignacion_masiva(body)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc.message),
        )
    from app.schemas.asignacion import AsignacionResponse

    return [
        EquipoResponse(
            id=str(a.id),
            tenant_id=str(a.tenant_id),
            usuario_id=str(a.usuario_id),
            rol=a.rol,
            materia_id=str(a.materia_id) if a.materia_id else None,
            carrera_id=str(a.carrera_id) if a.carrera_id else None,
            cohorte_id=str(a.cohorte_id) if a.cohorte_id else None,
            comisiones=a.comisiones,
            responsable_id=str(a.responsable_id) if a.responsable_id else None,
            desde=a.desde,
            hasta=a.hasta,
            estado_vigencia=_calcular_estado_vigencia(a),
            created_at=a.created_at,
            updated_at=a.updated_at,
        )
        for a in asignaciones
    ]


# ═══════════════════════════════════════════════════════════════════════
# POST /api/equipos/clonar
# ═══════════════════════════════════════════════════════════════════════


@router.post(
    "/equipos/clonar",
    dependencies=[Depends(require_permission("equipos:asignar"))],
)
async def clonar_equipo(
    body: ClonarEquipoRequest,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ClonarResponse:
    """Clona todas las asignaciones vigentes de origen a destino."""
    svc = _build_service(db, current_user.tenant_id, current_user.user_id)
    try:
        result = await svc.clonar_equipo(body)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc.message),
        )
    return result


# ═══════════════════════════════════════════════════════════════════════
# PATCH /api/equipos/vigencia
# ═══════════════════════════════════════════════════════════════════════


@router.patch(
    "/equipos/vigencia",
    dependencies=[Depends(require_permission("equipos:asignar"))],
)
async def modificar_vigencia(
    body: VigenciaRequest,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VigenciaResponse:
    """Modifica la vigencia de todas las asignaciones de un equipo."""
    svc = _build_service(db, current_user.tenant_id, current_user.user_id)
    result = await svc.modificar_vigencia(body)
    if result.afectadas == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay asignaciones para ese equipo en el contexto especificado",
        )
    return result


# ═══════════════════════════════════════════════════════════════════════
# GET /api/equipos/export
# ═══════════════════════════════════════════════════════════════════════


@router.get(
    "/equipos/export",
    dependencies=[Depends(require_permission("equipos:asignar"))],
)
async def exportar_equipo(
    materia_id: UUID,
    carrera_id: UUID,
    cohorte_id: UUID,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Exporta un equipo docente como CSV con cabeceras en espanol."""
    svc = _build_service(db, current_user.tenant_id, current_user.user_id)
    data = await svc.exportar_equipo(
        materia_id=materia_id,
        carrera_id=carrera_id,
        cohorte_id=cohorte_id,
    )

    HEADERS_ES = [
        "docente", "documento", "rol", "materia", "carrera",
        "cohorte", "comisiones", "desde", "hasta", "estado_vigencia",
    ]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=HEADERS_ES, extrasaction="ignore")
    writer.writeheader()
    if data:
        writer.writerows(data)

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                f"attachment; filename=equipo_{materia_id}_{carrera_id}_{cohorte_id}.csv"
            ),
        },
    )


# ── Helper interno ──────────────────────────────────────────────────


def _calcular_estado_vigencia(a) -> str:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    hasta = a.hasta
    desde = a.desde

    # Normalizar timezone: si el registro guardó naive, asumir UTC
    if hasta is not None:
        if hasta.tzinfo is None:
            hasta = hasta.replace(tzinfo=timezone.utc)
        if hasta < now:
            return "Vencida"
    if desde is not None:
        if desde.tzinfo is None:
            desde = desde.replace(tzinfo=timezone.utc)
        if desde > now:
            return "Sin iniciar"
    return "Vigente"
