"""RolRepository — repository for Rol model (tenant-scoped)."""

from typing import Optional
from uuid import UUID

from sqlalchemy import and_, select

from app.models.rol import Rol
from app.repositories.base import BaseRepository


class RolRepository(BaseRepository[Rol]):
    """Repository for tenant-scoped roles."""

    async def get_by_codigo(self, codigo: str) -> Optional[Rol]:
        stmt = select(self.model).where(
            and_(
                self.model.codigo == codigo,
                self.model.tenant_id == self.tenant_id,
            )
        )
        result = await self.session.scalar(stmt)
        return result

    async def get_by_codigos(self, codigos: list[str]) -> list[Rol]:
        if not codigos:
            return []
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.codigo.in_(codigos),
                    self.model.tenant_id == self.tenant_id,
                )
            )
        )
        result = await self.session.scalars(stmt)
        return list(result.all())
