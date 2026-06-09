"""MateriaRepository — repository for Materia model (tenant-scoped)."""

from typing import Optional

from sqlalchemy import and_, select

from app.models.materia import Materia
from app.repositories.base import BaseRepository


class MateriaRepository(BaseRepository[Materia]):
    """Repository for tenant-scoped materias."""

    async def get_by_codigo(self, codigo: str) -> Optional[Materia]:
        stmt = select(self.model).where(
            and_(
                self.model.codigo == codigo,
                self.model.tenant_id == self.tenant_id,
                self.model.deleted_at.is_(None),
            )
        )
        result = await self.session.scalar(stmt)
        return result
