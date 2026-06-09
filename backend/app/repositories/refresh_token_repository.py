"""Repositorio de RefreshToken — rotación, revocación y detección de reuso.

Operaciones:
- ``create(...)`` → inserta un refresh token.
- ``get_by_token_hash(hash)`` → lookup por hash (sin scope de tenant — el
  hash es global UNIQUE; el tenant se valida en service layer).
- ``revoke(token_id)`` → marca revoked_at.
- ``revoke_all_for_user(user_id)`` → revoca TODOS los tokens activos de un usuario.
- ``revoke_family(user_id, token_id)`` → revoca el token + todos los que
  referencian a su familia (reuso detection).
- ``count_active_for_user(user_id)`` → cuántos tokens activos tiene hoy.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken
from app.repositories.base import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    """Repositorio de refresh tokens con soporte de rotación y reuso-detection.

    Args:
        session: Sesión async de SQLAlchemy.
        tenant_id: UUID del tenant.
    """

    def __init__(self, session: AsyncSession | None, tenant_id: UUID) -> None:
        super().__init__(session=session, model=RefreshToken, tenant_id=tenant_id)

    async def create(
        self,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        user_agent: str | None = None,
        created_ip: str | None = None,
        impersonated_by: UUID | None = None,
    ) -> RefreshToken:
        """Crea un refresh token y lo persiste.

        Args:
            user_id: UUID del usuario dueño.
            token_hash: SHA-256 del token opaco.
            expires_at: Timestamp de expiración.
            user_agent: User-Agent del cliente (opcional).
            created_ip: IP del cliente (opcional).
            impersonated_by: UUID del actor real si es impersonación (opcional).

        Returns:
            RefreshToken instanciado.
        """
        token = RefreshToken(
            tenant_id=self.tenant_id,
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            created_ip=created_ip,
            impersonated_by=impersonated_by,
        )
        return await self.save(token)

    async def get_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        """Busca un token por su hash (SIN scope de tenant).

        El hash es UNIQUE global — el lookup es directo. El tenant se
        valida en service layer contra el token decodificado.

        Args:
            token_hash: SHA-256 hex del token opaco.

        Returns:
            RefreshToken o None.
        """
        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.deleted_at.is_(None),
        )
        return await self.session.scalar(stmt)  # type: ignore[union-attr]

    async def revoke(self, token_id: UUID) -> None:
        """Marca un token como revocado (soft revoke).

        Args:
            token_id: UUID del token a revocar.
        """
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.id == token_id)
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await self.session.execute(stmt)  # type: ignore[union-attr]

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        """Revoca TODOS los tokens activos de un usuario (no eliminados).

        Args:
            user_id: UUID del usuario.
        """
        now = datetime.now(timezone.utc)
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.tenant_id == self.tenant_id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.deleted_at.is_(None),
            )
            .values(revoked_at=now)
        )
        await self.session.execute(stmt)  # type: ignore[union-attr]

    async def revoke_family(self, user_id: UUID, token_id: UUID) -> int:
        """Revoca un token y todos los que lo referencian (reuso-detection).

        En casa de reuso de un refresh token ya revocado, la política de
        seguridad del spec exige revocar TODA la familia: esto es, todos
        los tokens del mismo ``user_id`` que no estén revocados.

        Returns:
            Cantidad de tokens revocados.
        """
        now = datetime.now(timezone.utc)
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.tenant_id == self.tenant_id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.deleted_at.is_(None),
            )
            .values(revoked_at=now)
        )
        result = await self.session.execute(stmt)  # type: ignore[union-attr]
        return result.rowcount  # type: ignore[no-any-return]

    async def count_active_for_user(self, user_id: UUID) -> int:
        """Cuenta los tokens activos (no revocados, no expirados, no eliminados).

        Args:
            user_id: UUID del usuario.

        Returns:
            Cantidad de tokens activos.
        """
        now = datetime.now(timezone.utc)
        stmt = select(func.count()).select_from(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.tenant_id == self.tenant_id,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > now,
            RefreshToken.deleted_at.is_(None),
        )
        result = await self.session.scalar(stmt)  # type: ignore[union-attr]
        return result or 0  # type: ignore[no-any-return]
