"""Repositorio de TwoFactorChallenge — challenge tokens efímeros para gate 2FA.

Operaciones:
- ``create(user_id, token_hash, expires_at)`` → inserta un challenge.
- ``get_by_token_hash(hash)`` → lookup por hash (global UNIQUE).
- ``mark_used(challenge_id)`` → setea used_at.
- ``cleanup_expired()`` → marca como usados los challenges expirados.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.two_factor_challenge import TwoFactorChallenge
from app.repositories.base import BaseRepository


class TwoFactorChallengeRepository(BaseRepository[TwoFactorChallenge]):
    """Repositorio de challenge tokens 2FA (efímero — sin soft delete).

    Args:
        session: Sesión async de SQLAlchemy.
        tenant_id: UUID del tenant.
    """

    def __init__(self, session: AsyncSession | None, tenant_id: UUID) -> None:
        super().__init__(
            session=session,
            model=TwoFactorChallenge,
            tenant_id=tenant_id,
        )

    async def create(
        self,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> TwoFactorChallenge:
        """Crea un challenge token para 2FA.

        Args:
            user_id: UUID del usuario que debe verificar TOTP.
            token_hash: SHA-256 del challenge opaco.
            expires_at: Timestamp de expiración (TTL 5 min).

        Returns:
            TwoFactorChallenge instanciado.
        """
        challenge = TwoFactorChallenge(
            tenant_id=self.tenant_id,
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        return await self.save(challenge)

    async def get_by_token_hash(self, token_hash: str) -> TwoFactorChallenge | None:
        """Busca un challenge por su hash (SIN scope de tenant — global UNIQUE).

        Args:
            token_hash: SHA-256 hex del challenge opaco.

        Returns:
            TwoFactorChallenge o None.
        """
        stmt = select(TwoFactorChallenge).where(
            TwoFactorChallenge.token_hash == token_hash
        )
        return await self.session.scalar(stmt)  # type: ignore[union-attr]

    async def mark_used(self, challenge_id: UUID) -> None:
        """Marca un challenge como usado.

        Args:
            challenge_id: UUID del challenge.
        """
        stmt = (
            update(TwoFactorChallenge)
            .where(TwoFactorChallenge.id == challenge_id)
            .values(used_at=datetime.now(timezone.utc))
        )
        await self.session.execute(stmt)  # type: ignore[union-attr]

    async def cleanup_expired(self) -> int:
        """Marca como usados todos los challenges expirados no usados.

        Returns:
            Cantidad de challenges marcados.
        """
        now = datetime.now(timezone.utc)
        stmt = (
            update(TwoFactorChallenge)
            .where(
                TwoFactorChallenge.used_at.is_(None),
                TwoFactorChallenge.expires_at < now,
            )
            .values(used_at=now)
        )
        result = await self.session.execute(stmt)  # type: ignore[union-attr]
        return result.rowcount  # type: ignore[no-any-return]
