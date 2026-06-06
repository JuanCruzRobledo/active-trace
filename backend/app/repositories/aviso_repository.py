"""AvisoRepository — acceso a datos de avisos institucionales (C-15).

Todas las queries filtran por tenant_id y excluyen registros soft-delete.
Incluye metodos para timeline por usuario, conteo de universo por alcance
y eliminacion híbrida (hard/soft segun estado de acknowledgments).
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.aviso import Aviso
from app.models.acknowledgment_aviso import AcknowledgmentAviso
from app.repositories.base import BaseRepository


class AvisoRepository(BaseRepository[Aviso]):
    """Repository de avisos con filtros y timeline."""

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        super().__init__(session, Aviso, tenant_id)

    async def listar(
        self,
        materia_id: UUID | None = None,
        cohorte_id: UUID | None = None,
        alcance: str | None = None,
        severidad: str | None = None,
        activo: bool | None = None,
    ) -> list[Aviso]:
        """Lista avisos con filtros opcionales.

        Args:
            materia_id: Filtrar por materia.
            cohorte_id: Filtrar por cohorte.
            alcance: Filtrar por alcance.
            severidad: Filtrar por severidad.
            activo: Filtrar por estado activo.

        Returns:
            Lista de avisos del tenant.
        """
        stmt = self._scope_query(select(self.model))
        if materia_id is not None:
            stmt = stmt.where(self.model.materia_id == materia_id)
        if cohorte_id is not None:
            stmt = stmt.where(self.model.cohorte_id == cohorte_id)
        if alcance is not None:
            stmt = stmt.where(self.model.alcance == alcance)
        if severidad is not None:
            stmt = stmt.where(self.model.severidad == severidad)
        if activo is not None:
            stmt = stmt.where(self.model.activo == activo)

        stmt = stmt.order_by(
            self.model.severidad.desc(),
            self.model.orden.asc(),
            self.model.created_at.desc(),
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def listar_timeline(
        self,
        usuario_id: UUID,
        materia_ids: list[UUID] | None = None,
        cohorte_ids: list[UUID] | None = None,
        roles: list[str] | None = None,
    ) -> list[Aviso]:
        """Lista avisos activos visibles para un usuario.

        Aplica filtros de alcance: Global, PorMateria (si el usuario
        tiene materias en materia_ids), PorCohorte, PorRol.

        Args:
            usuario_id: UUID del usuario (para verificar acknowledgments).
            materia_ids: Materias del usuario.
            cohorte_ids: Cohortes del usuario.
            roles: Roles del usuario.

        Returns:
            Lista de avisos activos y vigentes ordenados.
        """
        ahora = datetime.now(timezone.utc)
        stmt = self._scope_query(
            select(self.model).where(
                and_(
                    self.model.activo == True,  # noqa: E712
                    self.model.inicio_en <= ahora,
                    self.model.fin_en >= ahora,
                )
            )
        )

        # Construir filtro de alcance
        condiciones_alcance = [self.model.alcance == "Global"]

        if materia_ids:
            condiciones_alcance.append(
                and_(
                    self.model.alcance == "PorMateria",
                    self.model.materia_id.in_(materia_ids),
                )
            )

        if cohorte_ids:
            condiciones_alcance.append(
                and_(
                    self.model.alcance == "PorCohorte",
                    self.model.cohorte_id.in_(cohorte_ids),
                )
            )

        if roles:
            condiciones_alcance.append(
                and_(
                    self.model.alcance == "PorRol",
                    self.model.rol_destino.in_(roles),
                )
            )

        stmt = stmt.where(or_(*condiciones_alcance))
        stmt = stmt.order_by(
            self.model.severidad.desc(),
            self.model.orden.asc(),
            self.model.created_at.desc(),
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def actualizar(
        self, aviso_id: UUID, datos: dict
    ) -> Aviso | None:
        """Actualiza parcialmente un aviso.

        Args:
            aviso_id: UUID del aviso.
            datos: Dict con campos a actualizar.

        Returns:
            Aviso actualizado o None si no existe.
        """
        aviso = await self.get_by_id(aviso_id)
        if aviso is None:
            return None
        for key, value in datos.items():
            if hasattr(aviso, key):
                setattr(aviso, key, value)
        await self.save(aviso)
        return aviso

    async def hard_delete(self, aviso_id: UUID) -> bool:
        """Elimina fisicamente un aviso (solo si no tiene acknowledgments).

        Args:
            aviso_id: UUID del aviso.

        Returns:
            True si se elimino, False si no existe.
        """
        aviso = await self.get_by_id(aviso_id)
        if aviso is None:
            return False

        await self.session.delete(aviso)
        await self.session.flush()
        return True

    async def tiene_acknowledgments(self, aviso_id: UUID) -> bool:
        """Verifica si un aviso tiene al menos un acknowledgment.

        Args:
            aviso_id: UUID del aviso.

        Returns:
            True si tiene al menos un acknowledgment.
        """
        from app.models.acknowledgment_aviso import AcknowledgmentAviso

        stmt = (
            select(func.count())
            .select_from(AcknowledgmentAviso)
            .where(
                and_(
                    AcknowledgmentAviso.aviso_id == aviso_id,
                    AcknowledgmentAviso.tenant_id == self.tenant_id,
                    AcknowledgmentAviso.deleted_at.is_(None),
                )
            )
        )
        result = await self.session.scalar(stmt)
        return (result or 0) > 0

    async def contar_usuarios_en_alcance(
        self,
        aviso: Aviso,
        materia_usuarios: list[UUID] | None = None,
        cohorte_usuarios: list[UUID] | None = None,
    ) -> int:
        """Cuenta usuarios alcanzados por un aviso segun su alcance.

        Args:
            aviso: Instancia del aviso.
            materia_usuarios: IDs de usuarios vinculados a la materia.
            cohorte_usuarios: IDs de usuarios vinculados a la cohorte.

        Returns:
            Cantidad de usuarios en el alcance.
        """
        if aviso.alcance == "Global":
            # Todos los usuarios activos del tenant
            from app.models.usuario import Usuario  # noqa: PLC0415

            stmt = (
                select(func.count())
                .select_from(Usuario)
                .where(
                    and_(
                        Usuario.tenant_id == self.tenant_id,
                        Usuario.deleted_at.is_(None),
                        Usuario.estado == "Activo",
                    )
                )
            )
            result = await self.session.scalar(stmt)
            return result or 0
        elif aviso.alcance == "PorMateria" and materia_usuarios:
            return len(set(materia_usuarios))
        elif aviso.alcance == "PorCohorte" and cohorte_usuarios:
            return len(set(cohorte_usuarios))
        elif aviso.alcance == "PorRol":
            from app.models.usuario import Usuario  # noqa: PLC0415
            from app.models.asignacion import Asignacion  # noqa: PLC0415

            stmt = (
                select(func.count(func.distinct(Usuario.id)))
                .select_from(Usuario)
                .join(Asignacion, Asignacion.usuario_id == Usuario.id)
                .where(
                    and_(
                        Usuario.tenant_id == self.tenant_id,
                        Usuario.deleted_at.is_(None),
                        Usuario.estado == "Activo",
                        Asignacion.tenant_id == self.tenant_id,
                        Asignacion.deleted_at.is_(None),
                        Asignacion.rol == aviso.rol_destino,
                    )
                )
            )
            result = await self.session.scalar(stmt)
            return result or 0

        return 0
