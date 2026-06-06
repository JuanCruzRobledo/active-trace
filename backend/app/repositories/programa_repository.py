"""Repository para el modulo de programas de materia (C-17).

ProgramaMateriaRepository con scope de tenant obligatorio.
Hard delete en eliminacion (el modelo tiene deleted_at por herencia
de BaseMixin, pero la operacion de borrado es fisica).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.programa_materia import ProgramaMateria
from app.repositories.base import BaseRepository


class ProgramaMateriaRepository(BaseRepository[ProgramaMateria]):
    """Repository de programas de materia con filtros y hard delete."""

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        super().__init__(session, ProgramaMateria, tenant_id)

    async def create(self, programa: ProgramaMateria) -> ProgramaMateria:
        """Persiste un nuevo programa de materia.

        Args:
            programa: Instancia de ProgramaMateria a crear.

        Returns:
            El programa persistido.
        """
        return await self.save(programa)

    async def list(
        self,
        materia_id: UUID | None = None,
        carrera_id: UUID | None = None,
        cohorte_id: UUID | None = None,
    ) -> list[ProgramaMateria]:
        """Lista programas con filtros combinables.

        Args:
            materia_id: Filtrar por materia (opcional).
            carrera_id: Filtrar por carrera (opcional).
            cohorte_id: Filtrar por cohorte (opcional).

        Returns:
            Lista de programas ordenados por cargado_at DESC.
        """
        stmt = self._scope_query(select(ProgramaMateria))
        if materia_id is not None:
            stmt = stmt.where(ProgramaMateria.materia_id == materia_id)
        if carrera_id is not None:
            stmt = stmt.where(ProgramaMateria.carrera_id == carrera_id)
        if cohorte_id is not None:
            stmt = stmt.where(ProgramaMateria.cohorte_id == cohorte_id)
        stmt = stmt.order_by(ProgramaMateria.cargado_at.desc())
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def delete(self, programa_id: UUID) -> bool:
        """Elimina fisicamente un programa de materia (hard delete).

        Args:
            programa_id: UUID del programa a eliminar.

        Returns:
            True si se elimino, False si no existia.
        """
        stmt = (
            delete(ProgramaMateria)
            .where(
                ProgramaMateria.id == programa_id,
                ProgramaMateria.tenant_id == self.tenant_id,
            )
            .returning(ProgramaMateria.id)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one_or_none() is not None
