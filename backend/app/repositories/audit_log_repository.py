"""AuditLogRepository — repositorio append-only para auditoría (C-05).

SOLO expone métodos de lectura y registro. NO expone ``update()``,
``soft_delete()``, ni ningún método de modificación.

El modelo ``AuditLog`` no hereda ``BaseMixin`` (no tiene ``updated_at``
ni ``deleted_at``). El scoping de tenant se aplica manualmente sin
el filtro de soft-delete.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


class AuditLogRepository:
    """Repositorio append-only de auditoría.

    Args:
        session: Sesión async de SQLAlchemy.
        tenant_id: UUID del tenant — filtra todas las queries.
    """

    def __init__(
        self,
        session: AsyncSession | None,
        tenant_id: UUID,
    ) -> None:
        self.session = session
        self.tenant_id = tenant_id

    # ── Query scoping ──────────────────────────────────────────────────

    def _scope_query(self, stmt):
        """Aplica scope de tenant a una query existente.

        NO incluye filtro ``deleted_at IS NULL`` — el modelo ``AuditLog``
        no tiene soft delete.
        """
        return stmt.where(AuditLog.tenant_id == self.tenant_id)

    # ── Public API (append‑only) ────────────────────────────────────────

    async def register(
        self,
        *,
        tenant_id: UUID,
        actor_id: UUID,
        accion: str,
        detalle: dict | None = None,
        filas_afectadas: int | None = None,
        materia_id: UUID | None = None,
        impersonado_id: UUID | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        """Inserta un registro de auditoría (append‑only).

        Args:
            tenant_id: UUID del tenant.
            actor_id: UUID del usuario que ejecutó la acción.
            accion: Código estandarizado de la acción.
            detalle: Contexto adicional JSON (opcional).
            filas_afectadas: Cantidad de registros involucrados (opcional).
            materia_id: UUID de la materia asociada (opcional).
            impersonado_id: UUID del usuario impersonado (opcional).
            ip: Dirección IP del cliente (opcional).
            user_agent: User-Agent del cliente (opcional).

        Returns:
            AuditLog instanciado con PK asignada y timestamp.
        """
        record = AuditLog(
            tenant_id=tenant_id or self.tenant_id,
            actor_id=actor_id,
            accion=accion,
            detalle=detalle,
            filas_afectadas=filas_afectadas,
            materia_id=materia_id,
            impersonado_id=impersonado_id,
            ip=ip,
            user_agent=user_agent,
        )
        if self.session is not None:
            self.session.add(record)
            await self.session.flush()
        return record

    async def get_by_id(self, id: UUID) -> AuditLog | None:
        """Retorna un registro por ID, scoped al tenant.

        Args:
            id: UUID del registro.

        Returns:
            AuditLog o None si no existe.
        """
        stmt = self._scope_query(
            select(AuditLog).where(AuditLog.id == id)
        )
        if self.session is not None:
            result = await self.session.scalar(stmt)
            return result
        return None

    async def list(
        self,
        *,
        actor_id: UUID | None = None,
        accion: str | None = None,
        materia_id: UUID | None = None,
        fecha_hora_desde: datetime | None = None,
        fecha_hora_hasta: datetime | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[AuditLog]:
        """Retorna registros de auditoría paginados y filtrados.

        Los resultados se ordenan por ``fecha_hora DESC`` (más reciente primero).

        Args:
            actor_id: Filtrar por actor (opcional).
            accion: Filtrar por código de acción (opcional).
            materia_id: Filtrar por materia (opcional).
            fecha_hora_desde: Filtrar desde esta fecha (opcional).
            fecha_hora_hasta: Filtrar hasta esta fecha (opcional).
            offset: Desplazamiento para paginación (default 0).
            limit: Máximo de registros a retornar (default 50).

        Returns:
            Lista de AuditLog (vacía si no hay registros).
        """
        stmt = self._scope_query(select(AuditLog))

        conditions = []
        if actor_id is not None:
            conditions.append(AuditLog.actor_id == actor_id)
        if accion is not None:
            conditions.append(AuditLog.accion == accion)
        if materia_id is not None:
            conditions.append(AuditLog.materia_id == materia_id)
        if fecha_hora_desde is not None:
            conditions.append(AuditLog.fecha_hora >= fecha_hora_desde)
        if fecha_hora_hasta is not None:
            conditions.append(AuditLog.fecha_hora <= fecha_hora_hasta)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = stmt.order_by(AuditLog.fecha_hora.desc())
        stmt = stmt.offset(offset).limit(limit)

        if self.session is not None:
            result = await self.session.scalars(stmt)
            return list(result.all())
        return []

    async def count(
        self,
        *,
        actor_id: UUID | None = None,
        accion: str | None = None,
        materia_id: UUID | None = None,
        fecha_hora_desde: datetime | None = None,
        fecha_hora_hasta: datetime | None = None,
    ) -> int:
        """Retorna el total de registros coincidentes (sin paginación).

        Args:
            actor_id: Filtrar por actor (opcional).
            accion: Filtrar por código de acción (opcional).
            materia_id: Filtrar por materia (opcional).
            fecha_hora_desde: Filtrar desde esta fecha (opcional).
            fecha_hora_hasta: Filtrar hasta esta fecha (opcional).

        Returns:
            Cantidad total de registros.
        """
        stmt = self._scope_query(select(func.count(AuditLog.id)))

        conditions = []
        if actor_id is not None:
            conditions.append(AuditLog.actor_id == actor_id)
        if accion is not None:
            conditions.append(AuditLog.accion == accion)
        if materia_id is not None:
            conditions.append(AuditLog.materia_id == materia_id)
        if fecha_hora_desde is not None:
            conditions.append(AuditLog.fecha_hora >= fecha_hora_desde)
        if fecha_hora_hasta is not None:
            conditions.append(AuditLog.fecha_hora <= fecha_hora_hasta)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        if self.session is not None:
            result = await self.session.scalar(stmt)
            return result or 0
        return 0
