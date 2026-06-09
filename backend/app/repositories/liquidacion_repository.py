"""LiquidacionRepository — repository for Liquidacion model (tenant-scoped)."""

from uuid import UUID

from sqlalchemy import and_, select

from app.models.liquidacion import Liquidacion
from app.repositories.base import BaseRepository


class LiquidacionRepository(BaseRepository[Liquidacion]):
    """Repository for tenant-scoped Liquidacion operations."""

    async def find_by_periodo_usuario(
        self, periodo: str, usuario_id: UUID, rol: str
    ) -> Liquidacion | None:
        """Find a Liquidacion by period, user, and role.

        Args:
            periodo: YYYY-MM period string.
            usuario_id: UUID of the user.
            rol: Role filter.

        Returns:
            Liquidacion instance or None if not found.
        """
        stmt = self._scope_query(
            select(self.model).where(
                and_(
                    self.model.periodo == periodo,
                    self.model.usuario_id == usuario_id,
                    self.model.rol == rol,
                )
            )
        )
        return await self._one_or_none(stmt)

    async def list_by_periodo(self, periodo: str) -> list[Liquidacion]:
        """List all Liquidaciones for a given period.

        Args:
            periodo: YYYY-MM period string.

        Returns:
            List of Liquidacion instances.
        """
        stmt = self._scope_query(
            select(self.model).where(self.model.periodo == periodo)
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def list_by_cohorte(self, cohorte_id: UUID) -> list[Liquidacion]:
        """List all Liquidaciones for a given cohorte.

        Args:
            cohorte_id: UUID of the cohorte.

        Returns:
            List of Liquidacion instances.
        """
        stmt = self._scope_query(
            select(self.model).where(self.model.cohorte_id == cohorte_id)
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def list_abiertas(self) -> list[Liquidacion]:
        """List all open (Abierta) Liquidaciones for the tenant.

        Returns:
            List of Liquidacion instances with estado=Abierta.
        """
        stmt = self._scope_query(
            select(self.model).where(self.model.estado == "Abierta")
        )
        result = await self.session.scalars(stmt)
        return list(result.all())
