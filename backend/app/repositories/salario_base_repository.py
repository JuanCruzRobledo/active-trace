"""SalarioBaseRepository — repository for SalarioBase model (tenant-scoped)."""

from datetime import date
from uuid import UUID

from sqlalchemy import and_, select

from app.models.salario_base import SalarioBase
from app.repositories.base import BaseRepository


class SalarioBaseRepository(BaseRepository[SalarioBase]):
    """Repository for tenant-scoped SalarioBase operations."""

    async def find_vigente(self, rol: str, fecha: date | None = None) -> SalarioBase | None:
        """Find the active SalarioBase for a role at a given date.

        Args:
            rol: Role to look up.
            fecha: Date of reference (default: today).

        Returns:
            Active SalarioBase instance or None if not found.
        """
        ref = fecha or date.today()
        stmt = self._scope_query(
            select(self.model).where(
                and_(
                    self.model.rol == rol,
                    self.model.desde <= ref,
                    (self.model.hasta.is_(None)) | (self.model.hasta >= ref),
                )
            )
        )
        return await self._one_or_none(stmt)

    async def list_by_rol(self, rol: str) -> list[SalarioBase]:
        """List all SalarioBase entries for a given role.

        Args:
            rol: Role to filter by.

        Returns:
            List of SalarioBase instances.
        """
        stmt = self._scope_query(
            select(self.model).where(self.model.rol == rol)\
                .order_by(self.model.desde.desc())
        )
        result = await self.session.scalars(stmt)
        return list(result.all())
