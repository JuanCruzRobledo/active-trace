"""PerfilService — gestion del perfil propio del usuario autenticado (C-20).

Auto-scopeado al usuario del JWT: la identidad NUNCA viene de la URL ni del body.
El CUIL es de solo lectura (PerfilUpdate lo excluye estructuralmente via schema).
Toda edicion genera audit PERFIL_EDITAR con nombres de campos (no valores PII).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError
from app.models.usuario import Usuario
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.perfil import PerfilUpdate
from app.services.audit_service import ACCION_PERFIL_EDITAR, AuditService


# Campos del perfil que el usuario puede editar (excluye cuil, estado, legajo admin)
_EDITABLE_FIELDS = frozenset({
    "nombre", "apellidos", "email", "dni",
    "banco", "cbu", "alias_cbu", "regional",
    "legajo_profesional", "facturador",
})


class PerfilService:
    """Servicio de perfil propio: obtener y editar el usuario del JWT."""

    def __init__(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        actor_id: UUID,
    ) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.actor_id = actor_id
        self.repo = UsuarioRepository(session, Usuario, tenant_id)

    def _build_audit(self) -> AuditService:
        from app.core.config import Settings  # noqa: PLC0415
        from app.repositories.audit_log_repository import AuditLogRepository  # noqa: PLC0415

        return AuditService(
            audit_log_repo=AuditLogRepository(self.session, self.tenant_id),
            settings=Settings(),
        )

    async def obtener_mio(self, usuario_id: UUID) -> Usuario:
        """Retorna el usuario por su id, scoped al tenant.

        Args:
            usuario_id: ID resuelto desde el JWT.

        Returns:
            Instancia de Usuario.

        Raises:
            BusinessError: Si el usuario no existe en el tenant.
        """
        usuario = await self.repo.get_by_id(usuario_id)
        if usuario is None:
            raise BusinessError("Perfil no encontrado")
        return usuario

    async def actualizar_mio(self, usuario_id: UUID, datos: PerfilUpdate) -> Usuario:
        """Actualiza parcialmente el perfil propio.

        Solo aplica los campos declarados en PerfilUpdate que tienen valor no None.
        Registra PERFIL_EDITAR con los nombres de campos modificados (sin valores).

        Args:
            usuario_id: ID resuelto desde el JWT.
            datos: Campos editables a actualizar.

        Returns:
            Usuario actualizado.

        Raises:
            BusinessError: Si el usuario no existe en el tenant.
        """
        usuario = await self.repo.get_by_id(usuario_id)
        if usuario is None:
            raise BusinessError("Perfil no encontrado")

        campos_cambiados: list[str] = []
        update_dict = datos.model_dump(exclude_none=True)
        for campo, valor in update_dict.items():
            if campo in _EDITABLE_FIELDS:
                setattr(usuario, campo, valor)
                campos_cambiados.append(campo)

        if campos_cambiados:
            await self.repo.save(usuario)
            audit = self._build_audit()
            await audit.register(
                accion=ACCION_PERFIL_EDITAR,
                actor_id=self.actor_id,
                tenant_id=self.tenant_id,
                detalle={"campos": sorted(campos_cambiados)},
            )

        return usuario
