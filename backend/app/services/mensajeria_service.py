"""MensajeriaService — mensajeria interna entre usuarios registrados (C-20).

Modela hilos de dos participantes (usuario_a / usuario_b) con mensajes append-only.
Toda la participacion se verifica antes de leer o responder: no-participante → 404.
Toda creacion de hilo y respuesta genera audit MENSAJE_ENVIAR.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError
from app.models.mensaje import Mensaje, MensajeHilo
from app.repositories.mensaje_repository import MensajeHiloRepository, MensajeRepository
from app.schemas.mensajeria import (
    HiloCreate,
    HiloConMensajesResponse,
    HiloListResponse,
    HiloResponse,
    MensajeCreate,
    MensajeResponse,
)
from app.services.audit_service import ACCION_MENSAJE_ENVIAR, AuditService


class MensajeriaService:
    """Servicio de mensajeria interna: hilos, respuestas, inbox, lectura."""

    def __init__(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        actor_id: UUID,
    ) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.actor_id = actor_id
        self.hilo_repo = MensajeHiloRepository(session, tenant_id)
        self.msg_repo = MensajeRepository(session, tenant_id)

    def _build_audit(self) -> AuditService:
        from app.core.config import Settings  # noqa: PLC0415
        from app.repositories.audit_log_repository import AuditLogRepository  # noqa: PLC0415

        return AuditService(
            audit_log_repo=AuditLogRepository(self.session, self.tenant_id),
            settings=Settings(),
        )

    def _es_participante(self, hilo: MensajeHilo) -> bool:
        return hilo.usuario_a_id == self.actor_id or hilo.usuario_b_id == self.actor_id

    def _no_leidos(self, hilo: MensajeHilo) -> bool:
        """Indica si el hilo tiene mensajes no leidos para el actor."""
        return any(
            m.leido_at is None and m.autor_id != self.actor_id
            for m in (hilo.mensajes or [])
        )

    async def crear_hilo(self, body: HiloCreate) -> HiloConMensajesResponse:
        """Crea un nuevo hilo con su primer mensaje.

        Args:
            body: destinatario_id, asunto, cuerpo del primer mensaje.

        Returns:
            Hilo creado con el primer mensaje.

        Raises:
            BusinessError: Si el destinatario no existe en el tenant.
        """
        from sqlalchemy import select  # noqa: PLC0415
        from app.models.usuario import Usuario  # noqa: PLC0415

        # Validar que el destinatario existe en el tenant
        result = await self.session.execute(
            select(Usuario).where(
                Usuario.id == body.destinatario_id,
                Usuario.tenant_id == self.tenant_id,
                Usuario.deleted_at.is_(None),
            )
        )
        if result.scalar_one_or_none() is None:
            raise BusinessError("Destinatario no encontrado en el tenant")

        hilo = MensajeHilo(
            tenant_id=self.tenant_id,
            asunto=body.asunto,
            usuario_a_id=self.actor_id,
            usuario_b_id=body.destinatario_id,
        )
        hilo = await self.hilo_repo.create(hilo)

        msg = Mensaje(
            tenant_id=self.tenant_id,
            hilo_id=hilo.id,
            autor_id=self.actor_id,
            cuerpo=body.cuerpo,
        )
        msg = await self.msg_repo.create(msg)

        audit = self._build_audit()
        await audit.register(
            accion=ACCION_MENSAJE_ENVIAR,
            actor_id=self.actor_id,
            tenant_id=self.tenant_id,
            detalle={"hilo_id": str(hilo.id), "mensaje_id": str(msg.id)},
        )

        mensajes = await self.msg_repo.list_by_hilo(hilo.id)
        return HiloConMensajesResponse(
            id=hilo.id,
            tenant_id=hilo.tenant_id,
            asunto=hilo.asunto,
            usuario_a_id=hilo.usuario_a_id,
            usuario_b_id=hilo.usuario_b_id,
            mensajes=[MensajeResponse.model_validate(m) for m in mensajes],
            created_at=hilo.created_at,
        )

    async def responder(self, hilo_id: UUID, body: MensajeCreate) -> MensajeResponse:
        """Agrega un mensaje a un hilo existente.

        Args:
            hilo_id: UUID del hilo.
            body: cuerpo del mensaje.

        Returns:
            Mensaje creado.

        Raises:
            BusinessError: Si el hilo no existe o el actor no es participante.
        """
        hilo = await self.hilo_repo.get_by_id(hilo_id)
        if hilo is None or not self._es_participante(hilo):
            raise BusinessError("Hilo no encontrado o sin participación")

        msg = Mensaje(
            tenant_id=self.tenant_id,
            hilo_id=hilo_id,
            autor_id=self.actor_id,
            cuerpo=body.cuerpo,
        )
        msg = await self.msg_repo.create(msg)

        audit = self._build_audit()
        await audit.register(
            accion=ACCION_MENSAJE_ENVIAR,
            actor_id=self.actor_id,
            tenant_id=self.tenant_id,
            detalle={"hilo_id": str(hilo_id), "mensaje_id": str(msg.id)},
        )

        return MensajeResponse.model_validate(msg)

    async def obtener_hilo(self, hilo_id: UUID) -> HiloConMensajesResponse:
        """Retorna un hilo completo con todos sus mensajes.

        Args:
            hilo_id: UUID del hilo.

        Returns:
            Hilo con mensajes en orden cronologico.

        Raises:
            BusinessError: Si el hilo no existe o el actor no es participante.
        """
        hilo = await self.hilo_repo.get_by_id(hilo_id)
        if hilo is None or not self._es_participante(hilo):
            raise BusinessError("Hilo no encontrado o sin participación")

        mensajes = await self.msg_repo.list_by_hilo(hilo_id)
        return HiloConMensajesResponse(
            id=hilo.id,
            tenant_id=hilo.tenant_id,
            asunto=hilo.asunto,
            usuario_a_id=hilo.usuario_a_id,
            usuario_b_id=hilo.usuario_b_id,
            mensajes=[MensajeResponse.model_validate(m) for m in mensajes],
            created_at=hilo.created_at,
        )

    async def listar_inbox(self) -> HiloListResponse:
        """Lista todos los hilos del actor (inbox).

        Returns:
            Paginacion de hilos propios ordenados por ultimo mensaje.
        """
        hilos = await self.hilo_repo.list_by_participante(self.actor_id)
        items = [
            HiloResponse(
                id=h.id,
                tenant_id=h.tenant_id,
                asunto=h.asunto,
                usuario_a_id=h.usuario_a_id,
                usuario_b_id=h.usuario_b_id,
                tiene_no_leidos=self._no_leidos(h),
                created_at=h.created_at,
            )
            for h in hilos
        ]
        return HiloListResponse(items=items, total=len(items))
