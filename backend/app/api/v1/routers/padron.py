"""Router de importacion y gestion de padron de alumnos (C-09).

Endpoints protegidos con require_permission("padron:importar"):
- ``POST /api/padron/importar`` — preview (multipart) + confirm (preview_token).
- ``GET /api/padron/{materia_id}/{cohorte_id}`` — padron activo con entradas.
- ``DELETE /api/padron/{materia_id}/vaciar`` — vaciar datos de materia (F1.5, RN-04).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    UserContext,
    get_current_user,
    get_db,
    require_permission,
)
from app.core.exceptions import BusinessError
from app.schemas.padron import (
    EntradaPadronResponse,
    PadronConfirmRequest,
    PadronImportResponse,
    PadronPreviewResponse,
    PadronVaciarResponse,
    VersionPadronResponse,
)
from app.services.audit_service import ACCION_PADRON_CARGAR, ACCION_PADRON_VACIAR, AuditService
from app.services.padron_service import PadronService
from app.repositories.audit_log_repository import AuditLogRepository
from app.core.config import Settings

router = APIRouter(
    prefix="/api/padron",
    tags=["padron"],
)


# ── Helpers ──────────────────────────────────────────────────────────


def _build_service(db: AsyncSession, tenant_id: UUID) -> PadronService:
    return PadronService(session=db, tenant_id=tenant_id)


def _build_audit_service(db: AsyncSession, tenant_id: UUID, settings: Settings) -> AuditService:
    repo = AuditLogRepository(db, tenant_id=tenant_id)
    return AuditService(audit_log_repo=repo, settings=settings)


def _entrada_to_response(e: object) -> EntradaPadronResponse:
    return EntradaPadronResponse(
        id=str(e.id),
        version_id=str(e.version_id),
        usuario_id=str(e.usuario_id) if e.usuario_id else None,
        nombre=e.nombre,
        apellidos=e.apellidos,
        email=e.email,
        comision=e.comision,
        regional=e.regional,
    )


def _version_to_response(v: object) -> VersionPadronResponse:
    entradas = getattr(v, "entradas", [])
    return VersionPadronResponse(
        id=str(v.id),
        materia_id=str(v.materia_id),
        cohorte_id=str(v.cohorte_id),
        cargado_por=str(v.cargado_por) if v.cargado_por else None,
        cargado_at=v.cargado_at,
        activa=v.activa,
        entradas=[_entrada_to_response(e) for e in entradas],
        created_at=v.created_at,
        updated_at=v.updated_at,
    )


# ═══════════════════════════════════════════════════════════════════════
# Importar padron
# ═══════════════════════════════════════════════════════════════════════


@router.post(
    "/importar",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("padron:importar"))],
)
async def importar_padron(
    materia_id: UUID = Form(...),
    cohorte_id: UUID = Form(...),
    file: UploadFile = File(...),
    preview_token: str | None = Form(default=None),
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PadronImportResponse | PadronPreviewResponse:
    """Importa un padron de alumnos.

    Dos modos:
    - Preview (default): procesa el archivo y retorna preview + preview_token.
    - Confirm: envia el preview_token para persistir los datos.
    """
    svc = _build_service(db, current_user.tenant_id)
    data = await file.read()

    if not data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El archivo esta vacio",
        )

    # Modo preview: sin preview_token
    if not preview_token:
        try:
            preview = await svc.preview_importacion(data, file.filename or "import.xlsx")
        except BusinessError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            )
        return PadronPreviewResponse(**preview)

    # Modo confirm: con preview_token
    try:
        version = await svc.confirmar_importacion(
            preview_token=preview_token,
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            cargado_por=current_user.user_id,
        )
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    cantidad_entradas = 0
    if hasattr(version, "entradas"):
        cantidad_entradas = len(version.entradas)
    else:
        from app.models.entrada_padron import EntradaPadron
        from app.repositories.entrada_padron_repository import EntradaPadronRepository
        from app.repositories.version_padron_repository import VersionPadronRepository
        entrada_repo = EntradaPadronRepository(db, EntradaPadron, current_user.tenant_id)
        cantidad_entradas = await entrada_repo.listar_por_version(version.id)
        cantidad_entradas = len(cantidad_entradas)

    # Registrar auditoria
    settings = Settings()  # type: ignore[call-arg]
    audit_svc = _build_audit_service(db, current_user.tenant_id, settings)
    await audit_svc.register(
        accion=ACCION_PADRON_CARGAR,
        actor_id=current_user.user_id,
        tenant_id=current_user.tenant_id,
        materia_id=materia_id,
        filas_afectadas=cantidad_entradas,
        detalle={
            "version_id": str(version.id),
            "cohorte_id": str(cohorte_id),
            "filename": file.filename,
        },
    )

    return PadronImportResponse(
        version_id=str(version.id),
        materia_id=str(materia_id),
        cohorte_id=str(cohorte_id),
        cantidad_entradas=cantidad_entradas,
        cargado_at=version.cargado_at,
    )


# ═══════════════════════════════════════════════════════════════════════
# Consultar padron activo
# ═══════════════════════════════════════════════════════════════════════


@router.get(
    "/{materia_id}/{cohorte_id}",
    dependencies=[Depends(require_permission("padron:importar"))],
)
async def obtener_padron_activo(
    materia_id: UUID,
    cohorte_id: UUID,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VersionPadronResponse:
    """Obtiene el padron activo de una materia x cohorte."""
    svc = _build_service(db, current_user.tenant_id)
    version = await svc.obtener_activo(materia_id, cohorte_id)
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay padron activo para esta materia y cohorte",
        )
    return _version_to_response(version)


# ═══════════════════════════════════════════════════════════════════════
# Vaciar datos de materia (F1.5, RN-04)
# ═══════════════════════════════════════════════════════════════════════


@router.delete(
    "/{materia_id}/vaciar",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("padron:importar"))],
)
async def vaciar_padron_materia(
    materia_id: UUID,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PadronVaciarResponse:
    """Vacia los datos de padron e ingesta de una materia.

    Solo el PROFESOR de esa materia o COORDINADOR/ADMIN pueden ejecutarlo.
    No afecta otras materias (RN-04).
    """
    svc = _build_service(db, current_user.tenant_id)
    try:
        resultado = await svc.vaciar_materia(materia_id)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    # Registrar auditoria
    settings = Settings()  # type: ignore[call-arg]
    audit_svc = _build_audit_service(db, current_user.tenant_id, settings)
    await audit_svc.register(
        accion=ACCION_PADRON_VACIAR,
        actor_id=current_user.user_id,
        tenant_id=current_user.tenant_id,
        materia_id=materia_id,
        filas_afectadas=resultado["versiones_desactivadas"],
        detalle=resultado,
    )

    return PadronVaciarResponse(
        materia_id=str(materia_id),
        versiones_desactivadas=resultado["versiones_desactivadas"],
        entradas_eliminadas=resultado["entradas_eliminadas"],
    )
