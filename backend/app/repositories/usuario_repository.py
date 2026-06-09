"""UsuarioRepository — repository for Usuario model (tenant-scoped)."""

from typing import Any, Optional
from uuid import UUID

from sqlalchemy import and_, select

from app.models.usuario import Usuario
from app.repositories.base import BaseRepository


class UsuarioRepository(BaseRepository[Usuario]):
    """Repository for tenant-scoped Usuario operations."""

    async def find_by_email(
        self, tenant_id: UUID, email: str
    ) -> Optional[Usuario]:
        """Find active user by email within a tenant.

        Since email is stored encrypted, this method compares against the
        decrypted value in memory. For performance with large datasets,
        consider adding a deterministic hash column.

        Args:
            tenant_id: Tenant UUID to scope the search.
            email: Plaintext email to search for.

        Returns:
            Usuario instance or None if not found.
        """
        stmt = select(self.model).where(
            and_(
                self.model.tenant_id == tenant_id,
                self.model.deleted_at.is_(None),
            )
        )
        result = await self.session.scalars(stmt)
        for usuario in result:
            if usuario.email == email:
                return usuario
        return None

    async def list_by_tenant(
        self,
        estado: Optional[str] = None,
        nombre: Optional[str] = None,
    ) -> list[Usuario]:
        """List active users with optional filters.

        Args:
            estado: Filter by estado (e.g., "Activo", "Inactivo").
            nombre: Filter by nombre (partial match, case-insensitive).

        Returns:
            List of Usuario instances matching the filters.
        """
        stmt = self._scope_query(self._list_query())

        if estado is not None:
            stmt = stmt.where(self.model.estado == estado)
        if nombre is not None:
            stmt = stmt.where(self.model.nombre.ilike(f"%{nombre}%"))

        result = await self.session.scalars(stmt)
        return list(result.all())

    async def get_including_deleted(self, id: Any) -> Optional[Usuario]:
        """Get a user by ID including soft-deleted records.

        Args:
            id: UUID of the user.

        Returns:
            Usuario instance or None.
        """
        stmt = select(self.model).where(
            and_(
                self.model.id == id,
                self.model.tenant_id == self.tenant_id,
            )
        )
        result = await self.session.scalar(stmt)
        return result
