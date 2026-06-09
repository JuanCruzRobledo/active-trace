"""Repositorio de User — acceso a datos de usuarios.

Operaciones:
- ``get_by_email(tenant_id, email)`` → lookup único por email dentro del tenant.
- ``get_by_id(tenant_id, id)`` → lookup por PK scoped.
- ``create(email, password_hash, ...)`` → inserta un usuario.
- ``update_password(user_id, new_hash)`` → actualiza password_hash.
- ``enable_totp(user_id, encrypted_secret)`` → activa 2FA.
- ``disable_totp(user_id)`` → desactiva 2FA.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repositorio de usuarios con scope multi-tenant.

    Args:
        session: Sesión async de SQLAlchemy.
        tenant_id: UUID del tenant — filtra todas las queries.
    """

    def __init__(self, session: AsyncSession | None, tenant_id: UUID) -> None:
        super().__init__(session=session, model=User, tenant_id=tenant_id)

    async def get_by_email(self, email: str) -> User | None:
        """Retorna un usuario activo por email dentro del tenant.

        Args:
            email: Email del usuario a buscar.

        Returns:
            User o None si no existe o está soft-delete.
        """
        stmt = self._scope_query(
            select(User).where(User.email == email)
        )
        return await self.session.scalar(stmt)  # type: ignore[union-attr]

    async def create(
        self,
        email: str,
        password_hash: str,
        is_active: bool = True,
    ) -> User:
        """Crea un usuario y lo persiste en la sesión actual.

        Args:
            email: Email del usuario.
            password_hash: Hash Argon2id del password.
            is_active: Si el usuario arranca activo (default True).

        Returns:
            User instanciado con PK asignada.
        """
        user = User(
            tenant_id=self.tenant_id,
            email=email,
            password_hash=password_hash,
            is_active=is_active,
        )
        return await self.save(user)

    async def update_password(self, user_id: UUID, new_hash: str) -> None:
        """Actualiza el password_hash de un usuario (scoped).

        Args:
            user_id: UUID del usuario.
            new_hash: Nuevo hash Argon2id.
        """
        stmt = (
            update(User)
            .where(
                User.id == user_id,
                User.tenant_id == self.tenant_id,
                User.deleted_at.is_(None),
            )
            .values(password_hash=new_hash)
        )
        await self.session.execute(stmt)  # type: ignore[union-attr]

    async def enable_totp(self, user_id: UUID, encrypted_secret: str) -> None:
        """Activa 2FA TOTP para un usuario.

        Args:
            user_id: UUID del usuario.
            encrypted_secret: Secreto TOTP cifrado con Fernet.
        """
        stmt = (
            update(User)
            .where(
                User.id == user_id,
                User.tenant_id == self.tenant_id,
                User.deleted_at.is_(None),
            )
            .values(totp_secret=encrypted_secret, totp_enabled=True)
        )
        await self.session.execute(stmt)  # type: ignore[union-attr]

    async def disable_totp(self, user_id: UUID) -> None:
        """Desactiva 2FA TOTP para un usuario.

        Args:
            user_id: UUID del usuario.
        """
        stmt = (
            update(User)
            .where(
                User.id == user_id,
                User.tenant_id == self.tenant_id,
                User.deleted_at.is_(None),
            )
            .values(totp_secret=None, totp_enabled=False)
        )
        await self.session.execute(stmt)  # type: ignore[union-attr]
