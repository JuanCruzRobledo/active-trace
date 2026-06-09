"""Router de Avisos — CRUD, timeline, acknowledgment y tracking (C-15).

Endpoints:
- POST /api/avisos — crear aviso (avisos:gestionar).
- GET /api/avisos — listar avisos del tenant (avisos:gestionar).
- GET /api/avisos/{id} — detalle de aviso (avisos:ver).
- PUT /api/avisos/{id} — editar aviso (avisos:gestionar).
- DELETE /api/avisos/{id} — eliminar aviso (avisos:gestionar).
- GET /api/avisos/timeline — timeline del usuario (avisos:ver).
- POST /api/avisos/{id}/acknowledge — confirmar lectura (avisos:ver).
- GET /api/avisos/{id}/tracking — tracking de acuses (avisos:gestionar).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    UserContext,
    get_db,
    require_permission,
)
from app.core.exceptions import BusinessError
from app.models.usuario import Usuario
from app.schemas.avisos import (
    AvisoCreate,
    AvisoUpdate,
)
from app.services.aviso_service import AvisoService

router = APIRouter(
    prefix="/api/avisos",
    tags=["avisos"],
)


def _build_service(
    db: AsyncSession, ctx: UserContext
) -> AvisoService:
    """Construye AvisoService.

    Args:
        db: Sesion de base de datos.
        ctx: Contexto de usuario (JWT).
    """
    return AvisoService(
        session=db,
        tenant_id=ctx.tenant_id,
        actor_id=ctx.user_id,
        roles=ctx.roles,
    )


async def _resolve_usuario_id(
    db: AsyncSession, user_id: UUID
) -> UUID:
    """Resuelve un user_id a ``usuario.id``.

    El JWT puede contener ``users.id`` (auth) o directamente ``usuario.id``
    (tests). Probamos ambas vias:
    1. Si ``user_id`` ya es un ``usuario.id`` → lo retorna directo.
    2. Si no, busca por ``usuario.auth_user_id == user_id``.
    """
    # 1. Probar si ya es usuario.id
    row = await db.get(Usuario, user_id)
    if row is not None:
        return row.id

    # 2. Probar por auth_user_id (FK → users.id)
    result = await db.execute(
        select(Usuario.id).where(Usuario.auth_user_id == user_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil de usuario no encontrado",
        )
    return row


async def _get_materias_cohortes_usuario(
    db: AsyncSession, usuario_id: UUID, tenant_id: UUID
) -> tuple[list[UUID], list[UUID]]:
    """Obtiene las materias y cohortes asociadas a un usuario.

    Args:
        db: Sesion de base de datos.
        usuario_id: UUID del usuario.
        tenant_id: UUID del tenant.

    Returns:
        Tuple con (materia_ids, cohorte_ids).
    """
    from app.models.asignacion import Asignacion  # noqa: PLC0415

    result = await db.execute(
        select(
            Asignacion.materia_id,
            Asignacion.cohorte_id,
        ).where(
            Asignacion.usuario_id == usuario_id,
            Asignacion.tenant_id == tenant_id,
            Asignacion.deleted_at.is_(None),
        )
    )
    rows = result.all()
    materia_ids = list({r.materia_id for r in rows if r.materia_id is not None})
    cohorte_ids = list({r.cohorte_id for r in rows if r.cohorte_id is not None})
    return materia_ids, cohorte_ids


# ── CRUD ────────────────────────────────────────────────────────────────


@router.post("", status_code=status.HTTP_201_CREATED)
async def crear_aviso(
    body: AvisoCreate,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("avisos:gestionar")),
) -> dict:
    """Crea un nuevo aviso institucional."""
    service = _build_service(db, ctx)
    try:
        return await service.crear_aviso(body)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("")
async def listar_avisos(
    materia_id: UUID | None = Query(None),
    cohorte_id: UUID | None = Query(None),
    alcance: str | None = Query(None),
    severidad: str | None = Query(None),
    activo: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("avisos:gestionar")),
) -> dict:
    """Lista avisos del tenant con filtros opcionales."""
    service = _build_service(db, ctx)
    return await service.listar_avisos(
        materia_id=materia_id,
        cohorte_id=cohorte_id,
        alcance=alcance,
        severidad=severidad,
        activo=activo,
    )


# ── Timeline (MUST be before /{aviso_id} routes to avoid path conflict) ──


@router.get("/timeline")
async def obtener_timeline(
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("avisos:ver")),
) -> dict:
    """Timeline de avisos activos para el usuario autenticado."""
    service = _build_service(db, ctx)
    usuario_id = await _resolve_usuario_id(db, ctx.user_id)
    materia_ids, cohorte_ids = await _get_materias_cohortes_usuario(
        db, usuario_id, ctx.tenant_id
    )
    return await service.obtener_timeline(
        usuario_id=usuario_id,
        materia_ids=materia_ids,
        cohorte_ids=cohorte_ids,
    )


# ── CRUD individual ─────────────────────────────────────────────────────


@router.get("/{aviso_id}")
async def obtener_aviso(
    aviso_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("avisos:ver")),
) -> dict:
    """Obtiene detalle de un aviso con metricas."""
    service = _build_service(db, ctx)
    try:
        return await service.obtener_aviso(aviso_id)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.put("/{aviso_id}")
async def editar_aviso(
    aviso_id: UUID,
    body: AvisoUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("avisos:gestionar")),
) -> dict:
    """Edita un aviso existente (solo si no tiene acknowledgments)."""
    service = _build_service(db, ctx)
    try:
        return await service.editar_aviso(aviso_id, body)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.delete("/{aviso_id}")
async def eliminar_aviso(
    aviso_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("avisos:gestionar")),
) -> dict:
    """Elimina un aviso (hard delete si no tiene acuses, soft delete si ya tuvo)."""
    service = _build_service(db, ctx)
    try:
        return await service.eliminar_aviso(aviso_id)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


# ── Acknowledgment ──────────────────────────────────────────────────────


@router.post("/{aviso_id}/acknowledge")
async def acknowledge_aviso(
    aviso_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("avisos:ver")),
) -> dict:
    """Confirma la lectura de un aviso que requiere acuse."""
    service = _build_service(db, ctx)
    try:
        return await service.acknowledge(aviso_id)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


# ── Tracking ────────────────────────────────────────────────────────────


@router.get("/{aviso_id}/tracking")
async def tracking_aviso(
    aviso_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("avisos:gestionar")),
) -> dict:
    """Tracking de acknowledgments de un aviso."""
    service = _build_service(db, ctx)
    try:
        return await service.obtener_tracking(aviso_id)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
