"""Router de importacion de calificaciones y configuracion de umbrales (C-10).

Endpoints protegidos con ``require_permission("calificaciones:importar")``:
- ``POST /api/calificaciones/importar/preview`` — preview de importacion.
- ``POST /api/calificaciones/importar/confirm`` — confirmar importacion.
- ``POST /api/calificaciones/finalizacion`` — procesar finalizacion (RN-07, RN-08).
- ``GET /api/calificaciones/umbral`` — consultar umbral de aprobacion.
- ``PUT /api/calificaciones/umbral`` — configurar umbral de aprobacion.
"""

from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    UserContext,
    get_current_user,
    get_db,
    require_permission,
)
from app.core.exceptions import BusinessError
from app.models.asignacion import Asignacion
from app.repositories.asignacion_repository import AsignacionRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.umbral_materia_repository import UmbralMateriaRepository
from app.schemas.calificaciones import (
    ConfirmResponse,
    FinalizacionResponse,
    PreviewResponse,
    UmbralConfigRequest,
    UmbralMateriaResponse,
    UmbralResponse,
)
from app.services.audit_service import ACCION_CALIFICACIONES_IMPORTAR, AuditService
from app.services.calificacion_service import CalificacionService
from app.services.umbral_service import UmbralService
from app.core.config import Settings

router = APIRouter(
    prefix="/api/calificaciones",
    tags=["calificaciones"],
)


# ── Helpers ──────────────────────────────────────────────────────────


def _build_calificacion_service(db: AsyncSession, tenant_id: UUID) -> CalificacionService:
    return CalificacionService(session=db, tenant_id=tenant_id)


def _build_umbral_service(db: AsyncSession, tenant_id: UUID) -> UmbralService:
    return UmbralService(session=db, tenant_id=tenant_id)


def _build_audit_service(db: AsyncSession, tenant_id: UUID, settings: Settings) -> AuditService:
    repo = AuditLogRepository(db, tenant_id=tenant_id)
    return AuditService(audit_log_repo=repo, settings=settings)


async def _validar_scope_umbral(
    db: AsyncSession,
    asignacion_id: UUID,
    current_user: UserContext,
) -> None:
    """Valida que el usuario tenga alcance sobre la asignacion.

    COORDINADOR/ADMIN pueden ver cualquier asignacion.
    PROFESOR solo puede ver sus propias asignaciones.
    """
    es_admin = "COORDINADOR" in current_user.roles or "ADMIN" in current_user.roles
    if es_admin:
        return

    asig_repo = AsignacionRepository(db, Asignacion, current_user.tenant_id)
    asignaciones = await asig_repo.list_by_usuario(current_user.user_id)
    if not any(a.id == asignacion_id for a in asignaciones):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para esta asignacion",
        )


# ═══════════════════════════════════════════════════════════════════════
# POST /api/calificaciones/importar/preview
# ═══════════════════════════════════════════════════════════════════════


@router.post(
    "/importar/preview",
    response_model=PreviewResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("calificaciones:importar"))],
)
async def importar_preview(
    materia_id: UUID = Form(...),
    file: UploadFile = File(...),
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PreviewResponse:
    """Procesa un archivo y retorna preview con actividades detectadas."""
    svc = _build_calificacion_service(db, current_user.tenant_id)
    data = await file.read()

    if not data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El archivo esta vacio",
        )

    try:
        preview = await svc.importar_preview(data, file.filename or "import.xlsx", materia_id)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    return PreviewResponse(**preview)


# ═══════════════════════════════════════════════════════════════════════
# POST /api/calificaciones/importar/confirm
# ═══════════════════════════════════════════════════════════════════════


@router.post(
    "/importar/confirm",
    response_model=ConfirmResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("calificaciones:importar"))],
)
async def importar_confirm(
    preview_token: str = Form(...),
    materia_id: UUID = Form(...),
    actividades_seleccionadas: str = Form(...),
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConfirmResponse:
    """Confirma la importacion y persiste las calificaciones."""
    svc = _build_calificacion_service(db, current_user.tenant_id)

    try:
        actividades: list[str] = json.loads(actividades_seleccionadas)
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="actividades_seleccionadas debe ser un JSON array de strings",
        )

    try:
        result = await svc.importar_confirm(
            preview_token=preview_token,
            materia_id=materia_id,
            actividades_seleccionadas=actividades,
            usuario_id=current_user.user_id,
        )
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    settings = Settings()  # type: ignore[call-arg]
    audit_svc = _build_audit_service(db, current_user.tenant_id, settings)
    await audit_svc.register(
        accion=ACCION_CALIFICACIONES_IMPORTAR,
        actor_id=current_user.user_id,
        tenant_id=current_user.tenant_id,
        materia_id=materia_id,
        filas_afectadas=result["calificaciones_importadas"],
        detalle={
            "actividades": result["actividades"],
            "preview_token": preview_token,
        },
    )

    return ConfirmResponse(**result)


# ═══════════════════════════════════════════════════════════════════════
# POST /api/calificaciones/finalizacion
# ═══════════════════════════════════════════════════════════════════════


@router.post(
    "/finalizacion",
    response_model=FinalizacionResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("calificaciones:importar"))],
)
async def procesar_finalizacion(
    materia_id: UUID = Form(...),
    file: UploadFile = File(...),
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FinalizacionResponse:
    """Procesa un archivo de finalizacion y detecta entregas sin calificar."""
    svc = _build_calificacion_service(db, current_user.tenant_id)
    data = await file.read()

    if not data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El archivo esta vacio",
        )

    try:
        result = await svc.procesar_finalizacion(data, file.filename or "finalizacion.xlsx", materia_id)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    return FinalizacionResponse(**result)


# ═══════════════════════════════════════════════════════════════════════
# GET /api/calificaciones/umbral
# ═══════════════════════════════════════════════════════════════════════


@router.get(
    "/umbral",
    response_model=UmbralResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("calificaciones:importar"))],
)
async def obtener_umbral(
    materia_id: UUID = Query(...),
    asignacion_id: UUID = Query(...),
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UmbralResponse:
    """Obtiene la configuracion de umbral para una asignacion+materia."""
    await _validar_scope_umbral(db, asignacion_id, current_user)

    svc = _build_umbral_service(db, current_user.tenant_id)
    result = await svc.obtener_umbral(materia_id, asignacion_id)

    return UmbralResponse(**result)


# ═══════════════════════════════════════════════════════════════════════
# PUT /api/calificaciones/umbral
# ═══════════════════════════════════════════════════════════════════════


@router.put(
    "/umbral",
    response_model=UmbralMateriaResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("calificaciones:importar"))],
)
async def configurar_umbral(
    body: UmbralConfigRequest,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UmbralMateriaResponse:
    """Configura o actualiza el umbral de una asignacion+materia."""
    await _validar_scope_umbral(db, body.asignacion_id, current_user)

    svc = _build_umbral_service(db, current_user.tenant_id)
    try:
        result = await svc.configurar_umbral(
            materia_id=body.materia_id,
            asignacion_id=body.asignacion_id,
            umbral_pct=body.umbral_pct,
            valores_aprobatorios=body.valores_aprobatorios,
            usuario_id=current_user.user_id,
        )
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    settings = Settings()  # type: ignore[call-arg]
    audit_svc = _build_audit_service(db, current_user.tenant_id, settings)
    await audit_svc.register(
        accion=ACCION_CALIFICACIONES_IMPORTAR,
        actor_id=current_user.user_id,
        tenant_id=current_user.tenant_id,
        materia_id=body.materia_id,
        filas_afectadas=result.get("calificaciones_recalculadas", 0),
        detalle={
            "umbral_pct": result["umbral_pct"],
            "asignacion_id": str(body.asignacion_id),
        },
    )

    umbral_repo = UmbralMateriaRepository(db, current_user.tenant_id)
    umbral_obj = await umbral_repo.find_by_asignacion(body.asignacion_id)

    return UmbralMateriaResponse(
        id=umbral_obj.id if umbral_obj else UUID(int=0),
        materia_id=body.materia_id,
        asignacion_id=body.asignacion_id,
        umbral_pct=result["umbral_pct"],
        valores_aprobatorios=result.get("valores_aprobatorios"),
        calificaciones_recalculadas=result.get("calificaciones_recalculadas", 0),
    )
