"""PasswordService — solicitud y confirmación de reseteo de contraseña.

Flujo:
1. ``request_reset(email)`` → busca usuario, genera token opaco, lo persiste
   (hasheado), invalida tokens anteriores del mismo usuario, envía link vía mailer.
   Si el email no existe, no-op (no revelar existencia del email).
2. ``confirm_reset(token, new_password)`` → busca token por hash, valida,
   actualiza password_hash, marca token usado, invalida tokens de reset
   pendientes, revoca todos los refresh tokens del usuario.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.core.audit import record
from app.core.config import Settings
from app.core.mail import MailSender
from app.core.security import (
    SecurityError,
    TokenExpiredError,
    generate_opaque_token,
    hash_opaque_token,
    hash_password,
)
from app.repositories.password_reset_token_repository import (
    PasswordResetTokenRepository,
)
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository


class PasswordService:
    """Service de reseteo de contraseña.

    Args:
        user_repo: Repositorio de usuarios.
        reset_token_repo: Repositorio de tokens de reset.
        refresh_token_repo: Repositorio de refresh tokens (para revocar
            sesiones al resetear).
        mailer: Implementación de MailSender (ConsoleMailSender en C-03).
        settings: Config del sistema.
        tenant_id: UUID del tenant.
    """

    def __init__(
        self,
        user_repo: UserRepository,
        reset_token_repo: PasswordResetTokenRepository,
        refresh_token_repo: RefreshTokenRepository,
        mailer: MailSender,
        settings: Settings,
        tenant_id: UUID,
    ) -> None:
        self._user_repo = user_repo
        self._reset_token_repo = reset_token_repo
        self._refresh_token_repo = refresh_token_repo
        self._mailer = mailer
        self._settings = settings
        self._tenant_id = tenant_id

    async def request_reset(self, email: str) -> None:
        """Solicita un reset de contraseña.

        Siempre retorna exitosamente (no revela si el email existe).
        Si el usuario existe, genera token, invalida tokens anteriores y
        envía el link.

        Args:
            email: Email del usuario (puede no existir — no-op silencioso).
        """
        user = await self._user_repo.get_by_email(email)
        if user is None:
            return

        # Invalidar tokens de reset anteriores
        await self._reset_token_repo.invalidate_all_pending_for_user(user.id)

        # Generar nuevo token
        token_plain = generate_opaque_token()
        token_hash = hash_opaque_token(token_plain)
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=self._settings.PASSWORD_RESET_EXPIRE_MINUTES
        )

        await self._reset_token_repo.create(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )

        # Enviar link
        # El frontend resuelve la URL base desde su config; el backend
        # solo provee el token. En desarrollo, el link va a los logs.
        link = f"https://app.activia-trace.com/reset?token={token_plain}"
        self._mailer.send_reset_link(to_email=email, link=link)

        record(
            "PASSWORD_RESET_REQUEST",
            {
                "user_id": str(user.id),
                "tenant_id": str(self._tenant_id),
                "email": email,
            },
        )

    async def confirm_reset(self, token: str, new_password: str) -> None:
        """Confirma un reset de contraseña con el token recibido por email.

        Valida el token, actualiza el password, marca todo como usado y
        revoca sesiones activas.

        Args:
            token: Token opaco en claro (del query param).
            new_password: Nuevo password en texto plano.

        Raises:
            SecurityError: Si el token no existe, está usado o expiró.
        """
        token_hash = hash_opaque_token(token)
        stored = await self._reset_token_repo.get_by_token_hash(token_hash)

        if stored is None:
            raise SecurityError("Reset token not found")

        if stored.is_used():
            raise SecurityError("Reset token already used")

        if stored.is_expired():
            raise TokenExpiredError("Reset token has expired")

        # Actualizar password
        new_hash = hash_password(new_password)
        await self._user_repo.update_password(
            user_id=stored.user_id,
            new_hash=new_hash,
        )

        # Marcar token como usado
        await self._reset_token_repo.mark_used(stored.id)

        # Invalidar otros tokens de reset pendientes del mismo usuario
        await self._reset_token_repo.invalidate_all_pending_for_user(
            stored.user_id
        )

        # Revocar todas las sesiones activas del usuario
        await self._refresh_token_repo.revoke_all_for_user(stored.user_id)

        record(
            "PASSWORD_RESET_OK",
            {
                "user_id": str(stored.user_id),
                "tenant_id": str(self._tenant_id),
            },
        )
