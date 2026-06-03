"""AsignacionService — logica de negocio para Asignaciones.

Gestiona la creacion, actualizacion, baja logica y consulta de asignaciones
que vinculan usuarios con roles y contextos academicos.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError
from app.models.asignacion import Asignacion
from app.models.usuario import Usuario
from app.repositories.asignacion_repository import AsignacionRepository
from app.repositories.base import BaseRepository
from app.schemas.asignacion import AsignacionCreate, AsignacionUpdate


class AsignacionService:
    """Service for tenant-scoped Asignacion operations."""

    def __init__(
        self,
        session: AsyncSession,
        tenant_id: UUID,
    ) -> None:
        self.repo = AsignacionRepository(session, Asignacion, tenant_id)
        self.usuario_repo = BaseRepository(session, Usuario, tenant_id)
        self.tenant_id = tenant_id
        self.session = session

    async def create(self, data: AsignacionCreate) -> Asignacion:
        """Crea una nueva asignacion.

        Args:
            data: Datos de la asignacion.

        Returns:
            Asignacion creada.

        Raises:
            BusinessError: Si el usuario no existe.
        """
        # Validar existencia del usuario
        usuario_id = UUID(data.usuario_id)
        usuario = await self.usuario_repo.get_by_id(usuario_id)
        if usuario is None:
            raise BusinessError(
                f"No existe un usuario con id {data.usuario_id} en el tenant"
            )

        # Crear asignacion
        asignacion = Asignacion(
            tenant_id=self.tenant_id,
            usuario_id=usuario_id,
            rol=data.rol,
            materia_id=UUID(data.materia_id) if data.materia_id else None,
            carrera_id=UUID(data.carrera_id) if data.carrera_id else None,
            cohorte_id=UUID(data.cohorte_id) if data.cohorte_id else None,
            comisiones=data.comisiones,
            responsable_id=UUID(data.responsable_id) if data.responsable_id else None,
            desde=data.desde,
            hasta=data.hasta,
        )
        await self.repo.save(asignacion)
        return asignacion

    async def listar_por_usuario(
        self, usuario_id: UUID
    ) -> list[Asignacion]:
        """Lista todas las asignaciones de un usuario.

        Args:
            usuario_id: UUID del usuario.

        Returns:
            Lista de asignaciones del usuario.
        """
        return await self.repo.list_by_usuario(usuario_id)

    async def listar_por_contexto(
        self,
        materia_id: Optional[UUID] = None,
        carrera_id: Optional[UUID] = None,
        cohorte_id: Optional[UUID] = None,
        usuario_id: Optional[UUID] = None,
        rol: Optional[str] = None,
    ) -> list[Asignacion]:
        """Lista asignaciones filtradas por contexto academico.

        Args:
            materia_id: Filtrar por materia.
            carrera_id: Filtrar por carrera.
            cohorte_id: Filtrar por cohorte.
            usuario_id: Filtrar por usuario.
            rol: Filtrar por rol.

        Returns:
            Lista de asignaciones filtradas.
        """
        return await self.repo.list_by_context(
            materia_id=materia_id,
            carrera_id=carrera_id,
            cohorte_id=cohorte_id,
            usuario_id=usuario_id,
            rol=rol,
        )

    async def obtener(self, asignacion_id: UUID) -> Optional[Asignacion]:
        """Obtiene una asignacion por ID.

        Args:
            asignacion_id: UUID de la asignacion.

        Returns:
            Asignacion o None si no existe.
        """
        return await self.repo.get_by_id(asignacion_id)

    async def actualizar(
        self, asignacion_id: UUID, data: AsignacionUpdate
    ) -> Optional[Asignacion]:
        """Actualiza parcialmente una asignacion.

        Args:
            asignacion_id: UUID de la asignacion.
            data: Campos a actualizar.

        Returns:
            Asignacion actualizada o None si no existe.
        """
        asignacion = await self.repo.get_by_id(asignacion_id)
        if asignacion is None:
            return None

        if data.rol is not None:
            asignacion.rol = data.rol
        if data.materia_id is not None:
            asignacion.materia_id = UUID(data.materia_id)
        if data.carrera_id is not None:
            asignacion.carrera_id = UUID(data.carrera_id)
        if data.cohorte_id is not None:
            asignacion.cohorte_id = UUID(data.cohorte_id)
        if data.comisiones is not None:
            asignacion.comisiones = data.comisiones
        if data.responsable_id is not None:
            asignacion.responsable_id = UUID(data.responsable_id)
        if data.desde is not None:
            asignacion.desde = data.desde
        if data.hasta is not None:
            asignacion.hasta = data.hasta

        await self.repo.save(asignacion)
        return asignacion

    async def soft_delete(self, asignacion_id: UUID) -> None:
        """Realiza baja logica de una asignacion preservando historico.

        Args:
            asignacion_id: UUID de la asignacion a eliminar.
        """
        asignacion = await self.repo.get_by_id(asignacion_id)
        if asignacion is not None:
            await self.repo.soft_delete(asignacion)
