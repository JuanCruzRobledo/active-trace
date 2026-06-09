"""Router de asignaciones (C-07).

Endpoints protegidos con ``require_permission("equipos:asignar")``:
- ``/api/asignaciones`` — CRUD de asignaciones.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    UserContext,
    get_current_user,
    get_db,
    require_permission,
)
from app.core.exceptions import BusinessError
from app.models.asignacion import Asignacion
from app.schemas.asignacion import (
    AsignacionCreate,
    AsignacionResponse,
    AsignacionUpdate,
)
from app.services.asignacion_service import AsignacionService

router = APIRouter(
    prefix="/api",
    tags=["asignaciones"],
)


# ── Helpers ──────────────────────────────────────────────────────────


def _build_service(
    db: AsyncSession, tenant_id: UUID
) -> AsignacionService:
    return AsignacionService(session=db, tenant_id=tenant_id)


def _calcular_estado_vigencia(a: Asignacion) -> str:
    """Calcula el estado de vigencia de una asignacion.

    Returns:
        ``"Vigente"`` si la asignacion esta activa,
        ``"Vencida"`` si ``hasta`` ya paso,
        ``"Sin iniciar"`` si ``desde`` aun no llega.
    """
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    if a.hasta is not None and a.hasta < now:
        return "Vencida"
    if a.desde > now:
        return "Sin iniciar"
    return "Vigente"


def _asignacion_to_response(a: Asignacion) -> AsignacionResponse:
    return AsignacionResponse(
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


# ═══════════════════════════════════════════════════════════════════════
# POST /api/asignaciones — Crear
# ═══════════════════════════════════════════════════════════════════════


@router.post(
    "/asignaciones",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("equipos:asignar"))],
)
async def crear_asignacion(
    body: AsignacionCreate,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AsignacionResponse:
    """Crea una nueva asignacion."""
    svc = _build_service(db, current_user.tenant_id)
    try:
        asignacion = await svc.create(body)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc.message),
        )
    return _asignacion_to_response(asignacion)


# ═══════════════════════════════════════════════════════════════════════
# GET /api/asignaciones — Listar
# ═══════════════════════════════════════════════════════════════════════


@router.get(
    "/asignaciones",
    dependencies=[Depends(require_permission("equipos:asignar"))],
)
async def listar_asignaciones(
    usuario_id: UUID | None = None,
    materia_id: UUID | None = None,
    carrera_id: UUID | None = None,
    cohorte_id: UUID | None = None,
    rol: str | None = None,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AsignacionResponse]:
    """Lista asignaciones del tenant con filtros opcionales."""
    svc = _build_service(db, current_user.tenant_id)
    asignaciones = await svc.listar_por_contexto(
        materia_id=materia_id,
        carrera_id=carrera_id,
        cohorte_id=cohorte_id,
        usuario_id=usuario_id,
        rol=rol,
    )
    return [_asignacion_to_response(a) for a in asignaciones]


# ═══════════════════════════════════════════════════════════════════════
# GET /api/asignaciones/{asignacion_id} — Obtener por ID
# ═══════════════════════════════════════════════════════════════════════


@router.get(
    "/asignaciones/{asignacion_id}",
    dependencies=[Depends(require_permission("equipos:asignar"))],
)
async def obtener_asignacion(
    asignacion_id: UUID,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AsignacionResponse:
    """Obtiene una asignacion por ID."""
    svc = _build_service(db, current_user.tenant_id)
    asignacion = await svc.obtener(asignacion_id)
    if asignacion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asignacion no encontrada",
        )
    return _asignacion_to_response(asignacion)


# ═══════════════════════════════════════════════════════════════════════
# PATCH /api/asignaciones/{asignacion_id} — Actualizar
# ═══════════════════════════════════════════════════════════════════════


@router.patch(
    "/asignaciones/{asignacion_id}",
    dependencies=[Depends(require_permission("equipos:asignar"))],
)
async def actualizar_asignacion(
    asignacion_id: UUID,
    body: AsignacionUpdate,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AsignacionResponse:
    """Actualiza parcialmente una asignacion."""
    svc = _build_service(db, current_user.tenant_id)
    try:
        asignacion = await svc.actualizar(asignacion_id, body)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc.message),
        )
    if asignacion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asignacion no encontrada",
        )
    return _asignacion_to_response(asignacion)


# ═══════════════════════════════════════════════════════════════════════
# DELETE /api/asignaciones/{asignacion_id} — Soft delete
# ═══════════════════════════════════════════════════════════════════════


@router.delete(
    "/asignaciones/{asignacion_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("equipos:asignar"))],
)
async def eliminar_asignacion(
    asignacion_id: UUID,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Realiza baja logica de una asignacion."""
    svc = _build_service(db, current_user.tenant_id)
    asignacion = await svc.obtener(asignacion_id)
    if asignacion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asignacion no encontrada",
        )
    await svc.soft_delete(asignacion_id)
    return {"status": "deleted"}
