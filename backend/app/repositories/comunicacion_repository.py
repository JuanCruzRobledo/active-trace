"""ComunicacionRepository — acceso a datos del módulo de comunicaciones (C-12).

Todas las queries filtran por tenant_id y excluyen registros soft-delete.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import and_, func, select, update
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comunicacion import Comunicacion, EstadoComunicacion
from app.repositories.base import BaseRepository


class ComunicacionRepository(BaseRepository[Comunicacion]):
    """Repository de comunicaciones con soporte para lote, worker y aprobación."""

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        super().__init__(session, Comunicacion, tenant_id)

    def _tenant_filter(self) -> list:
        return [
            self.model.tenant_id == self.tenant_id,
            self.model.deleted_at.is_(None),
        ]

    async def crear_muchos(
        self,
        tenant_id: UUID,
        enviado_por_id: UUID,
        materia_id: UUID | None,
        lote_id: UUID,
        asunto: str,
        cuerpo: str,
        destinatarios: list[dict],
    ) -> list[Comunicacion]:
        """Crea N comunicaciones con el mismo lote_id y estado Pendiente.

        Args:
            tenant_id: UUID del tenant.
            enviado_por_id: UUID del usuario que envía.
            materia_id: UUID de la materia (opcional).
            lote_id: UUID que agrupa el envío masivo.
            asunto: Asunto del mensaje.
            cuerpo: Cuerpo del mensaje.
            destinatarios: Lista de {tipo, valor}.

        Returns:
            Lista de instancias Comunicacion creadas.
        """
        creadas: list[Comunicacion] = []
        for dest in destinatarios:
            c = Comunicacion(
                tenant_id=tenant_id,
                enviado_por_id=enviado_por_id,
                materia_id=materia_id,
                destinatario=dest["valor"],
                asunto=asunto,
                cuerpo=cuerpo,
                estado=EstadoComunicacion.Pendiente,
                lote_id=lote_id,
            )
            self.session.add(c)
            creadas.append(c)
        await self.session.flush()
        return creadas

    async def listar_por_lote(
        self, tenant_id: UUID, lote_id: UUID
    ) -> dict:
        """Consulta comunicaciones de un lote con conteo por estado.

        Returns:
            Dict con total, enviados, fallidos, cancelados, pendientes.
        """
        filters = [
            *self._tenant_filter(),
            self.model.lote_id == lote_id,
        ]
        base = select(self.model).where(and_(*filters))

        total_q = select(func.count()).select_from(self.model).where(and_(*filters))

        enviados_q = select(func.count()).select_from(self.model).where(
            and_(*filters, self.model.estado == EstadoComunicacion.Enviado)
        )
        fallidos_q = select(func.count()).select_from(self.model).where(
            and_(*filters, self.model.estado == EstadoComunicacion.Error)
        )
        cancelados_q = select(func.count()).select_from(self.model).where(
            and_(*filters, self.model.estado == EstadoComunicacion.Cancelado)
        )
        pendientes_q = select(func.count()).select_from(self.model).where(
            and_(*filters, self.model.estado == EstadoComunicacion.Pendiente)
        )

        total = await self.session.scalar(total_q) or 0
        enviados = await self.session.scalar(enviados_q) or 0
        fallidos = await self.session.scalar(fallidos_q) or 0
        cancelados = await self.session.scalar(cancelados_q) or 0
        pendientes = await self.session.scalar(pendientes_q) or 0

        return {
            "lote_id": lote_id,
            "total": total,
            "enviados": enviados,
            "fallidos": fallidos,
            "cancelados": cancelados,
            "pendientes": pendientes,
        }

    async def listar_pendientes_worker(
        self, tenant_id: UUID, limit: int = 50
    ) -> list[Comunicacion]:
        """SELECT FOR UPDATE SKIP LOCKED para el worker.

        Excluye comunicaciones que requieren aprobación no concedida.
        """
        filters = [
            *self._tenant_filter(),
            self.model.estado == EstadoComunicacion.Pendiente,
            self.model.necesita_aprobacion.is_(None),
        ]
        stmt = (
            select(self.model)
            .where(and_(*filters))
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def actualizar_estado(
        self,
        comunicacion_id: UUID,
        estado: EstadoComunicacion,
        enviado_at: datetime | None,
    ) -> None:
        """Update atómico de estado."""
        stmt = (
            update(Comunicacion)
            .where(
                and_(
                    Comunicacion.id == comunicacion_id,
                    Comunicacion.tenant_id == self.tenant_id,
                )
            )
            .values(
                estado=estado,
                enviado_at=enviado_at,
            )
        )
        await self.session.execute(stmt)

    async def cancelar(
        self, comunicacion_id: UUID, usuario_id: UUID
    ) -> bool:
        """Cancela una comunicación Pendiente propia.

        Returns:
            True si se canceló, False si no se cumplen las condiciones.
        """
        filters = [
            Comunicacion.id == comunicacion_id,
            Comunicacion.tenant_id == self.tenant_id,
            Comunicacion.enviado_por_id == usuario_id,
            Comunicacion.estado == EstadoComunicacion.Pendiente,
            Comunicacion.deleted_at.is_(None),
        ]
        stmt = (
            select(Comunicacion)
            .where(and_(*filters))
            .with_for_update()
        )
        result = await self.session.scalar(stmt)
        if result is None:
            return False
        result.estado = EstadoComunicacion.Cancelado
        await self.session.flush()
        return True

    async def cancelar_lote(
        self, lote_id: UUID, usuario_id: UUID
    ) -> bool:
        """Cancela todas las comunicaciones Pendientes de un lote.

        Returns:
            True si se canceló al menos una, False si no hay pendientes.
        """
        filters = [
            Comunicacion.lote_id == lote_id,
            Comunicacion.tenant_id == self.tenant_id,
            Comunicacion.enviado_por_id == usuario_id,
            Comunicacion.estado == EstadoComunicacion.Pendiente,
            Comunicacion.deleted_at.is_(None),
        ]
        stmt = (
            select(Comunicacion)
            .where(and_(*filters))
            .with_for_update()
        )
        rows = (await self.session.scalars(stmt)).all()
        if not rows:
            return False
        for row in rows:
            row.estado = EstadoComunicacion.Cancelado
        await self.session.flush()
        return True

    async def listar_por_usuario(
        self,
        tenant_id: UUID,
        usuario_id: UUID,
        pagina: int = 1,
        tamano: int = 20,
    ) -> tuple[list[Comunicacion], int]:
        """Historial paginado de comunicaciones de un usuario, agrupado por lote."""
        filters = [
            *self._tenant_filter(),
            self.model.enviado_por_id == usuario_id,
        ]

        total_q = select(func.count(func.distinct(self.model.lote_id))).select_from(
            self.model
        ).where(and_(*filters))
        total = await self.session.scalar(total_q) or 0

        lote_subq = (
            select(
                self.model.lote_id,
                func.row_number().over(
                    order_by=self.model.created_at.desc()
                ).label("rn"),
            )
            .where(and_(*filters))
            .distinct()
            .subquery()
        )

        offset = (pagina - 1) * tamano
        lotes_paginados = (
            select(lote_subq.c.lote_id)
            .where(lote_subq.c.rn <= offset + tamano)
        )
        lotes_result = await self.session.execute(lotes_paginados)
        lote_ids = [row[0] for row in lotes_result.all()]

        if not lote_ids:
            return [], total

        items_q = (
            select(self.model)
            .where(
                and_(
                    *self._tenant_filter(),
                    self.model.enviado_por_id == usuario_id,
                    self.model.lote_id.in_(lote_ids),
                )
            )
            .order_by(self.model.created_at.desc())
        )
        result = await self.session.scalars(items_q)
        items = list(result.all())

        # Dedicar solo los primeros por lote (para mostrar en historial)
        seen_lotes = set()
        deduped = []
        for item in items:
            if item.lote_id not in seen_lotes:
                seen_lotes.add(item.lote_id)
                deduped.append(item)
            if len(deduped) >= tamano:
                break

        return deduped, total

    async def listar_lotes_pendientes_aprobacion(
        self, tenant_id: UUID
    ) -> list[UUID]:
        """Lotes que requieren aprobación no concedida."""
        filters = [
            *self._tenant_filter(),
            self.model.necesita_aprobacion.isnot(None),
            self.model.estado == EstadoComunicacion.Pendiente,
        ]
        stmt = (
            select(func.distinct(self.model.lote_id))
            .where(and_(*filters))
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def aprobar_lote(
        self, lote_id: UUID, aprobador_id: UUID
    ) -> None:
        """Aprueba un lote: limpia flag de aprobación y registra aprobador."""
        now = datetime.now(timezone.utc)
        filters = [
            Comunicacion.lote_id == lote_id,
            Comunicacion.tenant_id == self.tenant_id,
        ]
        stmt = (
            update(Comunicacion)
            .where(and_(*filters))
            .values(
                necesita_aprobacion=None,
                aprobado_at=now,
                aprobado_por_id=aprobador_id,
            )
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def rechazar_lote(
        self, lote_id: UUID, aprobador_id: UUID
    ) -> None:
        """Rechaza un lote: cancela todas las comunicaciones."""
        now = datetime.now(timezone.utc)
        filters = [
            Comunicacion.lote_id == lote_id,
            Comunicacion.tenant_id == self.tenant_id,
        ]
        stmt = (
            update(Comunicacion)
            .where(and_(*filters))
            .values(
                estado=EstadoComunicacion.Cancelado,
                necesita_aprobacion=None,
                aprobado_at=now,
                aprobado_por_id=aprobador_id,
            )
        )
        await self.session.execute(stmt)
