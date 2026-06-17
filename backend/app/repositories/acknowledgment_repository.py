"""AcknowledgmentRepository — acceso a datos de acuses de recibo (C-15).

Gestiona los acknowledgments de avisos: creacion con manejo de unique
constraint, consultas de estado por usuario y conteos por aviso.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.acknowledgment_aviso import AcknowledgmentAviso
from app.repositories.base import BaseRepository


class AcknowledgmentRepository(BaseRepository[AcknowledgmentAviso]):
    """Repository de acknowledgments con manejo de unique constraint."""

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        super().__init__(session, AcknowledgmentAviso, tenant_id)

    async def crear(
        self, aviso_id: UUID, usuario_id: UUID
    ) -> AcknowledgmentAviso | None:
        """Crea un acknowledgment usando pg_insert ON CONFLICT DO NOTHING.

        Args:
            aviso_id: UUID del aviso.
            usuario_id: UUID del usuario.

        Returns:
            AcknowledgmentAviso creado o None si ya existia (duplicado).
        """
        ahora = datetime.now(timezone.utc)
        from uuid import uuid4

        stmt = (
            pg_insert(AcknowledgmentAviso)
            .values(
                id=uuid4(),
                tenant_id=self.tenant_id,
                aviso_id=aviso_id,
                usuario_id=usuario_id,
                confirmado_at=ahora,
            )
            .on_conflict_do_nothing(
                index_elements=["aviso_id", "usuario_id"]
            )
        )
        result = await self.session.execute(stmt)
        await self.session.flush()

        # Si ON CONFLICT DO NOTHING no insertó (rowcount == 0) → duplicado
        if result.rowcount == 0:
            return None

        # Recuperar el registro creado
        return await self.buscar(aviso_id, usuario_id)

    async def buscar(
        self, aviso_id: UUID, usuario_id: UUID
    ) -> AcknowledgmentAviso | None:
        """Busca un acknowledgment por aviso y usuario.

        Args:
            aviso_id: UUID del aviso.
            usuario_id: UUID del usuario.

        Returns:
            AcknowledgmentAviso o None.
        """
        stmt = self._scope_query(
            select(self.model).where(
                and_(
                    self.model.aviso_id == aviso_id,
                    self.model.usuario_id == usuario_id,
                )
            )
        )
        result = await self.session.scalar(stmt)
        return result

    async def listar_por_aviso(
        self, aviso_id: UUID
    ) -> list[AcknowledgmentAviso]:
        """Lista todos los acknowledgments de un aviso.

        Args:
            aviso_id: UUID del aviso.

        Returns:
            Lista de acknowledgments.
        """
        stmt = self._scope_query(
            select(self.model).where(self.model.aviso_id == aviso_id)
        ).order_by(self.model.confirmado_at.desc())
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def contar_por_aviso(self, aviso_id: UUID) -> int:
        """Cuenta los acknowledgments de un aviso.

        Args:
            aviso_id: UUID del aviso.

        Returns:
            Cantidad de acknowledgments.
        """
        stmt = (
            select(func.count())
            .select_from(self.model)
            .where(
                and_(
                    self.model.aviso_id == aviso_id,
                    self.model.tenant_id == self.tenant_id,
                    self.model.deleted_at.is_(None),
                )
            )
        )
        result = await self.session.scalar(stmt)
        return result or 0
