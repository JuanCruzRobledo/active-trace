"""TOTPService — enrollment y verificación de 2FA TOTP.

Responsabilidades:
- ``enroll(user, totp_issuer)`` → genera secreto, arma URI ``otpauth://``,
  genera PNG del QR, persiste el secreto CIFRADO (via UserRepository).
  NO activa 2FA todavía — necesita ``confirm``.
- ``confirm(user, code, settings)`` → verifica que el usuario pudo escanear
  el QR obteniendo un código TOTP válido. Si es correcto, activa 2FA.
- ``verify(code, encrypted_secret)`` → verifica un código TOTP contra el
  secreto descifrado (para login gate).
"""

from __future__ import annotations

import base64
import io
from uuid import UUID

import pyotp
import qrcode

from app.core.audit import record
from app.core.config import Settings
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TwoFactorEnrollResponse


class TOTPService:
    """Service de 2FA TOTP (enrollment + verificación).

    Args:
        user_repo: Repositorio de usuarios.
        settings: Config del sistema (para TOTP_ISSUER y TTLs).
        tenant_id: UUID del tenant.
    """

    def __init__(
        self,
        user_repo: UserRepository,
        settings: Settings,
        tenant_id: UUID,
    ) -> None:
        self._user_repo = user_repo
        self._settings = settings
        self._tenant_id = tenant_id

    def generate_secret(self) -> str:
        """Genera un secreto TOTP base32 (160 bits por defecto de pyotp).

        Returns:
            Secreto base32 (string).
        """
        return pyotp.random_base32()

    def build_otpauth_uri(
        self, secret: str, email: str, issuer: str | None = None
    ) -> str:
        """Construye la URI ``otpauth://totp/...`` para apps authenticator.

        Args:
            secret: Secreto TOTP base32.
            email: Email del usuario (identificador en la app authenticator).
            issuer: Nombre del issuer (default: ``TOTP_ISSUER`` del settings).

        Returns:
            URI estándar (compatible con Google Authenticator, Authy, etc.).
        """
        if issuer is None:
            issuer = self._settings.TOTP_ISSUER
        return pyotp.TOTP(secret).provisioning_uri(
            name=email,
            issuer_name=issuer,
        )

    def generate_qr_png_base64(self, otpauth_uri: str) -> str:
        """Genera un QR code PNG en base64 desde una URI otpauth.

        Args:
            otpauth_uri: URI ``otpauth://...``.

        Returns:
            PNG codificado en base64.
        """
        img = qrcode.make(otpauth_uri)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()

    async def enroll(
        self,
        user_id: UUID,
        email: str,
    ) -> TwoFactorEnrollResponse:
        """Inicia enrollment de 2FA: genera secreto, URI y QR.

        El secreto se persiste CIFRADO en ``User.totp_secret``, pero
        2FA NO se activa hasta ``confirm()``.

        Args:
            user_id: UUID del usuario.
            email: Email del usuario (para la URI).

        Returns:
            TwoFactorEnrollResponse con secreto, URI y QR en base64.
        """
        secret = self.generate_secret()
        otpauth_uri = self.build_otpauth_uri(secret, email)
        qr_png = self.generate_qr_png_base64(otpauth_uri)

        # Persistir secreto cifrado (aún sin activar 2FA)
        await self._user_repo.enable_totp(
            user_id=user_id,
            encrypted_secret=secret,
        )

        record(
            "TOTP_ENROLL_STARTED",
            {
                "user_id": str(user_id),
                "tenant_id": str(self._tenant_id),
            },
        )

        return TwoFactorEnrollResponse(
            secret=secret,
            otpauth_uri=otpauth_uri,
            qr_png_base64=qr_png,
        )

    async def confirm(self, user_id: UUID, code: str) -> bool:
        """Confirma el enrollment verificando un código TOTP.

        Si el código es válido, 2FA se activa (``totp_enabled = True``).

        Args:
            user_id: UUID del usuario.
            code: Código TOTP de 6 dígitos.

        Returns:
            True si el código es válido y 2FA se activó.
        """
        # Obtener usuario con su secreto (descifrado automáticamente)
        user = await self._user_repo.get_by_id(user_id)
        if user is None or not user.totp_secret:
            return False

        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(code, valid_window=1):
            return False

        # Código válido — activar 2FA
        await self._user_repo.enable_totp(
            user_id=user_id,
            encrypted_secret=user.totp_secret,  # ya está persistido
        )

        record(
            "TOTP_ENROLL_CONFIRMED",
            {
                "user_id": str(user_id),
                "tenant_id": str(self._tenant_id),
            },
        )
        return True

    async def verify(
        self,
        user_id: UUID,
        code: str,
    ) -> bool:
        """Verifica un código TOTP para un usuario (login gate).

        Args:
            user_id: UUID del usuario.
            code: Código TOTP de 6 dígitos.

        Returns:
            True si el código es válido.
        """
        user = await self._user_repo.get_by_id(user_id)
        if user is None or not user.totp_secret:
            return False

        totp = pyotp.TOTP(user.totp_secret)
        return totp.verify(code, valid_window=1)
