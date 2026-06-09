"""Router de Guardias — registro y consulta de guardias de atención (C-13).

Endpoints:
- POST /api/guardias — registrar guardia.
- GET /api/guardias — listar guardias con filtros.
- PATCH /api/guardias/{guardia_id} — editar estado/comentarios.
- GET /api/guardias/exportar — exportar guardias.
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
from app.core.exceptions import BusinessError
from app.schemas.guardias import (
    GuardiaCreate,
    GuardiaListResponse,
    GuardiaResponse,
    GuardiaUpdate,
)
from app.services.guardia_service import GuardiaService

router = APIRouter(
    prefix="/api/guardias",
    tags=["guardias"],
)


def _build_service(
    db: AsyncSession, ctx: UserContext
) -> GuardiaService:
    return GuardiaService(
        session=db,
        tenant_id=ctx.tenant_id,
        actor_id=ctx.user_id,
        roles=ctx.roles,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def registrar_guardia(
    body: GuardiaCreate,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("guardias:registrar")),
) -> dict:
    """Registra una nueva guardia."""
    service = _build_service(db, ctx)
    try:
        return await service.registrar_guardia(datos=body)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("")
async def listar_guardias(
    materia_id: UUID | None = Query(None),
    usuario_id: UUID | None = Query(None),
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    estado: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("guardias:registrar")),
) -> dict:
    """Lista guardias con filtros."""
    service = _build_service(db, ctx)
    result = await service.listar_guardias(
        materia_id=materia_id,
        usuario_id=usuario_id,
        desde=desde,
        hasta=hasta,
        estado=estado,
    )
    return result


@router.patch("/{guardia_id}")
async def editar_guardia(
    guardia_id: UUID,
    body: GuardiaUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("guardias:registrar")),
) -> dict:
    """Edita estado y/o comentarios de una guardia."""
    service = _build_service(db, ctx)
    try:
        return await service.editar_guardia(guardia_id, body)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/exportar")
async def exportar_guardias(
    materia_id: UUID | None = Query(None),
    usuario_id: UUID | None = Query(None),
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    estado: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("guardias:ver-admin")),
) -> list:
    """Exporta guardias con filtros (requiere guardias:ver-admin)."""
    service = _build_service(db, ctx)
    return await service.exportar_guardias(
        materia_id=materia_id,
        usuario_id=usuario_id,
        desde=desde,
        hasta=hasta,
        estado=estado,
    )
