"""CohorteRepository — repository for Cohorte model (tenant-scoped)."""

from typing import Optional

from sqlalchemy import and_, select

from app.models.cohorte import Cohorte
from app.repositories.base import BaseRepository


class CohorteRepository(BaseRepository[Cohorte]):
    """Repository for tenant-scoped cohortes."""

    async def get_by_nombre_and_carrera(
        self, nombre: str, carrera_id: str
    ) -> Optional[Cohorte]:
        stmt = select(self.model).where(
            and_(
                self.model.nombre == nombre,
                self.model.carrera_id == carrera_id,
                self.model.tenant_id == self.tenant_id,
                self.model.deleted_at.is_(None),
            )
        )
        result = await self.session.scalar(stmt)
        return result
