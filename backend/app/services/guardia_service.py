"""GuardiaService — lógica de negocio para guardias de atención a alumnos (C-13).

Gestiona registro, edición, listado con scope según rol y exportación de
guardias de tutores/docentes.
"""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select as sa_select

from app.core.exceptions import BusinessError
from app.models.asignacion import Asignacion
from app.models.enums import DiaSemana, EstadoGuardia
from app.models.guardia import Guardia
from app.repositories.guardia_repository import GuardiaRepository
from app.schemas.guardias import GuardiaCreate, GuardiaUpdate
from app.services.audit_service import AuditService

# ── Audit action codes ─────────────────────────────────────────────────

ACCION_GUARDIA_REGISTRAR = "GUARDIA_REGISTRAR"
ACCION_GUARDIA_MODIFICAR = "GUARDIA_MODIFICAR"


class GuardiaService:
    """Servicio de guardias: CRUD con scope por rol."""

    def __init__(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        actor_id: UUID,
        roles: list[str],
    ) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.actor_id = actor_id
        self.roles = roles
        self.repo = GuardiaRepository(session, tenant_id)
        self._es_admin = any(r in ("COORDINADOR", "ADMIN") for r in roles)

    # ── Helpers ──────────────────────────────────────────────────────────

    def _build_audit_service(self) -> AuditService:
        from app.core.config import Settings
        from app.repositories.audit_log_repository import AuditLogRepository

        audit_repo = AuditLogRepository(self.session, self.tenant_id)
        return AuditService(audit_log_repo=audit_repo, settings=Settings())

    def _to_response(self, guardia: Guardia) -> dict[str, Any]:
        return {
            "id": guardia.id,
            "asignacion_id": guardia.asignacion_id,
            "materia_id": guardia.materia_id,
            "carrera_id": guardia.carrera_id,
            "cohorte_id": guardia.cohorte_id,
            "dia": guardia.dia.value if hasattr(guardia.dia, "value") else str(guardia.dia),
            "horario": guardia.horario,
            "estado": guardia.estado.value if hasattr(guardia.estado, "value") else str(guardia.estado),
            "comentarios": guardia.comentarios,
            "creada_at": str(guardia.creada_at) if guardia.creada_at else None,
            "created_at": str(guardia.created_at) if guardia.created_at else None,
            "updated_at": str(guardia.updated_at) if guardia.updated_at else None,
            "docente_nombre": None,
        }

    # ── Asignación lookup ────────────────────────────────────────────────

    async def _get_mi_asignacion_id(self) -> UUID:
        """Retorna el ``asignacion.id`` del usuario actual (actor_id).

        Busca la asignación activa (más reciente) del usuario en el tenant
        actual.  Si no existe, lanza BusinessError.

        Returns:
            UUID de la asignación.
        """
        stmt = (
            sa_select(Asignacion.id)
            .where(
                Asignacion.tenant_id == self.tenant_id,
                Asignacion.usuario_id == self.actor_id,
                Asignacion.deleted_at.is_(None),
            )
            .order_by(Asignacion.desde.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            raise BusinessError(
                "No se encontró una asignación activa para el usuario actual"
            )
        return row

    # ── Validación de alcance ─────────────────────────────────────────────

    async def _verificar_propiedad(self, guardia_id: UUID) -> Guardia:
        """Verifica que el usuario puede modificar una guardia.

        COORDINADOR/ADMIN pueden modificar cualquier guardia.
        TUTOR solo puede modificar sus propias guardias.

        Args:
            guardia_id: UUID de la guardia.

        Returns:
            Guardia si tiene acceso.

        Raises:
            BusinessError: Si no existe o no tiene permiso.
        """
        guardia = await self.repo.get_by_id(guardia_id)
        if guardia is None:
            raise BusinessError("Guardia no encontrada")

        if not self._es_admin:
            mi_asignacion_id = await self._get_mi_asignacion_id()
            if guardia.asignacion_id != mi_asignacion_id:
                raise BusinessError("No tiene permisos para modificar esta guardia")

        return guardia

    # ── Registro de guardia ───────────────────────────────────────────────

    async def registrar_guardia(
        self,
        datos: GuardiaCreate,
        asignacion_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Registra una nueva guardia.

        Args:
            datos: Datos de la guardia.
            asignacion_id: Asignación del docente (opcional, por defecto self).

        Returns:
            GuardiaResponse dict.

        Raises:
            BusinessError: Si hay error de validación.
        """
        dia_enum = DiaSemana(datos.dia)
        estado_enum = EstadoGuardia.PENDIENTE

        resolved_asignacion_id = asignacion_id
        if resolved_asignacion_id is None and not self._es_admin:
            resolved_asignacion_id = await self._get_mi_asignacion_id()

        guardia = Guardia(
            tenant_id=self.tenant_id,
            asignacion_id=resolved_asignacion_id,
            materia_id=datos.materia_id,
            carrera_id=datos.carrera_id,
            cohorte_id=datos.cohorte_id,
            dia=dia_enum,
            horario=datos.horario,
            estado=estado_enum,
            comentarios=datos.comentarios,
        )
        await self.repo.save(guardia)

        audit = self._build_audit_service()
        await audit.register(
            accion=ACCION_GUARDIA_REGISTRAR,
            actor_id=self.actor_id,
            tenant_id=self.tenant_id,
            materia_id=datos.materia_id,
            detalle={
                "guardia_id": str(guardia.id),
                "asignacion_id": str(guardia.asignacion_id),
            },
            filas_afectadas=1,
        )

        return self._to_response(guardia)

    # ── Edición de guardia ────────────────────────────────────────────────

    async def editar_guardia(
        self, guardia_id: UUID, datos: GuardiaUpdate
    ) -> dict[str, Any]:
        """Actualiza estado y/o comentarios de una guardia.

        Args:
            guardia_id: UUID de la guardia.
            datos: Datos a actualizar.

        Returns:
            GuardiaResponse dict.

        Raises:
            BusinessError: Si no existe o no tiene permiso.
        """
        guardia = await self._verificar_propiedad(guardia_id)

        update_data = datos.model_dump(exclude_none=True)
        if not update_data:
            return self._to_response(guardia)

        guardia_actualizada = await self.repo.actualizar(guardia_id, update_data)
        if guardia_actualizada is None:
            raise BusinessError("Guardia no encontrada")

        audit = self._build_audit_service()
        await audit.register(
            accion=ACCION_GUARDIA_MODIFICAR,
            actor_id=self.actor_id,
            tenant_id=self.tenant_id,
            materia_id=guardia.materia_id,
            detalle={
                "guardia_id": str(guardia_id),
                "cambios": update_data,
            },
            filas_afectadas=1,
        )

        return self._to_response(guardia_actualizada)

    # ── Listado ───────────────────────────────────────────────────────────

    async def listar_guardias(
        self,
        materia_id: UUID | None = None,
        usuario_id: UUID | None = None,
        desde: date | None = None,
        hasta: date | None = None,
        estado: str | None = None,
    ) -> dict[str, Any]:
        """Lista guardias con filtros, aplicando scope según rol.

        TUTOR ve solo sus propias guardias.
        COORDINADOR/ADMIN ve todas.

        Returns:
            Dict con items y total.
        """
        # Si no es admin y no se filtró por usuario, filtrar por sí mismo
        filter_usuario = usuario_id
        if not self._es_admin:
            filter_usuario = self.actor_id

        guardias = await self.repo.listar(
            materia_id=materia_id,
            usuario_id=filter_usuario,
            desde=desde,
            hasta=hasta,
            estado=estado,
        )
        items = [self._to_response(g) for g in guardias]
        return {"items": items, "total": len(items)}

    # ── Exportación ───────────────────────────────────────────────────────

    async def exportar_guardias(
        self,
        materia_id: UUID | None = None,
        usuario_id: UUID | None = None,
        desde: date | None = None,
        hasta: date | None = None,
        estado: str | None = None,
    ) -> list[dict[str, Any]]:
        """Exporta guardias aplicando filtros.

        Returns:
            Lista de dicts con datos de guardias.
        """
        guardias = await self.repo.exportar(
            materia_id=materia_id,
            usuario_id=usuario_id,
            desde=desde,
            hasta=hasta,
            estado=estado,
        )
        return [self._to_response(g) for g in guardias]
