"""Router de Tareas Internas — CRUD, cambio de estado, comentarios (C-16).

Endpoints:
- POST /api/tareas — crear tarea (tareas:gestionar).
- GET /api/tareas/mias — timeline del usuario autenticado.
- GET /api/tareas — listar todas con filtros (tareas:gestionar).
- GET /api/tareas/{id} — detalle con comentarios.
- PATCH /api/tareas/{id}/estado — cambiar estado.
- POST /api/tareas/{id}/comentarios — agregar comentario.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    UserContext,
    get_current_user,
    get_db,
    require_permission,
)
from app.core.exceptions import BusinessError
from app.models.usuario import Usuario
from app.schemas.tareas import (
    ComentarioCreate,
    TareaCreate,
    TareaEstadoUpdate,
)
from app.services.tarea_service import TareaService

router = APIRouter(
    prefix="/api/tareas",
    tags=["tareas"],
)


def _build_service(
    db: AsyncSession, ctx: UserContext
) -> TareaService:
    """Construye TareaService.

    Args:
        db: Sesion de base de datos.
        ctx: Contexto de usuario (JWT).
    """
    return TareaService(
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
    row = await db.get(Usuario, user_id)
    if row is not None:
        return row.id

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


# ── Crear tarea ────────────────────────────────────────────────────────────


@router.post("", status_code=status.HTTP_201_CREATED)
async def crear_tarea(
    body: TareaCreate,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("tareas:gestionar")),
) -> dict:
    """Crea una nueva tarea interna.

    Requiere permiso ``tareas:gestionar``.
    """
    usuario_id = await _resolve_usuario_id(db, ctx.user_id)
    svc = _build_service(db, ctx)
    svc.actor_id = usuario_id
    try:
        return await svc.crear_tarea(body)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ── Timeline (MUST be before /{tarea_id}) ──────────────────────────────────


@router.get("/mias")
async def listar_mias(
    estado: str | None = Query(None),
    materia_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(get_current_user),
) -> dict:
    """Timeline de tareas asignadas al usuario autenticado.

    No requiere permiso especial — el acceso esta implícito por ser
    el usuario asignado.
    """
    usuario_id = await _resolve_usuario_id(db, ctx.user_id)
    svc = _build_service(db, ctx)
    svc.actor_id = usuario_id
    return await svc.listar_mias(
        estado=estado,
        materia_id=materia_id,
    )


# ── Listar todas (admin) ───────────────────────────────────────────────────


@router.get("")
async def listar_todas(
    estado: str | None = Query(None),
    materia_id: UUID | None = Query(None),
    asignado_a: UUID | None = Query(None),
    asignado_por: UUID | None = Query(None),
    busqueda: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("tareas:gestionar")),
) -> dict:
    """Lista todas las tareas del tenant con filtros combinables.

    Requiere permiso ``tareas:gestionar``.
    """
    svc = _build_service(db, ctx)
    return await svc.listar_todas(
        estado=estado,
        materia_id=materia_id,
        asignado_a=asignado_a,
        asignado_por=asignado_por,
        busqueda=busqueda,
    )


# ── Operaciones sobre tarea individual ─────────────────────────────────────


@router.get("/{tarea_id}")
async def obtener_tarea(
    tarea_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(get_current_user),
) -> dict:
    """Obtiene detalle de una tarea con sus comentarios.

    Verifica que el usuario tenga acceso (asignado o tareas:gestionar).
    """
    usuario_id = await _resolve_usuario_id(db, ctx.user_id)
    svc = _build_service(db, ctx)
    svc.actor_id = usuario_id
    try:
        return await svc.obtener_tarea(tarea_id)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.patch("/{tarea_id}/estado")
async def cambiar_estado(
    tarea_id: UUID,
    body: TareaEstadoUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(get_current_user),
) -> dict:
    """Cambia el estado de una tarea.

    Verifica que el usuario tenga acceso (asignado o tareas:gestionar)
    y que la transicion sea valida.
    """
    usuario_id = await _resolve_usuario_id(db, ctx.user_id)
    svc = _build_service(db, ctx)
    svc.actor_id = usuario_id
    try:
        return await svc.cambiar_estado(tarea_id, body.nuevo_estado)
    except BusinessError as exc:
        if "no encontrada" in str(exc).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.post("/{tarea_id}/comentarios", status_code=status.HTTP_201_CREATED)
async def agregar_comentario(
    tarea_id: UUID,
    body: ComentarioCreate,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(get_current_user),
) -> dict:
    """Agrega un comentario a una tarea.

    Verifica que el usuario tenga acceso (asignado o tareas:gestionar).
    """
    usuario_id = await _resolve_usuario_id(db, ctx.user_id)
    svc = _build_service(db, ctx)
    svc.actor_id = usuario_id
    try:
        return await svc.agregar_comentario(tarea_id, body)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
