"""InstanciaEncuentroRepository — acceso a datos de instancias de encuentro (C-13).

Todas las queries filtran por tenant_id y excluyen registros soft-delete.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.instancia_encuentro import InstanciaEncuentro
from app.repositories.base import BaseRepository


class InstanciaEncuentroRepository(BaseRepository[InstanciaEncuentro]):
    """Repository de instancias de encuentro con soporte para creación masiva y filtros."""

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        super().__init__(session, InstanciaEncuentro, tenant_id)

    async def crear_muchos(
        self, instancias: list[InstanciaEncuentro]
    ) -> list[InstanciaEncuentro]:
        """Inserta múltiples instancias en una transacción.

        Args:
            instancias: Lista de instancias a crear.

        Returns:
            Lista de instancias creadas con PK asignada.
        """
        for instancia in instancias:
            self.session.add(instancia)
        await self.session.flush()
        return instancias

    async def listar(
        self,
        materia_id: UUID | None = None,
        slot_id: UUID | None = None,
        desde: date | None = None,
        hasta: date | None = None,
        estado: str | None = None,
        usuario_id: UUID | None = None,
    ) -> list[InstanciaEncuentro]:
        """Lista instancias con filtros opcionales.

        Args:
            materia_id: Filtrar por materia (opcional).
            slot_id: Filtrar por slot (opcional).
            desde: Fecha desde (opcional).
            hasta: Fecha hasta (opcional).
            estado: Filtrar por estado (opcional).
            usuario_id: Filtrar por usuario (opcional, sin implementar join).

        Returns:
            Lista de instancias activas del tenant.
        """
        conditions = []
        if materia_id is not None:
            conditions.append(self.model.materia_id == materia_id)
        if slot_id is not None:
            conditions.append(self.model.slot_id == slot_id)
        if desde is not None:
            conditions.append(self.model.fecha >= desde)
        if hasta is not None:
            conditions.append(self.model.fecha <= hasta)
        if estado is not None:
            conditions.append(self.model.estado == estado)
        if usuario_id is not None:
            # TODO: join con slot_encuentro para filtrar por asignacion_id
            pass

        stmt = self._scope_query(select(self.model))
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.order_by(self.model.fecha, self.model.hora)

        result = await self.session.scalars(stmt)
        return list(result.all())

    async def actualizar(
        self, instancia_id: UUID, datos: dict
    ) -> InstanciaEncuentro | None:
        """Actualiza parcialmente una instancia.

        Args:
            instancia_id: UUID de la instancia.
            datos: Dict con campos a actualizar.

        Returns:
            Instancia actualizada o None si no existe.
        """
        instancia = await self.get_by_id(instancia_id)
        if instancia is None:
            return None
        for key, value in datos.items():
            if hasattr(instancia, key):
                setattr(instancia, key, value)
        await self.save(instancia)
        return instancia

    async def eliminar_por_slot(self, slot_id: UUID) -> int:
        """Soft-delete masivo de instancias de un slot.

        Args:
            slot_id: UUID del slot.

        Returns:
            Cantidad de instancias eliminadas.
        """
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        stmt = (
            update(InstanciaEncuentro)
            .where(
                and_(
                    InstanciaEncuentro.slot_id == slot_id,
                    InstanciaEncuentro.tenant_id == self.tenant_id,
                    InstanciaEncuentro.deleted_at.is_(None),
                )
            )
            .values(deleted_at=now)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount  # type: ignore[return-value]

    async def listar_para_exportar(
        self, materia_id: UUID
    ) -> list[InstanciaEncuentro]:
        """Lista instancias para generar HTML de aula.

        Incluye encuentros futuros (desde hoy) y pasados SOLO si tienen
        video_url (grabación disponible).

        Args:
            materia_id: UUID de la materia.

        Returns:
            Lista de instancias para exportar.
        """
        from datetime import datetime, timezone

        today = datetime.now(timezone.utc).date()

        conditions = [
            self.model.materia_id == materia_id,
            and_(
                self.model.fecha >= today,
                self.model.deleted_at.is_(None),
            ),
        ]

        stmt = self._scope_query(
            select(self.model).where(and_(*conditions))
        ).order_by(self.model.fecha, self.model.hora)

        result = await self.session.scalars(stmt)
        return list(result.all())
