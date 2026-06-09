"""PermissionService — resolves effective permissions from role codes."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.permiso import Permiso
from app.models.rol import Rol
from app.models.rol_permiso import RolPermiso
from app.repositories.permiso_repository import PermisoRepository
from app.repositories.rol_permiso_repository import RolPermisoRepository
from app.repositories.rol_repository import RolRepository


class PermissionService:
    """Resolves effective permissions from user roles, scoped by tenant."""

    def __init__(
        self,
        session: AsyncSession,
        tenant_id: UUID,
    ) -> None:
        self.rol_repo = RolRepository(session, Rol, tenant_id)
        self.permiso_repo = PermisoRepository(session, Permiso)
        self.rol_permiso_repo = RolPermisoRepository(
            session, RolPermiso, tenant_id
        )
        self.tenant_id = tenant_id

    async def get_effective_permissions(self, roles: list[str]) -> set[str]:
        """Resolve effective permissions from role codes.

        Args:
            roles: List of role codes (e.g. ["PROFESOR", "COORDINADOR"]).

        Returns:
            Set of permission codigos (e.g. {"calificaciones:importar", ...}).
        """
        if not roles:
            return set()
        roles_db = await self.rol_repo.get_by_codigos(roles)
        if not roles_db:
            return set()
        rol_ids = [r.id for r in roles_db]
        permisos = await self.rol_permiso_repo.get_codigos_by_roles(rol_ids)
        return set(permisos)

    async def has_permission(
        self, roles: list[str], permiso_requerido: str
    ) -> bool:
        efectivos = await self.get_effective_permissions(roles)
        return permiso_requerido in efectivos
