"""SlotEncuentroRepository — acceso a datos de slots de encuentro (C-13).

Todas las queries filtran por tenant_id y excluyen registros soft-delete.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.slot_encuentro import SlotEncuentro
from app.repositories.base import BaseRepository


class SlotEncuentroRepository(BaseRepository[SlotEncuentro]):
    """Repository de slots de encuentro con filtros por materia y usuario."""

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        super().__init__(session, SlotEncuentro, tenant_id)

    async def listar(
        self,
        materia_id: UUID | None = None,
        usuario_id: UUID | None = None,
    ) -> list[SlotEncuentro]:
        """Lista slots con filtros opcionales.

        Args:
            materia_id: Filtrar por materia (opcional).
            usuario_id: Filtrar por usuario via Asignacion (opcional).

        Returns:
            Lista de slots activos del tenant.
        """
        from app.models.asignacion import Asignacion

        stmt = self._scope_query(select(self.model))
        if usuario_id is not None:
            stmt = stmt.join(Asignacion, self.model.asignacion_id == Asignacion.id)
            stmt = stmt.where(Asignacion.usuario_id == usuario_id)
        if materia_id is not None:
            stmt = stmt.where(self.model.materia_id == materia_id)

        stmt = stmt.order_by(self.model.dia_semana, self.model.hora)
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def listar_por_usuario(
        self, usuario_id: UUID
    ) -> list[SlotEncuentro]:
        """Lista slots de un usuario específico (por asignacion_id).

        Args:
            usuario_id: UUID del usuario (asignacion_id).

        Returns:
            Lista de slots del usuario.
        """
        stmt = self._scope_query(
            select(self.model).where(
                self.model.asignacion_id == usuario_id  # type: ignore[attr-defined]
            )
        ).order_by(self.model.dia_semana, self.model.hora)

        result = await self.session.scalars(stmt)
        return list(result.all())

    async def actualizar(
        self, slot_id: UUID, datos: dict
    ) -> SlotEncuentro | None:
        """Actualiza parcialmente un slot.

        Args:
            slot_id: UUID del slot.
            datos: Dict con campos a actualizar.

        Returns:
            Slot actualizado o None si no existe.
        """
        slot = await self.get_by_id(slot_id)
        if slot is None:
            return None
        for key, value in datos.items():
            if hasattr(slot, key):
                setattr(slot, key, value)
        await self.save(slot)
        return slot

    async def contar_instancias(self, slot_id: UUID) -> int:
        """Cuenta instancias asociadas a un slot.

        Args:
            slot_id: UUID del slot.

        Returns:
            Cantidad de instancias activas del slot.
        """
        from app.models.instancia_encuentro import InstanciaEncuentro

        stmt = select(func.count()).select_from(InstanciaEncuentro).where(
            and_(
                InstanciaEncuentro.slot_id == slot_id,
                InstanciaEncuentro.tenant_id == self.tenant_id,
                InstanciaEncuentro.deleted_at.is_(None),
            )
        )
        result = await self.session.scalar(stmt)
        return result or 0
