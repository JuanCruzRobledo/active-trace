"""Router Perfil Propio — GET y PATCH /api/perfil (C-20).

La identidad se resuelve SIEMPRE desde el JWT — ningun parametro de URL
o body puede alterar de quien es el perfil. Toda edicion genera PERFIL_EDITAR.
PII se enmascara en todas las respuestas.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import UserContext, get_current_user, get_db
from app.core.exceptions import BusinessError
from app.core.pii import mask_alias_cbu, mask_cbu, mask_cuil, mask_dni, mask_email
from app.models.usuario import Usuario
from app.schemas.perfil import PerfilResponse, PerfilUpdate
from app.services.perfil_service import PerfilService

router = APIRouter(
    prefix="/api/perfil",
    tags=["perfil"],
)


async def _resolve_usuario_id(db: AsyncSession, user_id: UUID) -> UUID:
    """Resuelve un user_id (JWT) a usuario.id.

    El JWT puede contener users.id (auth) o directamente usuario.id.
    """
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
            detail="Perfil de usuario no encontrado",
        )
    return resolved


def _mask_usuario(u: Usuario) -> PerfilResponse:
    return PerfilResponse(
        id=u.id,
        tenant_id=u.tenant_id,
        nombre=u.nombre,
        apellidos=u.apellidos,
        email=mask_email(u.email) if u.email else None,
        dni=mask_dni(u.dni) if u.dni else None,
        cuil=mask_cuil(u.cuil) if u.cuil else None,
        banco=u.banco,
        cbu=mask_cbu(u.cbu) if u.cbu else None,
        alias_cbu=mask_alias_cbu(u.alias_cbu) if u.alias_cbu else None,
        regional=u.regional,
        legajo_profesional=u.legajo_profesional,
        facturador=u.facturador,
        estado=u.estado,
    )


@router.get("", response_model=PerfilResponse)
async def obtener_perfil(
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(get_current_user),
) -> PerfilResponse:
    """Retorna el perfil del usuario autenticado (PII enmascarada)."""
    usuario_id = await _resolve_usuario_id(db, ctx.user_id)
    svc = PerfilService(session=db, tenant_id=ctx.tenant_id, actor_id=usuario_id)
    try:
        usuario = await svc.obtener_mio(usuario_id)
    except BusinessError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _mask_usuario(usuario)


@router.patch("", response_model=PerfilResponse)
async def actualizar_perfil(
    body: PerfilUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(get_current_user),
) -> PerfilResponse:
    """Actualiza parcialmente el perfil del usuario autenticado."""
    usuario_id = await _resolve_usuario_id(db, ctx.user_id)
    svc = PerfilService(session=db, tenant_id=ctx.tenant_id, actor_id=usuario_id)
    try:
        usuario = await svc.actualizar_mio(usuario_id, body)
    except BusinessError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _mask_usuario(usuario)
