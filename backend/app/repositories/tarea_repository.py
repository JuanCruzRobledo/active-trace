"""Repositories para el modulo de tareas internas (C-16).

TareaRepository y ComentarioRepository con scope de tenant obligatorio.
Todas las queries filtran por tenant_id.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import EstadoTarea
from app.models.tarea import ComentarioTarea, Tarea
from app.repositories.base import BaseRepository


class TareaRepository(BaseRepository[Tarea]):
    """Repository de tareas con filtros por asignado, estado, materia y busqueda textual."""

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        super().__init__(session, Tarea, tenant_id)

    async def create(self, tarea: Tarea) -> Tarea:
        """Persiste una nueva tarea.

        Args:
            tarea: Instancia de Tarea a crear.

        Returns:
            La tarea persistida.
        """
        return await self.save(tarea)

    async def list_by_asignado(
        self,
        asignado_a: UUID,
        estado: str | None = None,
        materia_id: UUID | None = None,
    ) -> list[Tarea]:
        """Lista tareas asignadas a un usuario.

        Args:
            asignado_a: UUID del usuario asignado.
            estado: Filtrar por estado (opcional).
            materia_id: Filtrar por materia (opcional).

        Returns:
            Lista de tareas ordenadas por created_at DESC.
        """
        stmt = self._scope_query(select(Tarea).where(Tarea.asignado_a == asignado_a))
        if estado is not None:
            stmt = stmt.where(Tarea.estado == estado)
        if materia_id is not None:
            stmt = stmt.where(Tarea.materia_id == materia_id)
        stmt = stmt.order_by(Tarea.created_at.desc())
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def list_by_tenant(
        self,
        estado: str | None = None,
        materia_id: UUID | None = None,
        asignado_a: UUID | None = None,
        asignado_por: UUID | None = None,
        busqueda: str | None = None,
    ) -> list[Tarea]:
        """Lista todas las tareas del tenant con filtros combinables.

        Args:
            estado: Filtrar por estado.
            materia_id: Filtrar por materia.
            asignado_a: Filtrar por usuario asignado.
            asignado_por: Filtrar por usuario asignador.
            busqueda: Busqueda textual ILIKE sobre descripcion.

        Returns:
            Lista de tareas filtradas ordenadas por created_at DESC.
        """
        stmt = self._scope_query(select(Tarea))
        if estado is not None:
            stmt = stmt.where(Tarea.estado == estado)
        if materia_id is not None:
            stmt = stmt.where(Tarea.materia_id == materia_id)
        if asignado_a is not None:
            stmt = stmt.where(Tarea.asignado_a == asignado_a)
        if asignado_por is not None:
            stmt = stmt.where(Tarea.asignado_por == asignado_por)
        if busqueda:
            stmt = stmt.where(Tarea.descripcion.ilike(f"%{busqueda}%"))
        stmt = stmt.order_by(Tarea.created_at.desc())
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def update_estado(
        self, tarea_id: UUID, nuevo_estado: EstadoTarea, estado_esperado: EstadoTarea | None = None,
    ) -> Tarea | None:
        """Actualiza el estado de una tarea con optimistic locking.

        Si se provee ``estado_esperado``, el UPDATE solo se ejecuta si
        el estado actual coincide, previniendo condiciones de carrera.

        Args:
            tarea_id: UUID de la tarea.
            nuevo_estado: Nuevo estado (valor del enum).
            estado_esperado: Estado actual esperado para optimistic locking.

        Returns:
            Tarea actualizada o None si no existe.
        """
        if estado_esperado is not None:
            from sqlalchemy import update as sa_update

            stmt = (
                sa_update(Tarea)
                .where(Tarea.id == tarea_id, Tarea.estado == estado_esperado.value)
                .values(estado=nuevo_estado.value)
                .returning(Tarea)
            )
            result = await self.session.scalars(stmt)
            await self.session.flush()
            return result.one_or_none()

        tarea = await self.get_by_id(tarea_id)
        if tarea is None:
            return None
        tarea.estado = nuevo_estado
        await self.save(tarea)
        return tarea

    async def update(self, tarea_id: UUID, datos: dict) -> Tarea | None:
        """Actualiza parcialmente una tarea.

        Args:
            tarea_id: UUID de la tarea.
            datos: Dict con campos a actualizar.

        Returns:
            Tarea actualizada o None si no existe.
        """
        tarea = await self.get_by_id(tarea_id)
        if tarea is None:
            return None
        for key, value in datos.items():
            if hasattr(tarea, key):
                setattr(tarea, key, value)
        await self.save(tarea)
        return tarea


class ComentarioRepository(BaseRepository[ComentarioTarea]):
    """Repository de comentarios de tareas (append-only)."""

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        super().__init__(session, ComentarioTarea, tenant_id)

    async def create(self, comentario: ComentarioTarea) -> ComentarioTarea:
        """Persiste un nuevo comentario.

        Args:
            comentario: Instancia de ComentarioTarea a crear.

        Returns:
            El comentario persistido.
        """
        return await self.save(comentario)

    async def list_by_tarea(self, tarea_id: UUID) -> list[ComentarioTarea]:
        """Lista los comentarios de una tarea en orden cronologico ascendente.

        Args:
            tarea_id: UUID de la tarea.

        Returns:
            Lista de comentarios ordenados por creado_at ASC.
        """
        stmt = (
            self._scope_query(
                select(ComentarioTarea).where(ComentarioTarea.tarea_id == tarea_id)
            )
            .order_by(ComentarioTarea.creado_at.asc())
        )
        result = await self.session.scalars(stmt)
        return list(result.all())
