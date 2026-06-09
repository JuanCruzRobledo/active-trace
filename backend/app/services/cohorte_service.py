"""CohorteService — logica de negocio para Cohortes.

Regla de negocio: carrera inactiva no admite cohortes abiertas.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cohorte import Cohorte
from app.models.carrera import Carrera
from app.repositories.cohorte_repository import CohorteRepository
from app.repositories.carrera_repository import CarreraRepository
from app.schemas.cohorte import CohorteCreate, CohorteUpdate


class CohorteService:
    """Service for tenant-scoped cohorte operations."""

    def __init__(
        self,
        session: AsyncSession,
        tenant_id: UUID,
    ) -> None:
        self.repo = CohorteRepository(session, Cohorte, tenant_id)
        self.carrera_repo = CarreraRepository(session, Carrera, tenant_id)
        self.tenant_id = tenant_id

    async def _validar_carrera_activa(
        self, carrera_id: UUID
    ) -> None:
        from app.core.exceptions import BusinessError
        carrera = await self.carrera_repo.get_by_id(carrera_id)
        if carrera is None:
            raise BusinessError("La carrera no existe")
        if carrera.estado == "Inactiva":
            raise BusinessError(
                "No se puede crear una cohorte en una carrera inactiva"
            )

    async def crear(self, data: CohorteCreate) -> Cohorte:
        await self._validar_carrera_activa(UUID(data.carrera_id))

        # Validar unicidad
        existe = await self.repo.get_by_nombre_and_carrera(
            data.nombre, data.carrera_id
        )
        if existe:
            from app.core.exceptions import BusinessError
            raise BusinessError(
                "Ya existe una cohorte con ese nombre en la misma carrera"
            )

        cohorte = Cohorte(
            tenant_id=self.tenant_id,
            carrera_id=UUID(data.carrera_id),
            nombre=data.nombre,
            anio=data.anio,
            vig_desde=data.vig_desde,
            vig_hasta=data.vig_hasta,
            estado=data.estado,
        )
        await self.repo.save(cohorte)
        return cohorte

    async def listar(self) -> list[Cohorte]:
        return await self.repo.list_all()

    async def obtener(self, cohorte_id: UUID) -> Optional[Cohorte]:
        return await self.repo.get_by_id(cohorte_id)

    async def actualizar(
        self, cohorte_id: UUID, data: CohorteUpdate
    ) -> Optional[Cohorte]:
        cohorte = await self.repo.get_by_id(cohorte_id)
        if cohorte is None:
            return None
        if data.nombre is not None:
            cohorte.nombre = data.nombre
        if data.vig_desde is not None:
            cohorte.vig_desde = data.vig_desde
        if data.vig_hasta is not None:
            cohorte.vig_hasta = data.vig_hasta
        if data.estado is not None:
            cohorte.estado = data.estado
        await self.repo.save(cohorte)
        return cohorte
