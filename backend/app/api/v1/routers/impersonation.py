"""Router de impersonación (C-05 audit-log).

Endpoints:
- ``POST /api/auth/impersonate`` — inicia una sesión de impersonación.
- ``POST /api/auth/impersonate/stop`` — detiene la impersonación activa.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record
from app.core.config import Settings
from app.core.dependencies import UserContext, get_current_user, get_db
from app.core.permissions import PERM_IMPERSONACION_USAR
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import ImpersonateRequest, TokenPair
from app.services.audit_service import AuditService
from app.services.token_service import TokenService

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _build_impersonation_service(
    db: AsyncSession,
    tenant_id: UUID,
) -> tuple[UserRepository, TokenService, AuditLogRepository]:
    """Construye las dependencias necesarias para impersonación.

    Args:
        db: Sesión async.
        tenant_id: UUID del tenant.

    Returns:
        Tupla (user_repo, token_svc, audit_repo).
    """
    settings = Settings()  # type: ignore[call-arg]
    user_repo = UserRepository(session=db, tenant_id=tenant_id)
    refresh_repo = RefreshTokenRepository(session=db, tenant_id=tenant_id)
    audit_repo = AuditLogRepository(session=db, tenant_id=tenant_id)

    token_svc = TokenService(
        token_repo=refresh_repo,
        settings=settings,
        secret_key=settings.SECRET_KEY,
        tenant_id=tenant_id,
    )

    return user_repo, token_svc, audit_repo


# ═══════════════════════════════════════════════════════════════════════
# POST /impersonate
# ═══════════════════════════════════════════════════════════════════════


@router.post("/impersonate")
async def impersonate(
    body: ImpersonateRequest,
    request: Request,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TokenPair:
    """Inicia una sesión de impersonación.

    Requiere permiso ``impersonacion:usar``. Verifica que el target exista
    y esté activo dentro del mismo tenant. Registra ``IMPERSONACION_INICIAR``
    y emite un nuevo token pair con claim ``impersonated_by``.
    """
    from app.core.dependencies import require_permission  # noqa: PLC0415

    require_perm = require_permission(PERM_IMPERSONACION_USAR)
    await require_perm(current_user=current_user, db=db)

    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent")

    target_id = UUID(body.target_user_id)
    user_repo, token_svc, audit_repo = _build_impersonation_service(
        db, current_user.tenant_id
    )

    # Verificar que el target existe y está activo en el mismo tenant
    target_user = await user_repo.get_by_id(target_id)
    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target user not found",
        )
    if not target_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target user is inactive",
        )

    # Registrar inicio de impersonación
    actor_id = current_user.impersonated_by_id or current_user.user_id
    settings = Settings()  # type: ignore[call-arg]
    audit_svc = AuditService(
        audit_log_repo=audit_repo,
        settings=settings,
    )
    await audit_svc.register(
        accion="IMPERSONACION_INICIAR",
        actor_id=actor_id,
        tenant_id=current_user.tenant_id,
        impersonado_id=target_id,
        detalle={"impersonated_by": str(actor_id), "target": str(target_id)},
        ip=ip,
        user_agent=ua,
    )
    record(
        "IMPERSONACION_INICIAR",
        {
            "actor_id": str(actor_id),
            "target_id": str(target_id),
            "tenant_id": str(current_user.tenant_id),
            "ip": ip,
        },
    )

    # Emitir token pair con claim impersonated_by
    from app.repositories.user_rol_repository import UserRolRepository  # noqa: PLC0415

    user_rol_repo = UserRolRepository(session=db, tenant_id=current_user.tenant_id)
    target_roles = await user_rol_repo.get_role_codigos_for_user(target_id)

    pair = await token_svc.issue_token_pair(
        user=target_user,
        user_agent=ua,
        created_ip=ip,
        roles=target_roles,
        impersonated_by=str(actor_id),
    )

    return pair


# ═══════════════════════════════════════════════════════════════════════
# POST /impersonate/stop
# ═══════════════════════════════════════════════════════════════════════


@router.post("/impersonate/stop")
async def impersonate_stop(
    request: Request,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TokenPair:
    """Detiene la impersonación activa.

    Verifica que el token actual tenga ``impersonated_by`` (sesión bajo
    impersonación). Registra ``IMPERSONACION_FINALIZAR`` y emite un nuevo
    token pair para el actor real.
    """
    if current_user.impersonated_by_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not currently impersonating",
        )

    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent")

    actor_id = current_user.impersonated_by_id
    tenant_id = current_user.tenant_id

    _, token_svc, audit_repo = _build_impersonation_service(
        db, tenant_id
    )

    # Registrar finalización de impersonación
    settings = Settings()  # type: ignore[call-arg]
    audit_svc = AuditService(
        audit_log_repo=audit_repo,
        settings=settings,
    )
    await audit_svc.register(
        accion="IMPERSONACION_FINALIZAR",
        actor_id=actor_id,
        tenant_id=tenant_id,
        impersonado_id=current_user.user_id,
        detalle={
            "actor_id": str(actor_id),
            "impersonado_id": str(current_user.user_id),
        },
        ip=ip,
        user_agent=ua,
    )
    record(
        "IMPERSONACION_FINALIZAR",
        {
            "actor_id": str(actor_id),
            "impersonado_id": str(current_user.user_id),
            "tenant_id": str(tenant_id),
            "ip": ip,
        },
    )

    # Emitir token pair para el actor real
    user_repo = UserRepository(session=db, tenant_id=tenant_id)
    actor_user = await user_repo.get_by_id(actor_id)
    if actor_user is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Actor user not found",
        )

    from app.repositories.user_rol_repository import UserRolRepository  # noqa: PLC0415

    user_rol_repo = UserRolRepository(session=db, tenant_id=tenant_id)
    actor_roles = await user_rol_repo.get_role_codigos_for_user(actor_id)

    pair = await token_svc.issue_token_pair(
        user=actor_user,
        user_agent=ua,
        created_ip=ip,
        roles=actor_roles,
    )

    return pair
