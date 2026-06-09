"""PermisoRepository — repository for Permiso model (global, no tenant)."""

from typing import Optional

from sqlalchemy import select

from app.models.permiso import Permiso
from app.repositories.base import BaseRepository


class PermisoRepository(BaseRepository[Permiso]):
    """Repository for global permissions catalog.

    NOTE: Permiso has no tenant_id and no soft delete. The parent
    _scope_query would fail because tenant_id attribute doesn't exist.
    We override methods to bypass tenant scoping.
    """

    def __init__(self, session, model):
        super().__init__(session, model, tenant_id=None)

    async def get_by_codigo(self, codigo: str) -> Optional[Permiso]:
        stmt = select(self.model).where(self.model.codigo == codigo)
        result = await self.session.scalar(stmt)
        return result

    async def get_all(self) -> list[Permiso]:
        stmt = select(self.model)
        result = await self.session.scalars(stmt)
        return list(result.all())
