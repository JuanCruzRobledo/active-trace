"""FacturaRepository — repository for Factura model (tenant-scoped)."""

from uuid import UUID

from sqlalchemy import select

from app.models.factura import Factura
from app.repositories.base import BaseRepository


class FacturaRepository(BaseRepository[Factura]):
    """Repository for tenant-scoped Factura operations."""

    async def find_by_periodo_usuario(
        self, periodo: str, usuario_id: UUID
    ) -> Factura | None:
        """Find a Factura by period and user.

        Args:
            periodo: YYYY-MM period string.
            usuario_id: UUID of the user.

        Returns:
            Factura instance or None if not found.
        """
        stmt = self._scope_query(
            select(self.model).where(
                self.model.periodo == periodo,
                self.model.usuario_id == usuario_id,
            )
        )
        return await self._one_or_none(stmt)

    async def list_by_usuario(self, usuario_id: UUID) -> list[Factura]:
        """List all Facturas for a given user.

        Args:
            usuario_id: UUID of the user.

        Returns:
            List of Factura instances.
        """
        stmt = self._scope_query(
            select(self.model).where(self.model.usuario_id == usuario_id)
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def list_pendientes(self) -> list[Factura]:
        """List all pending (Pendiente) Facturas for the tenant.

        Returns:
            List of Factura instances with estado=Pendiente.
        """
        stmt = self._scope_query(
            select(self.model).where(self.model.estado == "Pendiente")
        )
        result = await self.session.scalars(stmt)
        return list(result.all())
