"""Router de comunicaciones — preview, envio, cancelacion y aprobacion (C-12).

Endpoints:
- ``POST /api/comunicaciones/preview`` — preview de contenido.
- ``POST /api/comunicaciones/enviar`` — envio masivo (protegido).
- ``POST /api/comunicaciones/enviar-individual`` — envio individual (protegido).
- ``GET /api/comunicaciones/mis-envios`` — listado personal.
- ``GET /api/comunicaciones/{lote_id}`` — estado de un lote.
- ``PUT /api/comunicaciones/{lote_id}/aprobar`` — aprobar/rechazar lote.
- ``POST /api/comunicaciones/{comunicacion_id}/cancelar`` — cancelar comunicacion individual.
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
from app.schemas.comunicacion import (
    AprobarRequest,
    CancelarResponse,
    EnvioIndividualRequest,
    EnvioIndividualResponse,
    EnvioRequest,
    EnvioResponse,
    LoteResponse,
    MisEnviosResponse,
    PreviewRequest,
    PreviewResponse,
)
from app.services.comunicacion_service import ComunicacionService

router = APIRouter(
    prefix="/api/comunicaciones",
    tags=["comunicaciones"],
)


def _build_service(db: AsyncSession, tenant_id: UUID) -> ComunicacionService:
    return ComunicacionService(session=db, tenant_id=tenant_id)


@router.post("/preview", response_model=PreviewResponse)
async def crear_preview(
    body: PreviewRequest,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("comunicacion:enviar")),
) -> PreviewResponse:
    """Genera un preview del contenido y devuelve un token de validacion."""
    service = _build_service(db, ctx.tenant_id)
    result = await service.generar_preview(
        asunto=body.asunto,
        cuerpo=body.cuerpo,
        destinatarios=[d.model_dump() for d in body.destinatarios],
    )
    return PreviewResponse(**result)


@router.post("/enviar", response_model=EnvioResponse)
async def enviar_comunicacion(
    body: EnvioRequest,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("comunicacion:enviar")),
) -> EnvioResponse:
    """Encola un envio masivo de comunicaciones."""
    if not body.acepta_terminos:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Debe aceptar los terminos de comunicacion",
        )

    service = _build_service(db, ctx.tenant_id)
    try:
        result = await service.encolar_envio(
            usuario_id=ctx.user_id,
            tenant_id=ctx.tenant_id,
            preview_token=body.preview_token,
            asunto=body.asunto,
            cuerpo=body.cuerpo,
            materia_id=body.materia_id,
            destinatarios=[d.model_dump() for d in body.destinatarios],
            roles=ctx.roles,
            requiere_aprobacion=body.requiere_aprobacion,
        )
        return EnvioResponse(**result)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/enviar-individual", response_model=EnvioIndividualResponse)
async def enviar_comunicacion_individual(
    body: EnvioIndividualRequest,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("comunicacion:enviar")),
) -> EnvioIndividualResponse:
    """Encola una comunicacion individual."""
    if not body.acepta_terminos:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Debe aceptar los terminos de comunicacion",
        )

    service = _build_service(db, ctx.tenant_id)
    try:
        result = await service.encolar_envio_individual(
            usuario_id=ctx.user_id,
            tenant_id=ctx.tenant_id,
            preview_token=body.preview_token,
            asunto=body.asunto,
            cuerpo=body.cuerpo,
            materia_id=body.materia_id,
            entrada_padron_id=body.entrada_padron_id,
            roles=ctx.roles,
        )
        return EnvioIndividualResponse(
            comunicacion_id=result["lote_id"],
            estado=result.get("estado", "Pendiente"),
        )
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/mis-envios", response_model=MisEnviosResponse)
async def mis_envios(
    pagina: int = Query(1, ge=1),
    tamano: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("comunicacion:enviar")),
) -> MisEnviosResponse:
    """Lista los envios realizados por el usuario actual."""
    service = _build_service(db, ctx.tenant_id)
    result = await service.obtener_mis_envios(
        usuario_id=ctx.user_id,
        tenant_id=ctx.tenant_id,
        pagina=pagina,
        tamano=tamano,
    )
    return MisEnviosResponse(**result)


@router.get("/{lote_id}", response_model=LoteResponse)
async def obtener_estado_lote(
    lote_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("comunicacion:enviar")),
) -> LoteResponse:
    """Obtiene el estado detallado de un lote de comunicaciones."""
    service = _build_service(db, ctx.tenant_id)
    try:
        result = await service.obtener_estado_lote(
            tenant_id=ctx.tenant_id, lote_id=lote_id
        )
        return LoteResponse(**result)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.put("/{lote_id}/aprobar", response_model=dict)
async def aprobar_o_rechazar_lote(
    lote_id: UUID,
    body: AprobarRequest,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("comunicacion:aprobar")),
) -> dict:
    """Aprueba o rechaza un lote que requiere aprobacion."""
    service = _build_service(db, ctx.tenant_id)
    try:
        if body.accion == "aprobar":
            await service.aprobar_lote(lote_id=lote_id, aprobador_id=ctx.user_id)
        else:
            await service.rechazar_lote(lote_id=lote_id, aprobador_id=ctx.user_id)
        return {"lote_id": str(lote_id), "accion": body.accion, "resultado": "ok"}
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/{comunicacion_id}/cancelar", response_model=CancelarResponse)
async def cancelar_comunicacion(
    comunicacion_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("comunicacion:enviar")),
) -> CancelarResponse:
    """Cancela una comunicacion pendiente (individual)."""
    service = _build_service(db, ctx.tenant_id)
    try:
        result = await service.cancelar_comunicacion(
            comunicacion_id=comunicacion_id, usuario_id=ctx.user_id
        )
        return result
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
