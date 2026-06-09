"""TokenService — emisión y rotación de pares access+refresh.

Responsabilidades:
- ``issue_token_pair(user, settings, secret_key)`` → genera access JWT + refresh
  opaco, persiste el refresh (hasheado), retorna ``TokenPair``.
- ``rotate_refresh(refresh_token_str, token_repo, settings, secret_key)`` →
  valida, rota y retorna un nuevo par. Detecta reuso y revoca toda la familia.

El service inyecta dependencies vía constructor (sin dependencias de módulo
globales), lo que lo hace testeable con DI manual.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.core.config import Settings
from app.core.security import (
    create_access_token,
    generate_opaque_token,
    hash_opaque_token,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.schemas.auth import TokenPair


class TokenService:
    """Emisión, rotación y revocación de pares access+refresh.

    Args:
        token_repo: Repositorio de refresh tokens.
        settings: Config del sistema (para TTLs).
        secret_key: SECRET_KEY para firmar JWT (se pasa explícito).
        tenant_id: UUID del tenant (scope obligatorio para el repositorio).
    """

    def __init__(
        self,
        token_repo: RefreshTokenRepository,
        settings: Settings,
        secret_key: str,
        tenant_id: UUID,
    ) -> None:
        self._token_repo = token_repo
        self._settings = settings
        self._secret_key = secret_key
        self._tenant_id = tenant_id

    async def issue_token_pair(
        self,
        user: User,
        user_agent: str | None = None,
        created_ip: str | None = None,
        roles: list[str] | None = None,
        impersonated_by: str | None = None,
    ) -> TokenPair:
        """Emite un par access+refresh para un usuario autenticado.

        1. Genera access JWT con claims sub/tenant_id/roles.
        2. Genera refresh opaco (256 bits), lo hashea y persiste.
        3. Calcula ``expires_in`` en segundos.

        Args:
            user: Usuario autenticado (debe tener PK asignada).
            user_agent: User-Agent del cliente (opcional).
            created_ip: IP del cliente (opcional).
            roles: Lista de códigos de rol para incluir en el JWT.
            impersonated_by: UUID del actor real si es impersonación
                (opcional). Se incluye como claim ``impersonated_by`` en el JWT.

        Returns:
            TokenPair listo para devolver al cliente.
        """
        # Extra claims para impersonación
        extra_claims: dict[str, object] = {}
        if impersonated_by is not None:
            extra_claims["impersonated_by"] = impersonated_by

        # Access token
        access_token = create_access_token(
            user_id=user.id,
            tenant_id=self._tenant_id,
            secret_key=self._secret_key,
            roles=roles or [],
            expires_minutes=self._settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            extra_claims=extra_claims if extra_claims else None,
        )

        # Refresh token opaco
        refresh_plain = generate_opaque_token()
        refresh_hash = hash_opaque_token(refresh_plain)
        from datetime import timedelta

        expires_at = datetime.now(timezone.utc) + timedelta(
            days=self._settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

        await self._token_repo.create(
            user_id=user.id,
            token_hash=refresh_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            created_ip=created_ip,
            impersonated_by=UUID(impersonated_by) if impersonated_by else None,
        )

        expires_in_seconds = self._settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_plain,
            expires_in=expires_in_seconds,
        )

    async def rotate_refresh(
        self,
        refresh_token_str: str,
        user_agent: str | None = None,
        ip: str | None = None,
        roles: list[str] | None = None,
        impersonated_by: str | None = None,
    ) -> TokenPair:
        """Rota un refresh token: valida, revoca el anterior, emite nuevo par.

        Si detecta que el token presentado ya fue revocado, revoca TODA la
        familia del usuario (reuso-detection) y levanta SecurityError.

        Args:
            refresh_token_str: Token opaco en claro (del body).
            user_agent: User-Agent del cliente (opcional).
            ip: IP del cliente (opcional).
            roles: Lista de códigos de rol para incluir en el nuevo JWT.
            impersonated_by: UUID del actor real si esta sesión está bajo
                impersonación (opcional). Se preserva durante la rotación.

        Returns:
            TokenPair nuevo.

        Raises:
            SecurityError: Si el token es inválido, expiró o hay reuso.
        """
        from app.core.security import SecurityError, TokenExpiredError

        token_hash = hash_opaque_token(refresh_token_str)
        stored = await self._token_repo.get_by_token_hash(token_hash)

        if stored is None:
            raise SecurityError("Refresh token not found")

        if stored.is_revoked():
            # Reuso detectado — revocar toda la familia
            await self._token_repo.revoke_family(
                user_id=stored.user_id, token_id=stored.id
            )
            raise SecurityError(
                "Refresh token reuse detected — all tokens revoked"
            )

        if stored.is_expired():
            raise TokenExpiredError("Refresh token has expired")

        # Marcar el viejo como revocado
        await self._token_repo.revoke(stored.id)

        # Emitir nuevo par (preservando impersonated_by si existe)
        imp_by: str | None = impersonated_by
        if imp_by is None and stored.impersonated_by is not None:
            imp_by = str(stored.impersonated_by)

        return await self.issue_token_pair(
            user=User(id=stored.user_id, tenant_id=self._tenant_id),
            user_agent=user_agent or stored.user_agent,
            created_ip=ip or stored.created_ip,
            roles=roles or [],
            impersonated_by=imp_by,
        )
