"""CarreraService — logica de negocio para Carreras."""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.carrera import Carrera
from app.repositories.carrera_repository import CarreraRepository
from app.schemas.carrera import CarreraCreate, CarreraUpdate


class CarreraService:
    """Service for tenant-scoped carrera operations."""

    def __init__(
        self,
        session: AsyncSession,
        tenant_id: UUID,
    ) -> None:
        self.repo = CarreraRepository(session, Carrera, tenant_id)
        self.tenant_id = tenant_id

    async def crear(self, data: CarreraCreate) -> Carrera:
        existe = await self.repo.get_by_codigo(data.codigo)
        if existe:
            from app.core.exceptions import BusinessError
            raise BusinessError("Ya existe una carrera con ese codigo en el tenant")
        carrera = Carrera(
            tenant_id=self.tenant_id,
            codigo=data.codigo,
            nombre=data.nombre,
            estado=data.estado,
        )
        await self.repo.save(carrera)
        return carrera

    async def listar(self) -> list[Carrera]:
        return await self.repo.list_all()

    async def obtener(self, carrera_id: UUID) -> Optional[Carrera]:
        return await self.repo.get_by_id(carrera_id)

    async def actualizar(
        self, carrera_id: UUID, data: CarreraUpdate
    ) -> Optional[Carrera]:
        carrera = await self.repo.get_by_id(carrera_id)
        if carrera is None:
            return None
        if data.nombre is not None:
            carrera.nombre = data.nombre
        if data.estado is not None:
            carrera.estado = data.estado
        await self.repo.save(carrera)
        return carrera
