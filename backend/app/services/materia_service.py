"""MateriaService — logica de negocio para Materias."""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.materia import Materia
from app.repositories.materia_repository import MateriaRepository
from app.schemas.materia import MateriaCreate, MateriaUpdate


class MateriaService:
    """Service for tenant-scoped materia operations."""

    def __init__(
        self,
        session: AsyncSession,
        tenant_id: UUID,
    ) -> None:
        self.repo = MateriaRepository(session, Materia, tenant_id)
        self.tenant_id = tenant_id

    async def crear(self, data: MateriaCreate) -> Materia:
        existe = await self.repo.get_by_codigo(data.codigo)
        if existe:
            from app.core.exceptions import BusinessError
            raise BusinessError("Ya existe una materia con ese codigo en el tenant")
        materia = Materia(
            tenant_id=self.tenant_id,
            codigo=data.codigo,
            nombre=data.nombre,
            estado=data.estado,
        )
        await self.repo.save(materia)
        return materia

    async def listar(self) -> list[Materia]:
        return await self.repo.list_all()

    async def obtener(self, materia_id: UUID) -> Optional[Materia]:
        return await self.repo.get_by_id(materia_id)

    async def actualizar(
        self, materia_id: UUID, data: MateriaUpdate
    ) -> Optional[Materia]:
        materia = await self.repo.get_by_id(materia_id)
        if materia is None:
            return None
        if data.nombre is not None:
            materia.nombre = data.nombre
        if data.estado is not None:
            materia.estado = data.estado
        await self.repo.save(materia)
        return materia
