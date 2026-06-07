"""Router Inbox — GET/POST /api/inbox, POST /api/inbox/{id}/mensajes (C-20).

Las rutas estaticas (/api/inbox) van ANTES de las dinamicas (/api/inbox/{id})
para evitar que 'mensajes' sea interpretado como hilo_id.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import UserContext, get_current_user, get_db
from app.core.exceptions import BusinessError
from app.models.usuario import Usuario
from app.schemas.mensajeria import (
    HiloConMensajesResponse,
    HiloCreate,
    HiloListResponse,
    MensajeCreate,
    MensajeResponse,
)
from app.services.mensajeria_service import MensajeriaService

router = APIRouter(
    prefix="/api/inbox",
    tags=["inbox"],
)


async def _resolve_usuario_id(db: AsyncSession, user_id: UUID) -> UUID:
    """Resuelve un user_id (JWT) a usuario.id."""
    row = await db.get(Usuario, user_id)
    if row is not None:
        return row.id

    result = await db.execute(
        select(Usuario.id).where(Usuario.auth_user_id == user_id)
    )
    resolved = result.scalar_one_or_none()
    if resolved is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )
    return resolved


# ── GET /api/inbox — listar hilos propios ─────────────────────────────────


@router.get("", response_model=HiloListResponse)
async def listar_inbox(
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(get_current_user),
) -> HiloListResponse:
    """Lista todos los hilos donde el usuario es participante."""
    usuario_id = await _resolve_usuario_id(db, ctx.user_id)
    svc = MensajeriaService(session=db, tenant_id=ctx.tenant_id, actor_id=usuario_id)
    return await svc.listar_inbox()


# ── POST /api/inbox — crear hilo ──────────────────────────────────────────


@router.post("", response_model=HiloConMensajesResponse, status_code=status.HTTP_201_CREATED)
async def crear_hilo(
    body: HiloCreate,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(get_current_user),
) -> HiloConMensajesResponse:
    """Crea un nuevo hilo con el primer mensaje."""
    usuario_id = await _resolve_usuario_id(db, ctx.user_id)
    svc = MensajeriaService(session=db, tenant_id=ctx.tenant_id, actor_id=usuario_id)
    try:
        return await svc.crear_hilo(body)
    except BusinessError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


# ── GET /api/inbox/{hilo_id} — leer hilo ─────────────────────────────────


@router.get("/{hilo_id}", response_model=HiloConMensajesResponse)
async def obtener_hilo(
    hilo_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(get_current_user),
) -> HiloConMensajesResponse:
    """Retorna un hilo completo con mensajes (solo para participantes)."""
    usuario_id = await _resolve_usuario_id(db, ctx.user_id)
    svc = MensajeriaService(session=db, tenant_id=ctx.tenant_id, actor_id=usuario_id)
    try:
        return await svc.obtener_hilo(hilo_id)
    except BusinessError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# ── POST /api/inbox/{hilo_id}/mensajes — responder ───────────────────────


@router.post(
    "/{hilo_id}/mensajes",
    response_model=MensajeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def responder_hilo(
    hilo_id: UUID,
    body: MensajeCreate,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(get_current_user),
) -> MensajeResponse:
    """Agrega un mensaje a un hilo existente (solo para participantes)."""
    usuario_id = await _resolve_usuario_id(db, ctx.user_id)
    svc = MensajeriaService(session=db, tenant_id=ctx.tenant_id, actor_id=usuario_id)
    try:
        return await svc.responder(hilo_id, body)
    except BusinessError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
