"""GuardiaRepository — acceso a datos de guardias (C-13).

Todas las queries filtran por tenant_id y excluyen registros soft-delete.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.guardia import Guardia
from app.repositories.base import BaseRepository


class GuardiaRepository(BaseRepository[Guardia]):
    """Repository de guardias con filtros por materia, usuario, fechas y estado."""

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        super().__init__(session, Guardia, tenant_id)

    async def listar(
        self,
        materia_id: UUID | None = None,
        usuario_id: UUID | None = None,
        desde: date | None = None,
        hasta: date | None = None,
        estado: str | None = None,
    ) -> list[Guardia]:
        """Lista guardias con filtros opcionales.

        Args:
            materia_id: Filtrar por materia (opcional).
            usuario_id: Filtrar por usuario via asignacion_id (opcional).
            desde: Fecha desde (opcional).
            hasta: Fecha hasta (opcional).
            estado: Filtrar por estado (opcional).

        Returns:
            Lista de guardias activas del tenant.
        """
        conditions = []
        if materia_id is not None:
            conditions.append(self.model.materia_id == materia_id)
        if usuario_id is not None:
            conditions.append(self.model.asignacion_id == usuario_id)
        if desde is not None:
            conditions.append(self.model.creada_at >= desde)
        if hasta is not None:
            conditions.append(self.model.creada_at <= hasta)
        if estado is not None:
            conditions.append(self.model.estado == estado)

        stmt = self._scope_query(select(self.model))
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.order_by(self.model.creada_at.desc())

        result = await self.session.scalars(stmt)
        return list(result.all())

    async def actualizar(
        self, guardia_id: UUID, datos: dict
    ) -> Guardia | None:
        """Actualiza parcialmente una guardia.

        Args:
            guardia_id: UUID de la guardia.
            datos: Dict con campos a actualizar.

        Returns:
            Guardia actualizada o None si no existe.
        """
        guardia = await self.get_by_id(guardia_id)
        if guardia is None:
            return None
        for key, value in datos.items():
            if hasattr(guardia, key):
                setattr(guardia, key, value)
        await self.save(guardia)
        return guardia

    async def exportar(
        self,
        materia_id: UUID | None = None,
        usuario_id: UUID | None = None,
        desde: date | None = None,
        hasta: date | None = None,
        estado: str | None = None,
    ) -> list[Guardia]:
        """Query para exportación de guardias (reutiliza lógica de listar).

        Returns:
            Lista de guardias para exportar.
        """
        return await self.listar(
            materia_id=materia_id,
            usuario_id=usuario_id,
            desde=desde,
            hasta=hasta,
            estado=estado,
        )
