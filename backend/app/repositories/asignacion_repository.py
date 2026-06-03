"""AsignacionRepository — repository for Asignacion model (tenant-scoped)."""

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import and_, select

from app.models.asignacion import Asignacion
from app.repositories.base import BaseRepository


class AsignacionRepository(BaseRepository[Asignacion]):
    """Repository for tenant-scoped Asignacion operations."""

    async def list_by_usuario(
        self, usuario_id: UUID
    ) -> list[Asignacion]:
        """List all active asignaciones for a specific user.

        Args:
            usuario_id: UUID of the user.

        Returns:
            List of Asignacion instances for that user.
        """
        stmt = self._scope_query(
            select(self.model).where(
                self.model.usuario_id == usuario_id
            )
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def find_vigentes(self) -> list[Asignacion]:
        """Find all active asignaciones that are currently valid.

        An asignacion is vigente if:
        - ``hasta`` IS NULL OR ``hasta`` >= now
        - ``desde`` <= now

        Returns:
            List of active Asignacion instances.
        """
        now = datetime.now(timezone.utc)
        stmt = self._scope_query(
            select(self.model).where(
                and_(
                    self.model.desde <= now,
                    (self.model.hasta.is_(None)) | (self.model.hasta >= now),
                )
            )
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def list_by_context(
        self,
        materia_id: Optional[UUID] = None,
        carrera_id: Optional[UUID] = None,
        cohorte_id: Optional[UUID] = None,
        usuario_id: Optional[UUID] = None,
        rol: Optional[str] = None,
    ) -> list[Asignacion]:
        """List asignaciones filtered by academic context.

        Args:
            materia_id: Filter by materia.
            carrera_id: Filter by carrera.
            cohorte_id: Filter by cohorte.
            usuario_id: Filter by usuario.
            rol: Filter by rol.

        Returns:
            List of matching Asignacion instances.
        """
        stmt = self._scope_query(self._list_query())

        if materia_id is not None:
            stmt = stmt.where(self.model.materia_id == materia_id)
        if carrera_id is not None:
            stmt = stmt.where(self.model.carrera_id == carrera_id)
        if cohorte_id is not None:
            stmt = stmt.where(self.model.cohorte_id == cohorte_id)
        if usuario_id is not None:
            stmt = stmt.where(self.model.usuario_id == usuario_id)
        if rol is not None:
            stmt = stmt.where(self.model.rol == rol)

        result = await self.session.scalars(stmt)
        return list(result.all())
