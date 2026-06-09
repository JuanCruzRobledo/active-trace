"""AsignacionRepository — repository for Asignacion model (tenant-scoped)."""

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import and_, select, update

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

    async def bulk_create(
        self, asignaciones: list[Asignacion]
    ) -> list[Asignacion]:
        """Crea multiples asignaciones en un solo flush.

        Args:
            asignaciones: Lista de instancias Asignacion a insertar.

        Returns:
            Lista de instancias persistidas con PK asignada.
        """
        if not asignaciones:
            return []
        self.session.add_all(asignaciones)
        await self.session.flush()
        return asignaciones

    async def list_by_equipo(
        self,
        materia_id: UUID,
        carrera_id: UUID,
        cohorte_id: UUID,
    ) -> list[Asignacion]:
        """Lista asignaciones que pertenecen a un equipo (materia×carrera×cohorte).

        Args:
            materia_id: UUID de la materia.
            carrera_id: UUID de la carrera.
            cohorte_id: UUID de la cohorte.

        Returns:
            Lista de asignaciones del equipo.
        """
        stmt = self._scope_query(self._list_query()).where(
            and_(
                self.model.materia_id == materia_id,
                self.model.carrera_id == carrera_id,
                self.model.cohorte_id == cohorte_id,
            )
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def update_vigencia_en_bloque(
        self,
        materia_id: UUID,
        carrera_id: UUID,
        cohorte_id: UUID,
        desde: datetime,
        hasta: datetime | None,
    ) -> int:
        """Actualiza desde/hasta en todas las asignaciones de un equipo.

        Args:
            materia_id: UUID de la materia.
            carrera_id: UUID de la carrera.
            cohorte_id: UUID de la cohorte.
            desde: Nuevo valor de ``desde``.
            hasta: Nuevo valor de ``hasta`` (None para limpiar).

        Returns:
            Cantidad de filas afectadas.
        """
        stmt = (
            update(self.model)
            .where(
                and_(
                    self.model.materia_id == materia_id,
                    self.model.carrera_id == carrera_id,
                    self.model.cohorte_id == cohorte_id,
                    self.model.tenant_id == self.tenant_id,
                )
            )
            .values(desde=desde, hasta=hasta)
            .execution_options(synchronize_session=False)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount
