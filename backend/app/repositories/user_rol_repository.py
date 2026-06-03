"""UserRolRepository — repository for user ↔ role assignments."""
from uuid import UUID, uuid4

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rol import Rol
from app.models.user_rol import UserRol
from app.repositories.base import BaseRepository


class UserRolRepository(BaseRepository[UserRol]):
    """Repository for user-role assignments (tenant-scoped).

    Args:
        session: Sesión async de SQLAlchemy.
        tenant_id: UUID del tenant — filtra todas las queries.
    """

    def __init__(self, session: AsyncSession | None, tenant_id: UUID) -> None:
        super().__init__(session=session, model=UserRol, tenant_id=tenant_id)

    async def get_role_codigos_for_user(self, user_id: UUID) -> list[str]:
        """Retorna los códigos de roles asignados a un usuario.

        Realiza JOIN user_rol → rol para obtener los códigos.
        Siempre scoped al tenant del repositorio.
        """
        stmt = (
            select(Rol.codigo)
            .select_from(UserRol)
            .join(Rol, UserRol.rol_id == Rol.id)
            .where(
                and_(
                    UserRol.user_id == user_id,
                    UserRol.tenant_id == self.tenant_id,
                    Rol.deleted_at.is_(None),
                )
            )
        )
        result = await self.session.execute(stmt)
        return [row[0] for row in result.all()]

    async def assign_role(self, user_id: UUID, rol_id: UUID) -> UserRol:
        """Asigna un rol a un usuario."""
        inst = UserRol(
            id=uuid4(),
            user_id=user_id,
            rol_id=rol_id,
            tenant_id=self.tenant_id,
        )
        self.session.add(inst)
        await self.session.flush()
        return inst
