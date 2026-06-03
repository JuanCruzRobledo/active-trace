"""Router de autenticación (C-03 auth-jwt-2fa).

Endpoints:
- ``POST /api/auth/login`` — autenticación email+password (rate-limited).
- ``POST /api/auth/2fa/verify`` — verificación TOTP post-login (rate-limited).
- ``POST /api/auth/refresh`` — rotación de refresh token (rate-limited).
- ``POST /api/auth/logout`` — revocación de refresh token (autenticado).
- ``POST /api/auth/forgot`` — solicitud de reset de contraseña (rate-limited).
- ``POST /api/auth/reset`` — confirmación de reset (rate-limited).
- ``POST /api/auth/2fa/enroll`` — inicio de enrollment 2FA (autenticado).
- ``POST /api/auth/2fa/confirm`` — confirmación de enrollment 2FA (autenticado).
- ``GET /api/auth/me`` — perfil del usuario autenticado.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.dependencies import UserContext, get_current_user, get_db
from app.core.mail import ConsoleMailSender
from app.core.rate_limit import (
    rate_limit_2fa_verify,
    rate_limit_forgot,
    rate_limit_login,
    rate_limit_refresh,
    rate_limit_reset,
)
from app.core.security import SecurityError
from app.repositories.password_reset_token_repository import (
    PasswordResetTokenRepository,
)
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.two_factor_challenge_repository import (
    TwoFactorChallengeRepository,
)
from app.repositories.user_repository import UserRepository
from app.repositories.user_rol_repository import UserRolRepository
from app.schemas.auth import (
    ForgotRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    ResetRequest,
    TOTPConfirmRequest,
    TOTPVerifyRequest,
    TokenPair,
    TwoFactorEnrollResponse,
    UserMeResponse,
)
from app.services.auth_service import AuthService, LoginFailedError
from app.services.password_service import PasswordService
from app.services.token_service import TokenService
from app.services.totp_service import TOTPService

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Tenant fijo para MVP C-03 (C-02 introduce multi-tenancy real).
_DEV_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")


# ── Factory helper ─────────────────────────────────────────────────────


def _build_auth_service(
    db: AsyncSession,
    tenant_id: UUID = _DEV_TENANT_ID,
) -> AuthService:
    """Construye un AuthService con todas sus dependencies.

    Args:
        db: Sesión async.
        tenant_id: UUID del tenant (default: dev tenant).

    Returns:
        AuthService listo para usar.
    """
    settings = Settings()  # type: ignore[call-arg]

    user_repo = UserRepository(session=db, tenant_id=tenant_id)
    user_rol_repo = UserRolRepository(session=db, tenant_id=tenant_id)
    refresh_repo = RefreshTokenRepository(session=db, tenant_id=tenant_id)
    twofa_repo = TwoFactorChallengeRepository(session=db, tenant_id=tenant_id)
    reset_repo = PasswordResetTokenRepository(session=db, tenant_id=tenant_id)
    mailer = ConsoleMailSender()

    token_svc = TokenService(
        token_repo=refresh_repo,
        settings=settings,
        secret_key=settings.SECRET_KEY,
        tenant_id=tenant_id,
    )
    totp_svc = TOTPService(
        user_repo=user_repo,
        settings=settings,
        tenant_id=tenant_id,
    )
    pwd_svc = PasswordService(
        user_repo=user_repo,
        reset_token_repo=reset_repo,
        refresh_token_repo=refresh_repo,
        mailer=mailer,
        settings=settings,
        tenant_id=tenant_id,
    )

    return AuthService(
        user_repo=user_repo,
        refresh_token_repo=refresh_repo,
        two_factor_repo=twofa_repo,
        password_reset_repo=reset_repo,
        token_service=token_svc,
        totp_service=totp_svc,
        password_service=pwd_svc,
        user_rol_repo=user_rol_repo,
        mailer=mailer,
        settings=settings,
        tenant_id=tenant_id,
    )


# ═══════════════════════════════════════════════════════════════════════
# POST /login
# ═══════════════════════════════════════════════════════════════════════


@router.post("/login")
@rate_limit_login
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Autentica un usuario por email+password.

    Retorna ``TokenPair`` o ``TwoFactorChallengeResponse`` si 2FA está
    activo para el usuario.
    """
    auth_svc = _build_auth_service(db)
    try:
        return await auth_svc.login(
            email=body.email,
            password=body.password,
            request=request,
        )
    except LoginFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )


# ═══════════════════════════════════════════════════════════════════════
# POST /2fa/verify
# ═══════════════════════════════════════════════════════════════════════


@router.post("/2fa/verify")
@rate_limit_2fa_verify
async def verify_2fa(
    body: TOTPVerifyRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenPair:
    """Verifica un challenge 2FA con código TOTP."""
    auth_svc = _build_auth_service(db)
    try:
        return await auth_svc.verify_2fa(
            challenge_token=body.challenge_token,
            code=body.code,
            request=request,
        )
    except (SecurityError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )


# ═══════════════════════════════════════════════════════════════════════
# POST /refresh
# ═══════════════════════════════════════════════════════════════════════


@router.post("/refresh")
@rate_limit_refresh
async def refresh(
    body: RefreshRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenPair:
    """Rota un refresh token y emite un nuevo par."""
    auth_svc = _build_auth_service(db)
    try:
        return await auth_svc.refresh(
            refresh_token_str=body.refresh_token,
            request=request,
        )
    except SecurityError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )


# ═══════════════════════════════════════════════════════════════════════
# POST /logout
# ═══════════════════════════════════════════════════════════════════════


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: LogoutRequest,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Revoca un refresh token del usuario autenticado."""
    auth_svc = _build_auth_service(db, tenant_id=current_user.tenant_id)
    await auth_svc.logout(
        refresh_token_str=body.refresh_token,
        current_user_id=current_user.user_id,
    )


# ═══════════════════════════════════════════════════════════════════════
# POST /forgot
# ═══════════════════════════════════════════════════════════════════════


@router.post("/forgot", status_code=status.HTTP_204_NO_CONTENT)
@rate_limit_forgot
async def forgot(
    body: ForgotRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Solicita un reset de contraseña (no-op si el email no existe)."""
    auth_svc = _build_auth_service(db)
    await auth_svc.forgot(email=body.email)


# ═══════════════════════════════════════════════════════════════════════
# POST /reset
# ═══════════════════════════════════════════════════════════════════════


@router.post("/reset", status_code=status.HTTP_204_NO_CONTENT)
@rate_limit_reset
async def reset(
    body: ResetRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Confirma un reset de contraseña con el token recibido por email."""
    auth_svc = _build_auth_service(db)
    try:
        await auth_svc.reset(
            token=body.token,
            new_password=body.new_password,
        )
    except SecurityError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


# ═══════════════════════════════════════════════════════════════════════
# POST /2fa/enroll
# ═══════════════════════════════════════════════════════════════════════


@router.post("/2fa/enroll")
async def enroll_2fa(
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TwoFactorEnrollResponse:
    """Inicia enrollment de 2FA TOTP para el usuario autenticado."""
    tid = current_user.tenant_id
    user_repo = UserRepository(session=db, tenant_id=tid)
    user = await user_repo.get_by_id(current_user.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    settings = Settings()  # type: ignore[call-arg]
    totp_svc = TOTPService(
        user_repo=user_repo,
        settings=settings,
        tenant_id=tid,
    )
    return await totp_svc.enroll(
        user_id=current_user.user_id,
        email=user.email,
    )


# ═══════════════════════════════════════════════════════════════════════
# POST /2fa/confirm
# ═══════════════════════════════════════════════════════════════════════


@router.post("/2fa/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def confirm_2fa(
    body: TOTPConfirmRequest,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Confirma enrollment de 2FA con un código TOTP válido."""
    tid = current_user.tenant_id
    settings = Settings()  # type: ignore[call-arg]
    user_repo = UserRepository(session=db, tenant_id=tid)
    totp_svc = TOTPService(
        user_repo=user_repo,
        settings=settings,
        tenant_id=tid,
    )
    ok = await totp_svc.confirm(
        user_id=current_user.user_id,
        code=body.code,
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid TOTP code",
        )


# ═══════════════════════════════════════════════════════════════════════
# GET /me
# ═══════════════════════════════════════════════════════════════════════


@router.get("/me")
async def get_me(
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserMeResponse:
    """Retorna el perfil del usuario autenticado.

    La identidad SIEMPRE viene del JWT. Cualquier intento de override
    vía query param (``?user_id=...``) es ignorado.
    """
    tid = current_user.tenant_id
    user_repo = UserRepository(session=db, tenant_id=tid)
    user = await user_repo.get_by_id(current_user.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    from app.services.permission_service import PermissionService  # noqa: PLC0415

    perm_svc = PermissionService(db, tid)
    permisos = await perm_svc.get_effective_permissions(
        current_user.roles
    )

    return UserMeResponse(
        id=str(user.id),
        tenant_id=str(user.tenant_id),
        email=user.email,
        is_active=user.is_active,
        totp_enabled=user.totp_enabled,
        roles=current_user.roles,
        permisos=sorted(permisos),
    )
