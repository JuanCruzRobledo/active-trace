"""Router de Encuentros — slots e instancias de encuentro sincrónico (C-13).

Endpoints:
- POST /api/encuentros/slots — crear slot recurrente o único.
- GET /api/encuentros/slots — listar slots.
- PATCH /api/encuentros/slots/{slot_id} — editar slot.
- DELETE /api/encuentros/slots/{slot_id} — eliminar slot (soft-delete).
- POST /api/encuentros/instancias — crear instancia independiente.
- GET /api/encuentros/instancias — listar instancias.
- PATCH /api/encuentros/instancias/{instancia_id} — editar instancia.
- GET /api/encuentros/{materia_id}/exportar-aula — exportar HTML para LMS.
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
from app.schemas.encuentros import (
    EncuentroListResponse,
    ExportarAulaResponse,
    InstanciaEncuentroCreate,
    InstanciaEncuentroResponse,
    InstanciaEncuentroUpdate,
    SlotEncuentroCreate,
    SlotEncuentroCreateUnico,
    SlotEncuentroResponse,
    SlotEncuentroUpdate,
)
from app.services.encuentro_service import EncuentroService

router = APIRouter(
    prefix="/api/encuentros",
    tags=["encuentros"],
)


def _build_service(
    db: AsyncSession, ctx: UserContext
) -> EncuentroService:
    return EncuentroService(
        session=db,
        tenant_id=ctx.tenant_id,
        actor_id=ctx.user_id,
        roles=ctx.roles,
    )


# ── Slots ──────────────────────────────────────────────────────────────


@router.post("/slots", status_code=status.HTTP_201_CREATED)
async def crear_slot(
    body: SlotEncuentroCreate,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("encuentros:gestionar")),
) -> dict:
    """Crea un slot recurrente con generación automática de instancias.

    Genera N instancias (una por semana) a partir de fecha_inicio.
    """
    service = _build_service(db, ctx)
    try:
        slot, instancias = await service.crear_slot_recurrente(body)
        return {"slot": slot, "instancias": instancias}
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/slots")
async def listar_slots(
    materia_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("encuentros:gestionar")),
) -> dict:
    """Lista slots del usuario/tenant."""
    service = _build_service(db, ctx)
    result = await service.listar_slots(materia_id=materia_id)
    return result


@router.patch("/slots/{slot_id}")
async def editar_slot(
    slot_id: UUID,
    body: SlotEncuentroUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("encuentros:gestionar")),
) -> dict:
    """Edita un slot sin afectar instancias ya generadas."""
    service = _build_service(db, ctx)
    try:
        return await service.editar_slot(slot_id, body)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.delete("/slots/{slot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_slot(
    slot_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("encuentros:gestionar")),
) -> None:
    """Soft-delete de slot + todas sus instancias."""
    service = _build_service(db, ctx)
    try:
        await service.eliminar_slot(slot_id)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ── Instancias ─────────────────────────────────────────────────────────


@router.post("/instancias", status_code=status.HTTP_201_CREATED)
async def crear_instancia(
    body: InstanciaEncuentroCreate,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("encuentros:gestionar")),
) -> dict:
    """Crea una instancia de encuentro independiente (sin slot)."""
    service = _build_service(db, ctx)
    try:
        result = await service.crear_instancia_independiente(
            materia_id=body.materia_id,
            titulo=body.titulo,
            fecha=body.fecha,
            hora=body.hora,
            meet_url=body.meet_url,
        )
        return result
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/instancias")
async def listar_instancias(
    materia_id: UUID | None = Query(None),
    slot_id: UUID | None = Query(None),
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    estado: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("encuentros:gestionar")),
) -> dict:
    """Lista instancias con filtros."""
    service = _build_service(db, ctx)
    result = await service.listar_instancias(
        materia_id=materia_id,
        slot_id=slot_id,
        desde=desde,
        hasta=hasta,
        estado=estado,
    )
    return result


@router.patch("/instancias/{instancia_id}")
async def editar_instancia(
    instancia_id: UUID,
    body: InstanciaEncuentroUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("encuentros:gestionar")),
) -> dict:
    """Edita una instancia (estado, meet_url, video_url, comentario)."""
    service = _build_service(db, ctx)
    try:
        return await service.editar_instancia(instancia_id, body)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ── Exportación ────────────────────────────────────────────────────────


@router.get("/{materia_id}/exportar-aula")
async def exportar_aula(
    materia_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("encuentros:gestionar")),
) -> dict:
    """Genera bloque HTML embebible con encuentros de la materia."""
    service = _build_service(db, ctx)
    try:
        return await service.generar_html_aula(materia_id)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
