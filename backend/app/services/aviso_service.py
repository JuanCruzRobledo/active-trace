"""AvisoService — logica de negocio para avisos institucionales (C-15).

Gestiona el ciclo completo: creacion, edicion, eliminacion segura,
timeline segmentada por rol/usuario, acknowledgment con tracking de
agregados y auditoria de todas las acciones.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError
from app.models.aviso import Aviso
from app.models.acknowledgment_aviso import AcknowledgmentAviso
from app.repositories.aviso_repository import AvisoRepository
from app.repositories.acknowledgment_repository import AcknowledgmentRepository
from app.schemas.avisos import (
    AvisoCreate,
    AvisoResponse,
    AvisoUpdate,
    AvisoTimelineItem,
    AvisoTimelineResponse,
    TrackingAvisoResponse,
    TrackingAckItem,
    AcknowledgmentResponse,
)
from app.services.audit_service import AuditService

from app.services.audit_service import (
    ACCION_AVISO_ACK,
    ACCION_AVISO_CREAR,
    ACCION_AVISO_ELIMINAR,
    ACCION_AVISO_MODIFICAR,
)


class AvisoService:
    """Servicio de avisos: CRUD, timeline, acknowledgment y tracking."""

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
        self.aviso_repo = AvisoRepository(session, tenant_id)
        self.ack_repo = AcknowledgmentRepository(session, tenant_id)

    # ── Helpers ──────────────────────────────────────────────────────────

    def _build_audit_service(self) -> AuditService:
        from app.core.config import Settings  # noqa: PLC0415
        from app.repositories.audit_log_repository import AuditLogRepository  # noqa: PLC0415

        audit_repo = AuditLogRepository(self.session, self.tenant_id)
        return AuditService(audit_log_repo=audit_repo, settings=Settings())

    async def _to_aviso_response(
        self, aviso: Aviso,
        total_ack: int | None = None,
        total_usuarios: int | None = None,
    ) -> dict:
        """Construye respuesta con datos del aviso."""
        if total_ack is None:
            total_ack = await self.ack_repo.contar_por_aviso(aviso.id)
        if total_usuarios is None:
            total_usuarios = await self.aviso_repo.contar_usuarios_en_alcance(
                aviso
            )

        porcentaje = 0.0
        if total_usuarios > 0:
            porcentaje = round((total_ack / total_usuarios) * 100, 1)

        return {
            "id": aviso.id,
            "alcance": aviso.alcance.value if hasattr(aviso.alcance, "value") else str(aviso.alcance),
            "materia_id": aviso.materia_id,
            "cohorte_id": aviso.cohorte_id,
            "rol_destino": aviso.rol_destino,
            "severidad": aviso.severidad.value if hasattr(aviso.severidad, "value") else str(aviso.severidad),
            "titulo": aviso.titulo,
            "cuerpo": aviso.cuerpo,
            "inicio_en": aviso.inicio_en,
            "fin_en": aviso.fin_en,
            "orden": aviso.orden,
            "activo": aviso.activo,
            "requiere_ack": aviso.requiere_ack,
            "created_at": str(aviso.created_at) if aviso.created_at else None,
            "updated_at": str(aviso.updated_at) if aviso.updated_at else None,
            "total_ack": total_ack,
            "total_usuarios_alcance": total_usuarios,
            "porcentaje_ack": porcentaje,
        }

    # ── CRUD ─────────────────────────────────────────────────────────────

    async def crear_aviso(self, datos: AvisoCreate) -> dict:
        """Crea un nuevo aviso institucional.

        Args:
            datos: Datos del aviso.

        Returns:
            AvisoResponse dict.

        Raises:
            BusinessError: Si los datos de alcance no son coherentes.
        """
        # Validar coherencia de alcance
        self._validar_alcance(datos)

        aviso = Aviso(
            tenant_id=self.tenant_id,
            alcance=datos.alcance,
            materia_id=datos.materia_id,
            cohorte_id=datos.cohorte_id,
            rol_destino=datos.rol_destino,
            severidad=datos.severidad,
            titulo=datos.titulo,
            cuerpo=datos.cuerpo,
            inicio_en=datos.inicio_en,
            fin_en=datos.fin_en,
            orden=datos.orden,
            activo=True,
            requiere_ack=datos.requiere_ack,
        )
        await self.aviso_repo.save(aviso)

        audit = self._build_audit_service()
        await audit.register(
            accion=ACCION_AVISO_CREAR,
            actor_id=self.actor_id,
            tenant_id=self.tenant_id,
            detalle={
                "aviso_id": str(aviso.id),
                "titulo": datos.titulo,
                "alcance": datos.alcance,
                "severidad": datos.severidad,
            },
            filas_afectadas=1,
        )

        return await self._to_aviso_response(aviso)

    async def editar_aviso(self, aviso_id: UUID, datos: AvisoUpdate) -> dict:
        """Edita un aviso existente.

        No permite editar si ya tuvo acknowledgments (para preservar
        la integridad del tracking).

        Args:
            aviso_id: UUID del aviso.
            datos: Datos a actualizar.

        Returns:
            AvisoResponse dict.

        Raises:
            BusinessError: Si el aviso no existe o ya tiene acknowledgments.
        """
        aviso = await self.aviso_repo.get_by_id(aviso_id)
        if aviso is None:
            raise BusinessError("Aviso no encontrado")

        # Verificar si ya tiene acknowledgments
        if await self.aviso_repo.tiene_acknowledgments(aviso_id):
            raise BusinessError(
                "No se puede editar un aviso que ya tiene acknowledgments"
            )

        update_data = datos.model_dump(exclude_none=True)
        if not update_data:
            return await self._to_aviso_response(aviso)

        aviso_actualizado = await self.aviso_repo.actualizar(
            aviso_id, update_data
        )
        if aviso_actualizado is None:
            raise BusinessError("Aviso no encontrado")

        audit = self._build_audit_service()
        await audit.register(
            accion=ACCION_AVISO_MODIFICAR,
            actor_id=self.actor_id,
            tenant_id=self.tenant_id,
            detalle={
                "aviso_id": str(aviso_id),
                "campos": list(update_data.keys()),
            },
            filas_afectadas=1,
        )

        return await self._to_aviso_response(aviso_actualizado)

    async def eliminar_aviso(self, aviso_id: UUID) -> dict:
        """Elimina un aviso: hard delete si no tiene acuses, soft delete si ya tuvo.

        Args:
            aviso_id: UUID del aviso.

        Returns:
            Dict con resultado de la operacion.

        Raises:
            BusinessError: Si el aviso no existe.
        """
        aviso = await self.aviso_repo.get_by_id(aviso_id)
        if aviso is None:
            raise BusinessError("Aviso no encontrado")

        tiene_acks = await self.aviso_repo.tiene_acknowledgments(aviso_id)

        if tiene_acks:
            # Soft delete
            await self.aviso_repo.soft_delete(aviso)
            metodo = "soft_delete"
        else:
            # Hard delete
            await self.aviso_repo.hard_delete(aviso_id)
            metodo = "hard_delete"

        audit = self._build_audit_service()
        await audit.register(
            accion=ACCION_AVISO_ELIMINAR,
            actor_id=self.actor_id,
            tenant_id=self.tenant_id,
            detalle={
                "aviso_id": str(aviso_id),
                "metodo": metodo,
                "titulo": aviso.titulo,
            },
            filas_afectadas=1,
        )

        return {"eliminado": True, "metodo": metodo, "aviso_id": str(aviso_id)}

    async def obtener_aviso(self, aviso_id: UUID) -> dict:
        """Obtiene detalle de un aviso con metricas.

        Args:
            aviso_id: UUID del aviso.

        Returns:
            AvisoResponse dict.

        Raises:
            BusinessError: Si el aviso no existe.
        """
        aviso = await self.aviso_repo.get_by_id(aviso_id)
        if aviso is None:
            raise BusinessError("Aviso no encontrado")

        return await self._to_aviso_response(aviso)

    async def listar_avisos(
        self,
        materia_id: UUID | None = None,
        cohorte_id: UUID | None = None,
        alcance: str | None = None,
        severidad: str | None = None,
        activo: bool | None = None,
    ) -> dict:
        """Lista avisos con filtros.

        Returns:
            Dict con items y total.
        """
        avisos = await self.aviso_repo.listar(
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            alcance=alcance,
            severidad=severidad,
            activo=activo,
        )
        items = []
        for av in avisos:
            items.append(await self._to_aviso_response(av))
        return {"items": items, "total": len(items)}

    # ── Timeline ─────────────────────────────────────────────────────────

    async def obtener_timeline(
        self,
        usuario_id: UUID,
        materia_ids: list[UUID] | None = None,
        cohorte_ids: list[UUID] | None = None,
    ) -> dict:
        """Obtiene la timeline de avisos activos para un usuario.

        Args:
            usuario_id: UUID del usuario.
            materia_ids: IDs de materias del usuario.
            cohorte_ids: IDs de cohortes del usuario.

        Returns:
            AvisoTimelineResponse dict.
        """
        avisos = await self.aviso_repo.listar_timeline(
            usuario_id=usuario_id,
            materia_ids=materia_ids,
            cohorte_ids=cohorte_ids,
            roles=self.roles,
        )

        items = []
        for av in avisos:
            # Verificar si el usuario ya hizo acknowledge
            acknowledged = False
            if av.requiere_ack:
                ack = await self.ack_repo.buscar(av.id, usuario_id)
                acknowledged = ack is not None

            items.append(
                AvisoTimelineItem(
                    id=av.id,
                    alcance=av.alcance.value if hasattr(av.alcance, "value") else str(av.alcance),
                    severidad=av.severidad.value if hasattr(av.severidad, "value") else str(av.severidad),
                    titulo=av.titulo,
                    cuerpo=av.cuerpo,
                    inicio_en=av.inicio_en,
                    fin_en=av.fin_en,
                    orden=av.orden,
                    requiere_ack=av.requiere_ack,
                    acknowledged=acknowledged,
                    created_at=str(av.created_at) if av.created_at else None,
                ).model_dump()
            )

        return AvisoTimelineResponse(items=items, total=len(items)).model_dump()

    # ── Acknowledgment ───────────────────────────────────────────────────

    async def acknowledge(self, aviso_id: UUID) -> dict:
        """Registra el acknowledgment de un usuario para un aviso.

        Args:
            aviso_id: UUID del aviso.

        Returns:
            dict con el resultado.

        Raises:
            BusinessError: Si el aviso no existe, no requiere ack,
                o el usuario ya hizo acknowledge.
        """
        aviso = await self.aviso_repo.get_by_id(aviso_id)
        if aviso is None:
            raise BusinessError("Aviso no encontrado")

        if not aviso.requiere_ack:
            raise BusinessError("Este aviso no requiere acknowledgment")

        # Verificar si ya existe (duplicado)
        existente = await self.ack_repo.buscar(aviso_id, self.actor_id)
        if existente is not None:
            raise BusinessError("Ya has confirmado la lectura de este aviso")

        ack = await self.ack_repo.crear(aviso_id, self.actor_id)
        if ack is None:
            raise BusinessError("Ya has confirmado la lectura de este aviso")

        audit = self._build_audit_service()
        await audit.register(
            accion=ACCION_AVISO_ACK,
            actor_id=self.actor_id,
            tenant_id=self.tenant_id,
            detalle={
                "aviso_id": str(aviso_id),
                "ack_id": str(ack.id),
            },
            filas_afectadas=1,
        )

        return {
            "id": ack.id,
            "aviso_id": ack.aviso_id,
            "usuario_id": ack.usuario_id,
            "confirmado_at": str(ack.confirmado_at),
        }

    # ── Tracking ─────────────────────────────────────────────────────────

    async def obtener_tracking(self, aviso_id: UUID) -> dict:
        """Obtiene tracking de acknowledgments de un aviso.

        Args:
            aviso_id: UUID del aviso.

        Returns:
            TrackingAvisoResponse dict.

        Raises:
            BusinessError: Si el aviso no existe.
        """
        aviso = await self.aviso_repo.get_by_id(aviso_id)
        if aviso is None:
            raise BusinessError("Aviso no encontrado")

        # Obtener todos los acknowledgments
        acks = await self.ack_repo.listar_por_aviso(aviso_id)

        # Calcular universo
        total_usuarios = await self.aviso_repo.contar_usuarios_en_alcance(aviso)
        total_ack = len(acks)

        porcentaje = 0.0
        if total_usuarios > 0:
            porcentaje = round((total_ack / total_usuarios) * 100, 1)

        # Poblar nombres de usuario
        ack_items = []
        for ack in acks:
            nombre = None
            try:
                from app.models.usuario import Usuario  # noqa: PLC0415

                result = await self.session.execute(
                    select(Usuario.nombre, Usuario.apellidos).where(
                        Usuario.id == ack.usuario_id
                    )
                )
                row = result.one_or_none()
                if row:
                    nombre = f"{row.nombre} {row.apellidos}".strip()
            except Exception:  # noqa: BLE001
                pass

            ack_items.append(
                TrackingAckItem(
                    usuario_id=ack.usuario_id,
                    usuario_nombre=nombre or str(ack.usuario_id),
                    confirmado_at=ack.confirmado_at,
                )
            )

        return TrackingAvisoResponse(
            total_usuarios=total_usuarios,
            total_ack=total_ack,
            porcentaje=porcentaje,
            acknowledgments=ack_items,
        ).model_dump()

    # ── Validacion ───────────────────────────────────────────────────────

    @staticmethod
    def _validar_alcance(datos: AvisoCreate) -> None:
        """Valida coherencia del alcance con los campos de contexto.

        Args:
            datos: Datos del aviso.

        Raises:
            BusinessError: Si el alcance requiere contexto y no se provee.
        """
        if datos.alcance == "PorMateria" and not datos.materia_id:
            raise BusinessError(
                "El alcance PorMateria requiere materia_id"
            )
        if datos.alcance == "PorCohorte" and not datos.cohorte_id:
            raise BusinessError(
                "El alcance PorCohorte requiere cohorte_id"
            )
        if datos.alcance == "PorRol" and not datos.rol_destino:
            raise BusinessError(
                "El alcance PorRol requiere rol_destino"
            )
        if datos.inicio_en >= datos.fin_en:
            raise BusinessError(
                "La fecha de inicio debe ser anterior a la fecha de fin"
            )
