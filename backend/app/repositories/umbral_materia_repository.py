"""UmbralMateriaRepository — repository for UmbralMateria model (tenant-scoped)."""

from typing import Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.umbral_materia import UmbralMateria
from app.repositories.base import BaseRepository


class UmbralMateriaRepository(BaseRepository[UmbralMateria]):
    """Repository for tenant-scoped umbrales de materia."""

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        super().__init__(session, UmbralMateria, tenant_id)

    async def find_by_asignacion(self, asignacion_id: UUID) -> Optional[UmbralMateria]:
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.asignacion_id == asignacion_id,
                    self.model.tenant_id == self.tenant_id,
                    self.model.deleted_at.is_(None),
                )
            )
            .limit(1)
        )
        result = await self.session.scalar(stmt)
        return result

    async def find_by_materia(self, materia_id: UUID) -> list[UmbralMateria]:
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.materia_id == materia_id,
                    self.model.tenant_id == self.tenant_id,
                    self.model.deleted_at.is_(None),
                )
            )
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def upsert(
        self,
        asignacion_id: UUID,
        materia_id: UUID,
        umbral_pct: int,
        valores_aprobatorios: list[str] | None,
    ) -> UmbralMateria:
        # Buscar existente (activo o soft-deleted)
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.asignacion_id == asignacion_id,
                    self.model.tenant_id == self.tenant_id,
                )
            )
            .order_by(self.model.updated_at.desc())
            .limit(1)
        )
        existing = await self.session.scalar(stmt)

        if existing is not None:
            existing.umbral_pct = umbral_pct
            existing.valores_aprobatorios = valores_aprobatorios
            existing.deleted_at = None
            await self.session.flush()
            return existing

        instance = UmbralMateria(
            tenant_id=self.tenant_id,
            asignacion_id=asignacion_id,
            materia_id=materia_id,
            umbral_pct=umbral_pct,
            valores_aprobatorios=valores_aprobatorios,
        )
        self.session.add(instance)
        await self.session.flush()
        return instance
