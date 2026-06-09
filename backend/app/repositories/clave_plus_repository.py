"""ClavePlusRepository — repository for ClavePlus model (tenant-scoped)."""

from uuid import UUID

from sqlalchemy import select

from app.models.clave_plus import ClavePlus
from app.repositories.base import BaseRepository


class ClavePlusRepository(BaseRepository[ClavePlus]):
    """Repository for tenant-scoped ClavePlus operations."""

    async def find_by_codigo(self, codigo: str) -> ClavePlus | None:
        """Find a ClavePlus by codigo within the tenant scope.

        Args:
            codigo: Unique code identifying the plus key.

        Returns:
            ClavePlus instance or None if not found.
        """
        stmt = self._scope_query(
            select(self.model).where(self.model.codigo == codigo)
        )
        return await self._one_or_none(stmt)

    async def list_activas(self) -> list[ClavePlus]:
        """List all active ClavePlus records for the tenant.

        Returns:
            List of active ClavePlus instances.
        """
        stmt = self._scope_query(
            select(self.model).where(self.model.activa.is_(True))
        )
        result = await self.session.scalars(stmt)
        return list(result.all())
