"""Repository para el modulo de fechas academicas (C-17).

FechaAcademicaRepository con scope de tenant obligatorio.
Soft delete estandar via BaseRepository.soft_delete().
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TipoFechaAcademica
from app.models.fecha_academica import FechaAcademica
from app.repositories.base import BaseRepository


class FechaAcademicaRepository(BaseRepository[FechaAcademica]):
    """Repository de fechas academicas con filtros y soft delete."""

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        super().__init__(session, FechaAcademica, tenant_id)

    async def create(self, fecha: FechaAcademica) -> FechaAcademica:
        """Persiste una nueva fecha academica.

        Args:
            fecha: Instancia de FechaAcademica a crear.

        Returns:
            La fecha persistida.
        """
        return await self.save(fecha)

    async def list(
        self,
        materia_id: UUID | None = None,
        cohorte_id: UUID | None = None,
        tipo: TipoFechaAcademica | None = None,
        periodo: str | None = None,
    ) -> list[FechaAcademica]:
        """Lista fechas con filtros combinables, ordenadas por fecha ASC.

        Args:
            materia_id: Filtrar por materia (opcional).
            cohorte_id: Filtrar por cohorte (opcional).
            tipo: Filtrar por tipo (opcional).
            periodo: Filtrar por periodo (opcional).

        Returns:
            Lista de fechas activas ordenadas por fecha ASC.
        """
        stmt = self._scope_query(select(FechaAcademica))
        if materia_id is not None:
            stmt = stmt.where(FechaAcademica.materia_id == materia_id)
        if cohorte_id is not None:
            stmt = stmt.where(FechaAcademica.cohorte_id == cohorte_id)
        if tipo is not None:
            stmt = stmt.where(FechaAcademica.tipo == tipo)
        if periodo is not None:
            stmt = stmt.where(FechaAcademica.periodo == periodo)
        stmt = stmt.order_by(FechaAcademica.fecha.asc())
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def update(
        self, fecha_id: UUID, datos: dict
    ) -> FechaAcademica | None:
        """Actualiza parcialmente una fecha academica.

        Args:
            fecha_id: UUID de la fecha.
            datos: Dict con campos a actualizar.

        Returns:
            Fecha actualizada o None si no existe.
        """
        fecha = await self.get_by_id(fecha_id)
        if fecha is None:
            return None
        for key, value in datos.items():
            if hasattr(fecha, key):
                setattr(fecha, key, value)
        await self.save(fecha)
        return fecha
