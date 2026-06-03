"""Router de administracion de usuarios (C-07).

Endpoints protegidos con ``require_permission("admin:gestionar-usuarios")``:
- ``/api/admin/usuarios`` — CRUD de usuarios con PII enmascarada.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    UserContext,
    get_current_user,
    get_db,
    require_permission,
)
from app.core.exceptions import BusinessError
from app.core.pii import mask_alias_cbu, mask_cbu, mask_cuil, mask_dni, mask_email
from app.models.usuario import Usuario
from app.schemas.usuario import (
    UsuarioCreate,
    UsuarioListResponse,
    UsuarioResponse,
    UsuarioUpdate,
)
from app.services.usuario_service import UsuarioService

router = APIRouter(
    prefix="/api/admin",
    tags=["admin", "usuarios"],
)


# ── Helpers ──────────────────────────────────────────────────────────


def _build_service(
    db: AsyncSession, tenant_id: UUID
) -> UsuarioService:
    return UsuarioService(session=db, tenant_id=tenant_id)


def _usuario_to_response(u: Usuario) -> UsuarioResponse:
    """Convierte un modelo Usuario a response con PII enmascarada."""
    return UsuarioResponse(
        id=str(u.id),
        tenant_id=str(u.tenant_id),
        nombre=u.nombre,
        apellidos=u.apellidos,
        email=mask_email(u.email),
        dni=mask_dni(u.dni),
        cuil=mask_cuil(u.cuil),
        cbu=mask_cbu(u.cbu),
        alias_cbu=mask_alias_cbu(u.alias_cbu) if u.alias_cbu else None,
        banco=u.banco,
        regional=u.regional,
        legajo=u.legajo,
        legajo_profesional=u.legajo_profesional,
        facturador=u.facturador,
        estado=u.estado,
        created_at=u.created_at,
        updated_at=u.updated_at,
    )


# ═══════════════════════════════════════════════════════════════════════
# POST /api/admin/usuarios — Crear
# ═══════════════════════════════════════════════════════════════════════


@router.post(
    "/usuarios",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("admin:gestionar-usuarios"))],
)
async def crear_usuario(
    body: UsuarioCreate,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UsuarioResponse:
    """Crea un nuevo usuario en el tenant."""
    svc = _build_service(db, current_user.tenant_id)
    try:
        usuario = await svc.create(body)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc.message),
        )
    return _usuario_to_response(usuario)


# ═══════════════════════════════════════════════════════════════════════
# GET /api/admin/usuarios — Listar
# ═══════════════════════════════════════════════════════════════════════


@router.get(
    "/usuarios",
    dependencies=[Depends(require_permission("admin:gestionar-usuarios"))],
)
async def listar_usuarios(
    estado: Optional[str] = Query(default=None),
    nombre: Optional[str] = Query(default=None, min_length=1, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UsuarioListResponse:
    """Lista usuarios del tenant con paginacion y filtros opcionales."""
    svc = _build_service(db, current_user.tenant_id)
    usuarios = await svc.listar_con_filtros(
        estado=estado, nombre=nombre
    )
    total = len(usuarios)
    start = (page - 1) * page_size
    end = start + page_size
    items = [_usuario_to_response(u) for u in usuarios[start:end]]
    return UsuarioListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


# ═══════════════════════════════════════════════════════════════════════
# GET /api/admin/usuarios/{usuario_id} — Obtener por ID
# ═══════════════════════════════════════════════════════════════════════


@router.get(
    "/usuarios/{usuario_id}",
    dependencies=[Depends(require_permission("admin:gestionar-usuarios"))],
)
async def obtener_usuario(
    usuario_id: UUID,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UsuarioResponse:
    """Obtiene un usuario por ID.

    Si el usuario fue soft-deleteado, se retorna con estado ``Inactivo``
    y el flag ``eliminado=True`` en lugar de 404.
    """
    svc = _build_service(db, current_user.tenant_id)
    usuario = await svc.obtener(usuario_id)
    if usuario is None:
        # Podria ser un soft-delete — buscamos incluyendo eliminados
        usuario = await svc.obtener_incluyendo_eliminados(usuario_id)
        if usuario is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )
        # Soft-deleteado: retornar con estado Inactivo
        resp = _usuario_to_response(usuario)
        resp.estado = "Inactivo"
        return resp
    return _usuario_to_response(usuario)


# ═══════════════════════════════════════════════════════════════════════
# PATCH /api/admin/usuarios/{usuario_id} — Actualizar
# ═══════════════════════════════════════════════════════════════════════


@router.patch(
    "/usuarios/{usuario_id}",
    dependencies=[Depends(require_permission("admin:gestionar-usuarios"))],
)
async def actualizar_usuario(
    usuario_id: UUID,
    body: UsuarioUpdate,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UsuarioResponse:
    """Actualiza parcialmente un usuario."""
    svc = _build_service(db, current_user.tenant_id)
    try:
        usuario = await svc.actualizar(usuario_id, body)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc.message),
        )
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )
    return _usuario_to_response(usuario)


# ═══════════════════════════════════════════════════════════════════════
# DELETE /api/admin/usuarios/{usuario_id} — Soft delete
# ═══════════════════════════════════════════════════════════════════════


@router.delete(
    "/usuarios/{usuario_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("admin:gestionar-usuarios"))],
)
async def eliminar_usuario(
    usuario_id: UUID,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Realiza baja logica de un usuario."""
    svc = _build_service(db, current_user.tenant_id)
    usuario = await svc.obtener(usuario_id)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )
    await svc.soft_delete(usuario_id)
    return {"status": "deleted"}
