"""VersionPadronRepository — repository for VersionPadron model (tenant-scoped)."""

from typing import Optional
from uuid import UUID

from sqlalchemy import and_, select

from app.models.version_padron import VersionPadron
from app.repositories.base import BaseRepository


class VersionPadronRepository(BaseRepository[VersionPadron]):
    """Repository for tenant-scoped versiones de padron."""

    async def get_activa(
        self, materia_id: UUID, cohorte_id: UUID
    ) -> Optional[VersionPadron]:
        """Retorna la version activa para una materia x cohorte."""
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.materia_id == materia_id,
                    self.model.cohorte_id == cohorte_id,
                    self.model.activa.is_(True),
                )
            )
            .limit(1)
        )
        result = await self.session.scalar(stmt)
        return result

    async def desactivar_anteriores(
        self, materia_id: UUID, cohorte_id: UUID
    ) -> None:
        """Desactiva todas las versiones activas de una materia x cohorte."""
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.materia_id == materia_id,
                    self.model.cohorte_id == cohorte_id,
                    self.model.activa.is_(True),
                    self.model.tenant_id == self.tenant_id,
                    self.model.deleted_at.is_(None),
                )
            )
        )
        result = await self.session.scalars(stmt)
        for version in result:
            version.activa = False
            await self.session.flush()

    async def listar_por_materia(
        self, materia_id: UUID, cohorte_id: UUID
    ) -> list[VersionPadron]:
        """Lista todas las versiones de una materia x cohorte."""
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.materia_id == materia_id,
                    self.model.cohorte_id == cohorte_id,
                    self.model.tenant_id == self.tenant_id,
                    self.model.deleted_at.is_(None),
                )
            )
            .order_by(self.model.cargado_at.desc())
        )
        result = await self.session.scalars(stmt)
        return list(result.all())
