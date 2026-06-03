"""CarreraRepository — repository for Carrera model (tenant-scoped)."""

from typing import Optional

from sqlalchemy import and_, select

from app.models.carrera import Carrera
from app.repositories.base import BaseRepository


class CarreraRepository(BaseRepository[Carrera]):
    """Repository for tenant-scoped carreras."""

    async def get_by_codigo(self, codigo: str) -> Optional[Carrera]:
        stmt = select(self.model).where(
            and_(
                self.model.codigo == codigo,
                self.model.tenant_id == self.tenant_id,
                self.model.deleted_at.is_(None),
            )
        )
        result = await self.session.scalar(stmt)
        return result
