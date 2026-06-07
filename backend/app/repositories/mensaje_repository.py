"""Repositories para el modulo de mensajeria interna (C-20).

MensajeHiloRepository: hilos con scope tenant + filtro por participante.
MensajeRepository: mensajes append-only, marcar leido, contar no leidos.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mensaje import Mensaje, MensajeHilo
from app.repositories.base import BaseRepository


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MensajeHiloRepository(BaseRepository[MensajeHilo]):
    """Repository de hilos de mensajería interna — scope tenant obligatorio."""

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        super().__init__(session, MensajeHilo, tenant_id)

    async def create(self, hilo: MensajeHilo) -> MensajeHilo:
        return await self.save(hilo)

    async def list_by_participante(self, usuario_id: UUID) -> list[MensajeHilo]:
        """Lista hilos donde el usuario es participante (usuario_a o usuario_b).

        Ordenados por el mensaje más reciente DESC (usa subquery MAX creado_at).
        """
        last_msg_sq = (
            select(Mensaje.hilo_id, func.max(Mensaje.creado_at).label("last_at"))
            .group_by(Mensaje.hilo_id)
            .subquery()
        )
        stmt = (
            self._scope_query(select(MensajeHilo))
            .where(
                or_(
                    MensajeHilo.usuario_a_id == usuario_id,
                    MensajeHilo.usuario_b_id == usuario_id,
                )
            )
            .outerjoin(last_msg_sq, last_msg_sq.c.hilo_id == MensajeHilo.id)
            .order_by(last_msg_sq.c.last_at.desc().nullslast())
        )
        result = await self.session.scalars(stmt)
        return list(result.all())


class MensajeRepository(BaseRepository[Mensaje]):
    """Repository de mensajes append-only — scope tenant obligatorio."""

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        super().__init__(session, Mensaje, tenant_id)

    async def create(self, mensaje: Mensaje) -> Mensaje:
        self.session.add(mensaje)
        await self.session.flush()
        return mensaje

    async def list_by_hilo(self, hilo_id: UUID) -> list[Mensaje]:
        """Lista mensajes de un hilo en orden cronologico ascendente."""
        stmt = (
            select(Mensaje)
            .where(Mensaje.tenant_id == self.tenant_id, Mensaje.hilo_id == hilo_id)
            .order_by(Mensaje.creado_at.asc())
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def marcar_leido(self, mensaje_id: UUID) -> Mensaje | None:
        """Marca un mensaje como leido (leido_at = ahora)."""
        msg = await self.session.get(Mensaje, mensaje_id)
        if msg is None or msg.tenant_id != self.tenant_id:
            return None
        msg.leido_at = _utcnow()
        await self.session.flush()
        return msg

    async def count_no_leidos_para(self, hilo_id: UUID, destinatario_id: UUID) -> int:
        """Cuenta mensajes no leidos para el destinatario en un hilo.

        Mensajes del propio autor no cuentan como no leidos para el mismo.
        """
        stmt = select(func.count()).where(
            Mensaje.tenant_id == self.tenant_id,
            Mensaje.hilo_id == hilo_id,
            Mensaje.autor_id != destinatario_id,
            Mensaje.leido_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
