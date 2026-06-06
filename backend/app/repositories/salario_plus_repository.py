"""SalarioPlusRepository — repository for SalarioPlus model (tenant-scoped)."""

from datetime import date
from uuid import UUID

from sqlalchemy import and_, select

from app.models.salario_plus import SalarioPlus
from app.repositories.base import BaseRepository


class SalarioPlusRepository(BaseRepository[SalarioPlus]):
    """Repository for tenant-scoped SalarioPlus operations."""

    async def find_vigente(self, grupo: str, rol: str, fecha: date | None = None) -> SalarioPlus | None:
        """Find the active SalarioPlus for a group/role at a given date.

        Args:
            grupo: Group/code of the plus key.
            rol: Role to look up.
            fecha: Date of reference (default: today).

        Returns:
            Active SalarioPlus instance or None if not found.
        """
        ref = fecha or date.today()
        stmt = self._scope_query(
            select(self.model).where(
                and_(
                    self.model.grupo == grupo,
                    self.model.rol == rol,
                    self.model.desde <= ref,
                    (self.model.hasta.is_(None)) | (self.model.hasta >= ref),
                )
            )
        )
        return await self._one_or_none(stmt)

    async def list_by_grupo(self, grupo: str) -> list[SalarioPlus]:
        """List all SalarioPlus entries for a given group.

        Args:
            grupo: Group/code to filter by.

        Returns:
            List of SalarioPlus instances.
        """
        stmt = self._scope_query(
            select(self.model).where(self.model.grupo == grupo)\
                .order_by(self.model.desde.desc())
        )
        result = await self.session.scalars(stmt)
        return list(result.all())
