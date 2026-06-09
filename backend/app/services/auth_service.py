"""AuthService — orquestador de autenticación.

Coordina flow completo:
- ``login(email, password, request)`` → valida credenciales, chequea 2FA,
  emite TokenPair o TwoFactorChallengeResponse.
- ``verify_2fa(challenge_token, code, request)`` → valida challenge TOTP,
  emite TokenPair.
- ``refresh(refresh_token_str, request)`` → rota refresh token.
- ``logout(refresh_token_str, current_user_id)`` → revoca refresh token.

TODAS las llamadas pasan por rate_limit primero (decorador en el router).
Este service es la capa que une repositorios + security + mail + audit.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import Request

from app.core.audit import record
from app.core.config import Settings
from app.core.mail import MailSender
from app.core.security import (
    SecurityError,
    TokenExpiredError,
    generate_opaque_token,
    hash_opaque_token,
    verify_password,
)
from app.repositories.audit_log_repository import AuditLogRepository
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
    TokenPair,
    TwoFactorChallengeResponse,
    UserMeResponse,
)
from app.services.audit_service import AuditService
from app.services.token_service import TokenService
from app.services.totp_service import TOTPService


class LoginFailedError(SecurityError):
    """Credenciales inválidas (email no existe o password incorrecto)."""


class TwoFactorRequiredError(SecurityError):
    """El usuario tiene 2FA activo — debe pasar el gate TOTP."""


class TwoFactorFailedError(SecurityError):
    """Código TOTP inválido o challenge expirado."""


class TwoFactorDisabledError(SecurityError):
    """2FA no está habilitado para este usuario."""


class RateLimitExceededError(SecurityError):
    """Demasiados intentos — rate limit excedido."""


class AuthService:
    """Orquestador de autenticación.

    Inyecta dependencies vía constructor. Ninguna dependencia global.
    """

    def __init__(
        self,
        user_repo: UserRepository,
        refresh_token_repo: RefreshTokenRepository,
        two_factor_repo: TwoFactorChallengeRepository,
        password_reset_repo: PasswordResetTokenRepository,
        token_service: TokenService,
        totp_service: TOTPService,
        password_service: PasswordService,
        user_rol_repo: UserRolRepository,
        mailer: MailSender,
        settings: Settings,
        tenant_id: UUID,
        audit_service: AuditService | None = None,
    ) -> None:
        self._user_repo = user_repo
        self._refresh_token_repo = refresh_token_repo
        self._two_factor_repo = two_factor_repo
        self._password_reset_repo = password_reset_repo
        self._token_service = token_service
        self._totp_service = totp_service
        self._password_service = password_service
        self._user_rol_repo = user_rol_repo
        self._mailer = mailer
        self._settings = settings
        self._tenant_id = tenant_id
        self._audit_service = audit_service

    # ── Helpers ─────────────────────────────────────────────────────────

    async def _register_audit(
        self,
        accion: str,
        actor_id: UUID,
        *,
        detalle: dict | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Registra un evento de auditoría si el servicio está configurado.

        Args:
            accion: Código de acción.
            actor_id: UUID del usuario que ejecutó la acción.
            detalle: Contexto adicional (opcional).
            ip: Dirección IP (opcional).
            user_agent: User-Agent (opcional).
        """
        if self._audit_service is not None:
            await self._audit_service.register(
                accion=accion,
                actor_id=actor_id,
                tenant_id=self._tenant_id,
                detalle=detalle,
                ip=ip,
                user_agent=user_agent,
            )

    async def _get_user_roles(self, user_id: UUID) -> list[str]:
        """Carga los códigos de rol de un usuario desde la DB.

        Args:
            user_id: UUID del usuario.

        Returns:
            Lista de códigos (ej: ``["PROFESOR"]``), vacío si no tiene roles.
        """
        return await self._user_rol_repo.get_role_codigos_for_user(user_id)

    # ── Login ───────────────────────────────────────────────────────────

    async def login(
        self,
        email: str,
        password: str,
        request: Request | None = None,
    ) -> TokenPair | TwoFactorChallengeResponse:
        """Autentica un usuario por email+password.

        Flow:
        1. Busca usuario por email (scoped al tenant).
        2. Verifica password con Argon2id.
        3. Si 2FA activo → genera challenge, retorna challenge response.
        4. Si no 2FA → emite TokenPair.

        Args:
            email: Email del usuario.
            password: Password en texto plano.
            request: Request de FastAPI (para IP + User-Agent).

        Returns:
            TokenPair o TwoFactorChallengeResponse.

        Raises:
            LoginFailedError: Si email no existe o password incorrecto.
        """
        ip = request.client.host if request and request.client else "unknown"
        ua = (
            request.headers.get("user-agent")
            if request
            else None
        )

        user = await self._user_repo.get_by_email(email)
        if user is None:
            record(
                "LOGIN_FAIL",
                {
                    "email": email,
                    "tenant_id": str(self._tenant_id),
                    "reason": "unknown_email",
                    "ip": ip,
                },
            )
            raise LoginFailedError("Invalid email or password")

        if not verify_password(password, user.password_hash):
            record(
                "LOGIN_FAIL",
                {
                    "email": email,
                    "tenant_id": str(self._tenant_id),
                    "reason": "bad_credentials",
                    "user_id": str(user.id),
                    "ip": ip,
                },
            )
            raise LoginFailedError("Invalid email or password")

        if not user.is_active:
            record(
                "LOGIN_FAIL",
                {
                    "email": email,
                    "tenant_id": str(self._tenant_id),
                    "reason": "inactive_user",
                    "user_id": str(user.id),
                    "ip": ip,
                },
            )
            raise LoginFailedError("Account is inactive")

        # 2FA gate
        if user.totp_enabled:
            challenge_plain = generate_opaque_token()
            challenge_hash = hash_opaque_token(challenge_plain)
            from datetime import datetime, timedelta, timezone

            expires_at = datetime.now(timezone.utc) + timedelta(
                minutes=self._settings.TWO_FA_CHALLENGE_EXPIRE_MINUTES
            )

            await self._two_factor_repo.create(
                user_id=user.id,
                token_hash=challenge_hash,
                expires_at=expires_at,
            )

            record(
                "LOGIN_2FA_REQUIRED",
                {
                    "user_id": str(user.id),
                    "tenant_id": str(self._tenant_id),
                    "ip": ip,
                },
            )

            return TwoFactorChallengeResponse(
                twofa_required=True,
                challenge_token=challenge_plain,
            )

        # Login exitoso sin 2FA
        roles = await self._get_user_roles(user.id)
        pair = await self._token_service.issue_token_pair(
            user=user,
            user_agent=ua,
            created_ip=ip,
            roles=roles,
        )

        record(
            "LOGIN_OK",
            {
                "user_id": str(user.id),
                "tenant_id": str(self._tenant_id),
                "ip": ip,
            },
        )
        await self._register_audit(
            "LOGIN_OK", actor_id=user.id, ip=ip, user_agent=ua
        )

        return pair

    # ── 2FA Verify ──────────────────────────────────────────────────────

    async def verify_2fa(
        self,
        challenge_token: str,
        code: str,
        request: Request | None = None,
    ) -> TokenPair:
        """Verifica un challenge 2FA con código TOTP y emite TokenPair.

        Args:
            challenge_token: Token opaco del challenge.
            code: Código TOTP de 6 dígitos.
            request: Request de FastAPI (para IP + User-Agent).

        Returns:
            TokenPair (access+refresh).

        Raises:
            SecurityError: Si challenge inválido, expirado o código incorrecto.
        """
        ip = request.client.host if request and request.client else "unknown"
        ua = (
            request.headers.get("user-agent")
            if request
            else None
        )

        challenge_hash = hash_opaque_token(challenge_token)
        challenge = await self._two_factor_repo.get_by_token_hash(
            challenge_hash
        )

        if challenge is None:
            raise SecurityError("Challenge not found")

        if challenge.is_used():
            raise SecurityError("Challenge already used")

        if challenge.is_expired():
            raise TokenExpiredError("Challenge has expired")

        # Verificar código TOTP
        valid = await self._totp_service.verify(
            user_id=challenge.user_id,
            code=code,
        )

        if not valid:
            record(
                "LOGIN_2FA_FAIL",
                {
                    "user_id": str(challenge.user_id),
                    "tenant_id": str(self._tenant_id),
                    "ip": ip,
                },
            )
            await self._register_audit(
                "LOGIN_2FA_FAIL", actor_id=challenge.user_id, ip=ip
            )
            raise TwoFactorFailedError("Invalid TOTP code")

        # Marcar challenge usado
        await self._two_factor_repo.mark_used(challenge.id)

        # Emitir token pair
        user = await self._user_repo.get_by_id(challenge.user_id)
        if user is None:
            raise SecurityError("User not found")

        roles = await self._get_user_roles(user.id)
        pair = await self._token_service.issue_token_pair(
            user=user,
            user_agent=ua,
            created_ip=ip,
            roles=roles,
        )

        record(
            "LOGIN_2FA_OK",
            {
                "user_id": str(challenge.user_id),
                "tenant_id": str(self._tenant_id),
                "ip": ip,
            },
        )
        await self._register_audit(
            "LOGIN_2FA_OK", actor_id=challenge.user_id, ip=ip, user_agent=ua
        )

        return pair

    # ── Refresh ─────────────────────────────────────────────────────────

    async def refresh(
        self,
        refresh_token_str: str,
        request: Request | None = None,
    ) -> TokenPair:
        """Rota un refresh token y emite un nuevo par.

        Args:
            refresh_token_str: Token opaco en claro.
            request: Request de FastAPI (para IP + User-Agent).

        Returns:
            TokenPair nuevo.

        Raises:
            SecurityError: Si el token es inválido, expiró o hay reuso.
        """
        ua = (
            request.headers.get("user-agent")
            if request
            else None
        )
        ip = request.client.host if request and request.client else "unknown"

        # Cargar roles del usuario antes de rotar (para incluirlos en el nuevo JWT)
        token_hash = hash_opaque_token(refresh_token_str)
        stored = await self._refresh_token_repo.get_by_token_hash(token_hash)
        roles = (
            await self._get_user_roles(stored.user_id)
            if stored is not None
            else []
        )

        # Preservar impersonated_by del token almacenado durante la rotación
        imp_by: str | None = None
        if stored is not None and stored.impersonated_by is not None:
            imp_by = str(stored.impersonated_by)

        try:
            pair = await self._token_service.rotate_refresh(
                refresh_token_str=refresh_token_str,
                user_agent=ua,
                ip=ip,
                roles=roles,
                impersonated_by=imp_by,
            )
        except SecurityError as exc:
            # Si es reuso, ya se auditó en token_service. Igual registramos.
            record(
                "REFRESH_REUSE_DETECTED"
                if "reuse" in str(exc).lower()
                else "TOKEN_SIGNATURE_INVALID",
                {
                    "ip": ip,
                    "error": str(exc),
                },
            )
            raise

        record(
            "REFRESH_OK",
            {
                "ip": ip,
            },
        )
        if stored is not None:
            await self._register_audit(
                "REFRESH_OK", actor_id=stored.user_id, ip=ip, user_agent=ua
            )

        return pair

    # ── Logout ──────────────────────────────────────────────────────────

    async def logout(
        self,
        refresh_token_str: str,
        current_user_id: UUID,
    ) -> None:
        """Revoca un refresh token del usuario actual.

        Args:
            refresh_token_str: Token opaco a revocar.
            current_user_id: UUID del usuario autenticado (del JWT).
        """
        token_hash = hash_opaque_token(refresh_token_str)
        stored = await self._refresh_token_repo.get_by_token_hash(token_hash)

        if stored is not None and stored.user_id == current_user_id:
            if not stored.is_revoked():
                await self._refresh_token_repo.revoke(stored.id)

        record(
            "LOGOUT",
            {
                "user_id": str(current_user_id),
                "tenant_id": str(self._tenant_id),
            },
        )
        await self._register_audit("LOGOUT", actor_id=current_user_id)

    # ── Forgot / Reset (delegado) ───────────────────────────────────────

    async def forgot(self, email: str) -> None:
        """Solicita reset de contraseña (delega a PasswordService).

        Args:
            email: Email del usuario.
        """
        await self._password_service.request_reset(email)

    async def reset(self, token: str, new_password: str) -> None:
        """Confirma reset de contraseña (delega a PasswordService).

        Args:
            token: Token opaco del reset.
            new_password: Nuevo password.
        """
        await self._password_service.confirm_reset(token, new_password)

    # ── 2FA Enroll (delegado) ───────────────────────────────────────────

    async def enroll_2fa(
        self,
        user_id: UUID,
        email: str,
    ):
        """Inicia enrollment 2FA (delega a TOTPService).

        Args:
            user_id: UUID del usuario.
            email: Email del usuario.

        Returns:
            TwoFactorEnrollResponse.
        """
        return await self._totp_service.enroll(user_id, email)

    async def confirm_2fa(self, user_id: UUID, code: str) -> bool:
        """Confirma enrollment 2FA.

        Args:
            user_id: UUID del usuario.
            code: Código TOTP.

        Returns:
            True si se activó 2FA.
        """
        return await self._totp_service.confirm(user_id, code)

    # ── Me ──────────────────────────────────────────────────────────────

    async def get_me(self, user_id: UUID) -> UserMeResponse | None:
        """Retorna el perfil público del usuario autenticado.

        Args:
            user_id: UUID del usuario (del JWT).

        Returns:
            UserMeResponse o None si el usuario no existe.
        """
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            return None

        return UserMeResponse(
            id=str(user.id),
            tenant_id=str(user.tenant_id),
            email=user.email,
            is_active=user.is_active,
            totp_enabled=user.totp_enabled,
            roles=[],
        )
