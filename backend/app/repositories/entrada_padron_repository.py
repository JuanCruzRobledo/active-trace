"""EntradaPadronRepository — repository for EntradaPadron model (tenant-scoped)."""

from uuid import UUID

from sqlalchemy import and_, select

from app.models.entrada_padron import EntradaPadron
from app.repositories.base import BaseRepository


class EntradaPadronRepository(BaseRepository[EntradaPadron]):
    """Repository for tenant-scoped entradas de padron."""

    async def listar_por_version(self, version_id: UUID) -> list[EntradaPadron]:
        """Retorna todas las entradas de una version."""
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.version_id == version_id,
                    self.model.tenant_id == self.tenant_id,
                )
            )
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def contar_por_version(self, version_id: UUID) -> int:
        """Cuenta las entradas de una version."""
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.version_id == version_id,
                    self.model.tenant_id == self.tenant_id,
                )
            )
        )
        result = await self.session.scalars(stmt)
        return len(list(result.all()))

    async def eliminar_por_materia(
        self, materia_id: UUID, version_ids: list[UUID]
    ) -> None:
        """Elimina entradas asociadas a versiones de una materia."""
        if not version_ids:
            return
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.version_id.in_(version_ids),
                    self.model.tenant_id == self.tenant_id,
                )
            )
        )
        result = await self.session.scalars(stmt)
        for entrada in result:
            await self.session.delete(entrada)
