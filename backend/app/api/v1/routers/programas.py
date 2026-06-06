"""Router de Programas de Materia — CRUD de documentos oficiales (C-17).

Endpoints:
- POST /api/programas — subir programa (estructura:gestionar).
- GET /api/programas — listar programas con filtros.
- GET /api/programas/{id} — obtener detalle (incluye referencia_archivo).
- DELETE /api/programas/{id} — eliminar programa (hard delete, estructura:gestionar).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    UserContext,
    get_db,
    require_permission,
)
from app.core.exceptions import BusinessError
from app.schemas.programas import ProgramaMateriaCreate
from app.services.programa_service import ProgramaService

router = APIRouter(
    prefix="/api/programas",
    tags=["programas"],
)


def _build_service(
    db: AsyncSession, ctx: UserContext
) -> ProgramaService:
    """Construye ProgramaService.

    Args:
        db: Sesion de base de datos.
        ctx: Contexto de usuario (JWT).
    """
    return ProgramaService(
        session=db,
        tenant_id=ctx.tenant_id,
        actor_id=ctx.user_id,
        roles=ctx.roles,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def subir_programa(
    body: ProgramaMateriaCreate,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("estructura:gestionar")),
) -> dict:
    """Sube un nuevo programa de materia.

    Requiere permiso ``estructura:gestionar``.
    """
    svc = _build_service(db, ctx)
    try:
        return await svc.subir_programa(body)
    except BusinessError as exc:
        msg = str(exc)
        if "ya existe" in msg.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=msg,
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        ) from exc


@router.get("")
async def listar_programas(
    materia_id: UUID | None = Query(None),
    carrera_id: UUID | None = Query(None),
    cohorte_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("estructura:gestionar")),
) -> dict:
    """Lista programas de materia con filtros combinables.

    Requiere permiso ``estructura:gestionar``.
    Retorna items sin ``referencia_archivo`` (se obtiene por detalle).
    """
    svc = _build_service(db, ctx)
    return await svc.listar_programas(
        materia_id=materia_id,
        carrera_id=carrera_id,
        cohorte_id=cohorte_id,
    )


@router.get("/{programa_id}")
async def obtener_programa(
    programa_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("estructura:gestionar")),
) -> dict:
    """Obtiene el detalle completo de un programa de materia.

    Requiere permiso ``estructura:gestionar``.
    Incluye ``referencia_archivo`` en la respuesta.
    """
    svc = _build_service(db, ctx)
    try:
        return await svc.obtener_programa(programa_id)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.delete("/{programa_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_programa(
    programa_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("estructura:gestionar")),
) -> None:
    """Elimina fisicamente un programa de materia (hard delete).

    Requiere permiso ``estructura:gestionar``.
    Registra audit log ``PROGRAMA_ELIMINAR``.
    """
    svc = _build_service(db, ctx)
    try:
        await svc.eliminar_programa(programa_id)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
