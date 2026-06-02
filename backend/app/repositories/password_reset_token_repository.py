"""Repositorio de PasswordResetToken — tokens efímeros de un solo uso.

Operaciones:
- ``create(user_id, token_hash, expires_at)`` → inserta un token.
- ``get_by_token_hash(hash)`` → lookup por hash (global UNIQUE).
- ``mark_used(token_id)`` → setea used_at.
- ``invalidate_all_pending_for_user(user_id)`` → marca como usados todos
  los tokens pendientes de un usuario (para que un nuevo reset los invalide).
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.password_reset_token import PasswordResetToken
from app.repositories.base import BaseRepository


class PasswordResetTokenRepository(BaseRepository[PasswordResetToken]):
    """Repositorio de tokens de reset (efímero — sin soft delete).

    Args:
        session: Sesión async de SQLAlchemy.
        tenant_id: UUID del tenant.
    """

    def __init__(self, session: AsyncSession | None, tenant_id: UUID) -> None:
        super().__init__(
            session=session,
            model=PasswordResetToken,
            tenant_id=tenant_id,
        )

    async def create(
        self,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> PasswordResetToken:
        """Crea un token de reset password.

        Args:
            user_id: UUID del usuario que solicita el reset.
            token_hash: SHA-256 del token opaco.
            expires_at: Timestamp de expiración.

        Returns:
            PasswordResetToken instanciado.
        """
        token = PasswordResetToken(
            tenant_id=self.tenant_id,
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        return await self.save(token)

    async def get_by_token_hash(self, token_hash: str) -> PasswordResetToken | None:
        """Busca un token por su hash (SIN scope de tenant — global UNIQUE).

        Args:
            token_hash: SHA-256 hex del token opaco.

        Returns:
            PasswordResetToken o None.
        """
        stmt = select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash
        )
        return await self.session.scalar(stmt)  # type: ignore[union-attr]

    async def mark_used(self, token_id: UUID) -> None:
        """Marca un token como usado.

        Args:
            token_id: UUID del token.
        """
        stmt = (
            update(PasswordResetToken)
            .where(PasswordResetToken.id == token_id)
            .values(used_at=datetime.now(timezone.utc))
        )
        await self.session.execute(stmt)  # type: ignore[union-attr]

    async def invalidate_all_pending_for_user(self, user_id: UUID) -> int:
        """Marca como usados todos los tokens pendientes de un usuario.

        Se llama cuando se solicita un nuevo reset: los tokens anteriores
        quedan inválidos.

        Args:
            user_id: UUID del usuario.

        Returns:
            Cantidad de tokens invalidados.
        """
        stmt = (
            update(PasswordResetToken)
            .where(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.tenant_id == self.tenant_id,
                PasswordResetToken.used_at.is_(None),
            )
            .values(used_at=datetime.now(timezone.utc))
        )
        result = await self.session.execute(stmt)  # type: ignore[union-attr]
        return result.rowcount  # type: ignore[no-any-return]
