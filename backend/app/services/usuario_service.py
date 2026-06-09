"""UsuarioService — logica de negocio para Usuarios.

Gestiona el ciclo de vida de usuarios del dominio: creacion con cifrado de
PII, actualizacion, baja logica y consulta. La creacion incluye la auto-creacion
del User de autenticacion con password temporal.
"""

from __future__ import annotations

import secrets
from typing import Optional
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError
from app.core.security import hash_password
from app.models.usuario import Usuario
from app.repositories.usuario_repository import UsuarioRepository
from app.repositories.user_repository import UserRepository
from app.schemas.usuario import UsuarioCreate, UsuarioUpdate


class UsuarioService:
    """Service for tenant-scoped Usuario operations."""

    def __init__(
        self,
        session: AsyncSession,
        tenant_id: UUID,
    ) -> None:
        self.repo = UsuarioRepository(session, Usuario, tenant_id)
        self.auth_repo = UserRepository(session, tenant_id)
        self.tenant_id = tenant_id
        self.session = session

    async def create(self, data: UsuarioCreate) -> Usuario:
        """Crea un nuevo usuario con PII cifrada y su User de auth.

        Args:
            data: Datos del usuario a crear.

        Returns:
            Usuario creado.

        Raises:
            BusinessError: Si el email ya existe en el tenant.
        """
        # Validar unicidad de email por tenant
        existing = await self.repo.find_by_email(self.tenant_id, data.email)
        if existing is not None:
            raise BusinessError(
                f"Ya existe un usuario con email {data.email} en el tenant"
            )

        # Crear Usuario (PII se cifra automaticamente via EncryptedColumn)
        usuario = Usuario(
            tenant_id=self.tenant_id,
            nombre=data.nombre,
            apellidos=data.apellidos,
            email=data.email,
            dni=data.dni,
            cuil=data.cuil,
            cbu=data.cbu,
            alias_cbu=data.alias_cbu,
            banco=data.banco,
            regional=data.regional,
            legajo=data.legajo,
            legajo_profesional=data.legajo_profesional,
            facturador=data.facturador,
            estado=data.estado,
        )
        await self.repo.save(usuario)

        # Crear User de auth con password temporal
        temp_password = secrets.token_urlsafe(12)
        password_hash = hash_password(temp_password)
        try:
            auth_user = await self.auth_repo.create(
                email=data.email,
                password_hash=password_hash,
                is_active=True,
            )
        except IntegrityError as exc:
            # ``users`` tiene UniqueConstraint(tenant_id, email) — si ya
            # existe un User con ese email (por soft-delete previo o
            # conflicto real), se traduce a BusinessError de dominio.
            raise BusinessError(
                f"Ya existe una cuenta de autenticación con email "
                f"{data.email} en el tenant"
            ) from exc

        # Vincular auth_user_id
        usuario.auth_user_id = auth_user.id
        await self.repo.save(usuario)

        return usuario

    async def listar(self) -> list[Usuario]:
        """Lista todos los usuarios activos del tenant."""
        return await self.repo.list_all()

    async def listar_con_filtros(
        self,
        estado: Optional[str] = None,
        nombre: Optional[str] = None,
    ) -> list[Usuario]:
        """Lista usuarios con filtros opcionales."""
        return await self.repo.list_by_tenant(estado=estado, nombre=nombre)

    async def obtener(self, usuario_id: UUID) -> Optional[Usuario]:
        """Obtiene un usuario activo por ID.

        Args:
            usuario_id: UUID del usuario.

        Returns:
            Usuario activo o None si no existe o está soft-delete.
        """
        return await self.repo.get_by_id(usuario_id)

    async def obtener_incluyendo_eliminados(
        self, usuario_id: UUID
    ) -> Optional[Usuario]:
        """Obtiene un usuario incluyendo soft-deleteados.

        Args:
            usuario_id: UUID del usuario.

        Returns:
            Usuario (activo o soft-deleteado) o None si no existe.
        """
        return await self.repo.get_including_deleted(usuario_id)

    async def actualizar(
        self, usuario_id: UUID, data: UsuarioUpdate
    ) -> Optional[Usuario]:
        """Actualiza parcialmente un usuario.

        Args:
            usuario_id: UUID del usuario a actualizar.
            data: Campos a actualizar.

        Returns:
            Usuario actualizado o None si no existe.

        Raises:
            BusinessError: Si el nuevo email ya está ocupado.
        """
        usuario = await self.repo.get_by_id(usuario_id)
        if usuario is None:
            return None

        # Si se cambia el email, validar unicidad
        if data.email is not None and data.email != usuario.email:
            existing = await self.repo.find_by_email(
                self.tenant_id, data.email
            )
            if existing is not None and existing.id != usuario_id:
                raise BusinessError(
                    f"Ya existe un usuario con email {data.email} en el tenant"
                )

        if data.nombre is not None:
            usuario.nombre = data.nombre
        if data.apellidos is not None:
            usuario.apellidos = data.apellidos
        if data.email is not None:
            usuario.email = data.email
        if data.dni is not None:
            usuario.dni = data.dni
        if data.cuil is not None:
            usuario.cuil = data.cuil
        if data.cbu is not None:
            usuario.cbu = data.cbu
        if data.alias_cbu is not None:
            usuario.alias_cbu = data.alias_cbu
        if data.banco is not None:
            usuario.banco = data.banco
        if data.regional is not None:
            usuario.regional = data.regional
        if data.legajo is not None:
            usuario.legajo = data.legajo
        if data.legajo_profesional is not None:
            usuario.legajo_profesional = data.legajo_profesional
        if data.facturador is not None:
            usuario.facturador = data.facturador
        if data.estado is not None:
            usuario.estado = data.estado

        await self.repo.save(usuario)
        return usuario

    async def soft_delete(self, usuario_id: UUID) -> None:
        """Realiza baja logica de un usuario.

        Args:
            usuario_id: UUID del usuario a eliminar.
        """
        usuario = await self.repo.get_by_id(usuario_id)
        if usuario is not None:
            await self.repo.soft_delete(usuario)
