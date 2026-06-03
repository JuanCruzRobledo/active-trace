"""RolPermisoRepository — repository for RolPermiso matrix."""

from uuid import UUID

from sqlalchemy import and_, select

from app.models.permiso import Permiso
from app.models.rol_permiso import RolPermiso
from app.repositories.base import BaseRepository


class RolPermisoRepository(BaseRepository[RolPermiso]):
    """Repository for role-permission assignments."""

    async def get_codigos_by_roles(self, rol_ids: list[UUID]) -> list[str]:
        if not rol_ids:
            return []
        stmt = (
            select(Permiso.codigo)
            .select_from(RolPermiso)
            .join(Permiso, RolPermiso.permiso_id == Permiso.id)
            .where(
                and_(
                    RolPermiso.rol_id.in_(rol_ids),
                    RolPermiso.tenant_id == self.tenant_id,
                )
            )
        )
        result = await self.session.execute(stmt)
        return [row[0] for row in result.all()]

    async def get_permiso_ids_by_rol(self, rol_id: UUID) -> list[RolPermiso]:
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.rol_id == rol_id,
                    self.model.tenant_id == self.tenant_id,
                )
            )
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def asignar(
        self, rol_id: UUID, permiso_id: UUID, tenant_id: UUID
    ) -> None:
        from uuid import uuid4
        inst = RolPermiso(
            id=uuid4(),
            tenant_id=tenant_id,
            rol_id=rol_id,
            permiso_id=permiso_id,
        )
        self.session.add(inst)
        await self.session.flush()
