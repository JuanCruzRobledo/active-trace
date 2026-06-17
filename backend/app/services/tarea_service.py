"""TareaService — logica de negocio para tareas internas (C-16).

Gestiona el ciclo completo: creacion de tareas, cambios de estado con
transiciones validas, comentarios asincronicos, timeline personal y
vista de administracion con filtros. Toda accion significativa genera
un evento de auditoria.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError
from app.models.enums import EstadoTarea
from app.models.tarea import ComentarioTarea, Tarea
from app.repositories.tarea_repository import ComentarioRepository, TareaRepository
from app.schemas.tareas import (
    ComentarioCreate,
    ComentarioResponse,
    TareaConComentariosResponse,
    TareaCreate,
    TareaListResponse,
    TareaResponse,
)
from app.services.audit_service import AuditService
from app.services.audit_service import (
    ACCION_TAREA_COMENTARIO,
    ACCION_TAREA_CREAR,
    ACCION_TAREA_ESTADO_CAMBIAR,
)

# ── State machine ──────────────────────────────────────────────────────────

VALID_TRANSITIONS: dict[EstadoTarea, list[EstadoTarea]] = {
    EstadoTarea.PENDIENTE: [EstadoTarea.EN_PROGRESO, EstadoTarea.CANCELADA],
    EstadoTarea.EN_PROGRESO: [EstadoTarea.RESUELTA, EstadoTarea.CANCELADA],
    EstadoTarea.RESUELTA: [],
    EstadoTarea.CANCELADA: [],
}

PERMISO_GESTIONAR = "tareas:gestionar"


class TareaService:
    """Servicio de tareas internas: CRUD, cambio de estado, comentarios."""

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
        self.tarea_repo = TareaRepository(session, tenant_id)
        self.comentario_repo = ComentarioRepository(session, tenant_id)

    # ── Helpers ──────────────────────────────────────────────────────────

    def _tiene_permiso_gestionar(self) -> bool:
        """Verifica si el actor tiene permiso de gestion.

        El JWT contiene codigos de rol (``ADMIN``, ``PROFESOR``, ...),
        no permisos directos. Ademas del check del permiso especifico,
        los roles ADMIN y COORDINADOR tienen gestion implicita.

        Returns:
            True si el actor tiene ``tareas:gestionar``.
        """
        return (
            PERMISO_GESTIONAR in self.roles
            or any(r in ("ADMIN", "COORDINADOR") for r in self.roles)
        )

    def _puede_acceder_tarea(self, tarea: Tarea) -> bool:
        """Verifica si el actor puede acceder a una tarea.

        El acceso se concede si:
        - El actor es el asignado de la tarea, o
        - El actor tiene permiso ``tareas:gestionar``.

        Args:
            tarea: Instancia de Tarea.

        Returns:
            True si el actor tiene acceso.
        """
        return (
            tarea.asignado_a == self.actor_id
            or self._tiene_permiso_gestionar()
        )

    def _build_audit_service(self) -> AuditService:
        from app.core.config import Settings  # noqa: PLC0415
        from app.repositories.audit_log_repository import AuditLogRepository  # noqa: PLC0415

        audit_repo = AuditLogRepository(self.session, self.tenant_id)
        return AuditService(audit_log_repo=audit_repo, settings=Settings())

    @staticmethod
    def _validar_transicion(estado_actual: str, nuevo_estado: str) -> None:
        """Valida que la transicion de estado sea permitida.

        Args:
            estado_actual: Estado actual de la tarea.
            nuevo_estado: Estado al que se quiere transicionar.

        Raises:
            BusinessError: Si la transicion no es valida.
        """
        try:
            actual = EstadoTarea(estado_actual)
            nuevo = EstadoTarea(nuevo_estado)
        except ValueError as exc:
            raise BusinessError(f"Estado invalido: {exc}") from exc

        permitidos = VALID_TRANSITIONS.get(actual, [])
        if nuevo not in permitidos:
            raise BusinessError(
                f"Transicion invalida: {estado_actual} → {nuevo_estado}"
            )

    async def _validar_materia_en_tenant(self, materia_id: UUID) -> None:
        """Verifica que una materia exista y pertenezca al tenant.

        Args:
            materia_id: UUID de la materia a verificar.

        Raises:
            BusinessError: Si la materia no existe en el tenant.
        """
        from app.models.materia import Materia  # noqa: PLC0415

        stmt = select(Materia).where(
            Materia.id == materia_id,
            Materia.tenant_id == self.tenant_id,
            Materia.deleted_at.is_(None),
        )
        result = await self.session.scalar(stmt)
        if result is None:
            raise BusinessError("Materia no encontrada en el tenant")

    async def _validar_usuario_en_tenant(self, usuario_id: UUID) -> None:
        """Verifica que un usuario exista y este activo en el tenant.

        Args:
            usuario_id: UUID del usuario a verificar.

        Raises:
            BusinessError: Si el usuario no existe en el tenant.
        """
        from app.models.usuario import Usuario  # noqa: PLC0415

        stmt = select(Usuario).where(
            Usuario.id == usuario_id,
            Usuario.tenant_id == self.tenant_id,
            Usuario.deleted_at.is_(None),
        )
        result = await self.session.scalar(stmt)
        if result is None:
            raise BusinessError("Usuario asignado no encontrado en el tenant")

    async def _to_tarea_response(self, tarea: Tarea) -> dict:
        """Convierte una Tarea a dict de respuesta.

        Resuelve nombres de usuarios desde las relaciones ``asignado``
        y ``asignador`` del modelo Tarea.

        Args:
            tarea: Instancia de Tarea.

        Returns:
            Dict con datos de la tarea.
        """
        asignado_nombre = None
        asignador_nombre = None
        if tarea.asignado:
            asignado_nombre = (
                f"{tarea.asignado.nombre} {tarea.asignado.apellidos}".strip()
            )
        if tarea.asignador:
            asignador_nombre = (
                f"{tarea.asignador.nombre} {tarea.asignador.apellidos}".strip()
            )

        return {
            "id": tarea.id,
            "tenant_id": tarea.tenant_id,
            "materia_id": tarea.materia_id,
            "asignado_a": tarea.asignado_a,
            "asignado_a_nombre": asignado_nombre,
            "asignado_por": tarea.asignado_por,
            "asignado_por_nombre": asignador_nombre,
            "estado": tarea.estado.value if hasattr(tarea.estado, "value") else str(tarea.estado),
            "descripcion": tarea.descripcion,
            "contexto_id": tarea.contexto_id,
            "created_at": tarea.created_at,
            "updated_at": tarea.updated_at,
        }

    async def _to_comentario_response(self, comentario: ComentarioTarea) -> dict:
        """Convierte un ComentarioTarea a dict de respuesta.

        Args:
            comentario: Instancia de ComentarioTarea.

        Returns:
            Dict con datos del comentario.
        """
        return {
            "id": comentario.id,
            "tarea_id": comentario.tarea_id,
            "autor_id": comentario.autor_id,
            "texto": comentario.texto,
            "creado_at": comentario.creado_at,
        }

    # ── Crear tarea ───────────────────────────────────────────────────────

    async def crear_tarea(self, datos: TareaCreate) -> dict:
        """Crea una nueva tarea interna.

        Args:
            datos: Datos de la tarea a crear.

        Returns:
            TareaResponse dict.

        Raises:
            BusinessError: Si el usuario asignado no existe en el tenant,
                o si la materia no pertenece al tenant.
        """
        if datos.materia_id is not None:
            await self._validar_materia_en_tenant(datos.materia_id)
        await self._validar_usuario_en_tenant(datos.asignado_a)

        tarea = Tarea(
            tenant_id=self.tenant_id,
            materia_id=datos.materia_id,
            asignado_a=datos.asignado_a,
            asignado_por=self.actor_id,
            estado=EstadoTarea.PENDIENTE,
            descripcion=datos.descripcion,
            contexto_id=datos.contexto_id,
        )
        await self.tarea_repo.create(tarea)

        audit = self._build_audit_service()
        await audit.register(
            accion=ACCION_TAREA_CREAR,
            actor_id=self.actor_id,
            tenant_id=self.tenant_id,
            detalle={
                "tarea_id": str(tarea.id),
                "asignado_a": str(datos.asignado_a),
                "descripcion": datos.descripcion[:100],
            },
            filas_afectadas=1,
        )

        return await self._to_tarea_response(tarea)

    # ── Cambiar estado ────────────────────────────────────────────────────

    async def cambiar_estado(self, tarea_id: UUID, nuevo_estado: str) -> dict:
        """Cambia el estado de una tarea validando la transicion.

        Args:
            tarea_id: UUID de la tarea.
            nuevo_estado: Nuevo estado (valor del enum).

        Returns:
            TareaResponse dict.

        Raises:
            BusinessError: Si la tarea no existe, la transicion es invalida,
                o el actor no tiene acceso.
        """
        tarea = await self.tarea_repo.get_by_id(tarea_id)
        if tarea is None:
            raise BusinessError("Tarea no encontrada")

        if not self._puede_acceder_tarea(tarea):
            raise BusinessError("No tienes permiso para cambiar el estado de esta tarea")

        estado_actual = tarea.estado.value if hasattr(tarea.estado, "value") else str(tarea.estado)
        self._validar_transicion(estado_actual, nuevo_estado)

        estado_actual_enum = EstadoTarea(estado_actual)
        tarea_actualizada = await self.tarea_repo.update_estado(
            tarea_id, EstadoTarea(nuevo_estado), estado_esperado=estado_actual_enum,
        )
        if tarea_actualizada is None:
            raise BusinessError("Tarea no encontrada")

        audit = self._build_audit_service()
        await audit.register(
            accion=ACCION_TAREA_ESTADO_CAMBIAR,
            actor_id=self.actor_id,
            tenant_id=self.tenant_id,
            detalle={
                "tarea_id": str(tarea_id),
                "estado_anterior": estado_actual,
                "estado_nuevo": nuevo_estado,
            },
            filas_afectadas=1,
        )

        return await self._to_tarea_response(tarea_actualizada)

    # ── Comentarios ───────────────────────────────────────────────────────

    async def agregar_comentario(self, tarea_id: UUID, datos: ComentarioCreate) -> dict:
        """Agrega un comentario a una tarea.

        Args:
            tarea_id: UUID de la tarea.
            datos: Datos del comentario.

        Returns:
            ComentarioResponse dict.

        Raises:
            BusinessError: Si la tarea no existe o el actor no tiene acceso.
        """
        tarea = await self.tarea_repo.get_by_id(tarea_id)
        if tarea is None:
            raise BusinessError("Tarea no encontrada")

        if not self._puede_acceder_tarea(tarea):
            raise BusinessError("No tienes permiso para comentar en esta tarea")

        comentario = ComentarioTarea(
            tenant_id=self.tenant_id,
            tarea_id=tarea_id,
            autor_id=self.actor_id,
            texto=datos.texto,
        )
        await self.comentario_repo.create(comentario)

        audit = self._build_audit_service()
        await audit.register(
            accion=ACCION_TAREA_COMENTARIO,
            actor_id=self.actor_id,
            tenant_id=self.tenant_id,
            detalle={
                "tarea_id": str(tarea_id),
                "comentario_id": str(comentario.id),
            },
            filas_afectadas=1,
        )

        return await self._to_comentario_response(comentario)

    # ── Obtener tarea ─────────────────────────────────────────────────────

    async def obtener_tarea(self, tarea_id: UUID) -> dict:
        """Obtiene el detalle de una tarea con sus comentarios.

        Args:
            tarea_id: UUID de la tarea.

        Returns:
            TareaConComentariosResponse dict.

        Raises:
            BusinessError: Si la tarea no existe o el actor no tiene acceso.
        """
        tarea = await self.tarea_repo.get_by_id(tarea_id)
        if tarea is None:
            raise BusinessError("Tarea no encontrada")

        if not self._puede_acceder_tarea(tarea):
            raise BusinessError("No tienes permiso para ver esta tarea")

        comentarios = await self.comentario_repo.list_by_tarea(tarea_id)
        comentarios_response = [await self._to_comentario_response(c) for c in comentarios]

        tarea_dict = await self._to_tarea_response(tarea)
        tarea_dict["comentarios"] = comentarios_response
        return tarea_dict

    # ── Listar mis tareas ────────────────────────────────────────────────

    async def listar_mias(
        self,
        estado: str | None = None,
        materia_id: UUID | None = None,
    ) -> dict:
        """Lista las tareas asignadas al usuario autenticado.

        Args:
            estado: Filtrar por estado (opcional).
            materia_id: Filtrar por materia (opcional).

        Returns:
            TareaListResponse dict.
        """
        tareas = await self.tarea_repo.list_by_asignado(
            asignado_a=self.actor_id,
            estado=estado,
            materia_id=materia_id,
        )
        items = [await self._to_tarea_response(t) for t in tareas]
        return {"items": items, "total": len(items)}

    # ── Listar todas (admin) ──────────────────────────────────────────────

    async def listar_todas(
        self,
        estado: str | None = None,
        materia_id: UUID | None = None,
        asignado_a: UUID | None = None,
        asignado_por: UUID | None = None,
        busqueda: str | None = None,
    ) -> dict:
        """Lista todas las tareas del tenant con filtros combinables.

        Requiere permiso ``tareas:gestionar`` (verificado en el router).

        Args:
            estado: Filtrar por estado.
            materia_id: Filtrar por materia.
            asignado_a: Filtrar por usuario asignado.
            asignado_por: Filtrar por usuario asignador.
            busqueda: Busqueda textual en descripcion.

        Returns:
            TareaListResponse dict.
        """
        tareas = await self.tarea_repo.list_by_tenant(
            estado=estado,
            materia_id=materia_id,
            asignado_a=asignado_a,
            asignado_por=asignado_por,
            busqueda=busqueda,
        )
        items = [await self._to_tarea_response(t) for t in tareas]
        return {"items": items, "total": len(items)}
