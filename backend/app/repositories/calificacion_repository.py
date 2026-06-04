"""CalificacionRepository — repository for Calificacion model (tenant-scoped)."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import case, select, update
from sqlalchemy import and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calificacion import Calificacion
from app.repositories.base import BaseRepository


class CalificacionRepository(BaseRepository[Calificacion]):
    """Repository for tenant-scoped calificaciones."""

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        super().__init__(session, Calificacion, tenant_id)

    async def list_by_materia(self, materia_id: UUID) -> list[Calificacion]:
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

    async def list_by_entrada_padron(
        self, entrada_padron_id: UUID
    ) -> list[Calificacion]:
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.entrada_padron_id == entrada_padron_id,
                    self.model.tenant_id == self.tenant_id,
                    self.model.deleted_at.is_(None),
                )
            )
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def find_by_actividad(
        self, materia_id: UUID, actividad: str
    ) -> list[Calificacion]:
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.materia_id == materia_id,
                    self.model.actividad == actividad,
                    self.model.tenant_id == self.tenant_id,
                    self.model.deleted_at.is_(None),
                )
            )
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def bulk_create(
        self, calificaciones: list[Calificacion]
    ) -> list[Calificacion]:
        self.session.add_all(calificaciones)
        await self.session.flush()
        return calificaciones

    async def delete_by_materia(self, materia_id: UUID) -> None:
        stmt = (
            update(self.model)
            .where(
                and_(
                    self.model.materia_id == materia_id,
                    self.model.tenant_id == self.tenant_id,
                    self.model.deleted_at.is_(None),
                )
            )
            .values(deleted_at=datetime.now(timezone.utc))
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def recalcular_aprobado(
        self,
        materia_id: UUID,
        umbral_pct: int,
        valores_aprobatorios: list[str] | None,
    ) -> int:
        when_clauses = [
            (
                self.model.nota_numerica.isnot(None),
                self.model.nota_numerica >= umbral_pct,
            ),
        ]

        if valores_aprobatorios:
            when_clauses.append(
                (
                    and_(
                        self.model.nota_numerica.is_(None),
                        self.model.nota_textual.isnot(None),
                        self.model.nota_textual.in_(valores_aprobatorios),
                    ),
                    True,
                )
            )
            when_clauses.append(
                (
                    and_(
                        self.model.nota_numerica.is_(None),
                        self.model.nota_textual.isnot(None),
                        ~self.model.nota_textual.in_(valores_aprobatorios),
                    ),
                    False,
                )
            )

        stmt = (
            update(self.model)
            .where(
                and_(
                    self.model.materia_id == materia_id,
                    self.model.tenant_id == self.tenant_id,
                    self.model.deleted_at.is_(None),
                )
            )
            .values(aprobado=case(*when_clauses, else_=None))
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount
