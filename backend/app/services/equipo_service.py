"""EquipoService — logica de negocio para Equipos Docentes (C-08).

Gestiona operaciones sobre equipos docentes: consulta, asignacion masiva,
clonacion, modificacion de vigencia y exportacion.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.exceptions import BusinessError
from app.models.asignacion import Asignacion
from app.models.carrera import Carrera
from app.models.cohorte import Cohorte
from app.models.materia import Materia
from app.models.usuario import Usuario
from app.repositories.asignacion_repository import AsignacionRepository
from app.repositories.base import BaseRepository
from app.schemas.equipo import (
    AsignacionMasivaRequest,
    ClonarEquipoRequest,
    ClonarResponse,
    VigenciaRequest,
    VigenciaResponse,
)
from app.schemas.asignacion import AsignacionResponse
from app.services.audit_service import (
    ACCION_ASIGNACION_MODIFICAR,
    AuditService,
)


class EquipoService:
    """Service for tenant-scoped Equipo Docente operations."""

    def __init__(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        actor_id: UUID,
    ) -> None:
        self.repo = AsignacionRepository(session, Asignacion, tenant_id)
        self.usuario_repo = BaseRepository(session, Usuario, tenant_id)
        self.materia_repo = BaseRepository(session, Materia, tenant_id)
        self.carrera_repo = BaseRepository(session, Carrera, tenant_id)
        self.cohorte_repo = BaseRepository(session, Cohorte, tenant_id)
        self.tenant_id = tenant_id
        self.session = session
        self.actor_id = actor_id

    # ── Helpers ────────────────────────────────────────────────────────

    def _calcular_estado_vigencia(self, desde: datetime, hasta: datetime | None) -> str:
        """Calcula el estado de vigencia de una asignacion.

        Returns:
            ``"Vigente"`` si esta activa, ``"Vencida"`` si ya paso,
            ``"Sin iniciar"`` si aun no empezo.
        """
        now = datetime.now(timezone.utc)
        if hasta is not None and hasta < now:
            return "Vencida"
        if desde > now:
            return "Sin iniciar"
        return "Vigente"

    def _build_audit_service(self) -> AuditService:
        from app.repositories.audit_log_repository import AuditLogRepository
        from app.core.config import Settings

        audit_repo = AuditLogRepository(self.session, self.tenant_id)
        settings = Settings()
        return AuditService(audit_log_repo=audit_repo, settings=settings)

    # ── Helpers — resolucion de nombres ────────────────────────────────

    async def _resolve_nombres_contexto(
        self,
        asignaciones: list[Asignacion],
    ) -> tuple[dict[UUID, str], dict[UUID, str], dict[UUID, str]]:
        """Resuelve nombres de materia, carrera y cohorte para asignaciones.

        Colecta IDs unicos y los resuelve con una unica query por tipo.

        Returns:
            Tupla (materias, carreras, cohortes) — dicts UUID → nombre.
        """
        materia_ids = {a.materia_id for a in asignaciones if a.materia_id}
        carrera_ids = {a.carrera_id for a in asignaciones if a.carrera_id}
        cohorte_ids = {a.cohorte_id for a in asignaciones if a.cohorte_id}

        materias: dict[UUID, str] = {}
        for mid in materia_ids:
            m = await self.materia_repo.get_by_id(mid)
            if m:
                materias[mid] = m.nombre

        carreras: dict[UUID, str] = {}
        for cid in carrera_ids:
            c = await self.carrera_repo.get_by_id(cid)
            if c:
                carreras[cid] = c.nombre

        cohortes: dict[UUID, str] = {}
        for cid in cohorte_ids:
            c = await self.cohorte_repo.get_by_id(cid)
            if c:
                cohortes[cid] = c.nombre

        return materias, carreras, cohortes

    # ── Mis equipos ────────────────────────────────────────────────────

    async def mis_equipos(
        self,
        usuario_id: UUID,
        filtros: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Retorna las asignaciones del usuario con nombres de contexto.

        Args:
            usuario_id: UUID del usuario.
            filtros: Filtros adicionales (materia_id, carrera_id, etc.).

        Returns:
            Lista de dicts con datos de asignacion + nombres.
        """
        asignaciones = await self.repo.list_by_usuario(usuario_id)
        materias, carreras, cohortes = await self._resolve_nombres_contexto(asignaciones)

        result = []
        for a in asignaciones:
            entry: dict[str, Any] = {
                "id": str(a.id),
                "tenant_id": str(a.tenant_id),
                "usuario_id": str(a.usuario_id),
                "rol": a.rol,
                "materia_id": str(a.materia_id) if a.materia_id else None,
                "carrera_id": str(a.carrera_id) if a.carrera_id else None,
                "cohorte_id": str(a.cohorte_id) if a.cohorte_id else None,
                "comisiones": a.comisiones,
                "responsable_id": str(a.responsable_id) if a.responsable_id else None,
                "desde": a.desde,
                "hasta": a.hasta,
                "estado_vigencia": self._calcular_estado_vigencia(a.desde, a.hasta),
                "materia_nombre": materias.get(a.materia_id) if a.materia_id else None,
                "carrera_nombre": carreras.get(a.carrera_id) if a.carrera_id else None,
                "cohorte_nombre": cohortes.get(a.cohorte_id) if a.cohorte_id else None,
                "created_at": a.created_at,
                "updated_at": a.updated_at,
            }
            result.append(entry)

        return result


    # ── Listar equipos (gestion) ───────────────────────────────────────

    async def listar_equipos(
        self,
        materia_id: UUID | None = None,
        carrera_id: UUID | None = None,
        cohorte_id: UUID | None = None,
        usuario_id: UUID | None = None,
        rol: str | None = None,
    ) -> list[dict[str, Any]]:
        """Lista todas las asignaciones del tenant con nombres de contexto.

        Args:
            materia_id: Filtrar por materia.
            carrera_id: Filtrar por carrera.
            cohorte_id: Filtrar por cohorte.
            usuario_id: Filtrar por usuario.
            rol: Filtrar por rol.

        Returns:
            Lista de dicts con datos de asignacion + nombres.
        """
        asignaciones = await self.repo.list_by_context(
            materia_id=materia_id,
            carrera_id=carrera_id,
            cohorte_id=cohorte_id,
            usuario_id=usuario_id,
            rol=rol,
        )
        materias, carreras, cohortes = await self._resolve_nombres_contexto(asignaciones)

        result = []
        for a in asignaciones:
            entry: dict[str, Any] = {
                "id": str(a.id),
                "tenant_id": str(a.tenant_id),
                "usuario_id": str(a.usuario_id),
                "rol": a.rol,
                "materia_id": str(a.materia_id) if a.materia_id else None,
                "carrera_id": str(a.carrera_id) if a.carrera_id else None,
                "cohorte_id": str(a.cohorte_id) if a.cohorte_id else None,
                "comisiones": a.comisiones,
                "responsable_id": str(a.responsable_id) if a.responsable_id else None,
                "desde": a.desde,
                "hasta": a.hasta,
                "estado_vigencia": self._calcular_estado_vigencia(a.desde, a.hasta),
                "materia_nombre": materias.get(a.materia_id) if a.materia_id else None,
                "carrera_nombre": carreras.get(a.carrera_id) if a.carrera_id else None,
                "cohorte_nombre": cohortes.get(a.cohorte_id) if a.cohorte_id else None,
                "created_at": a.created_at,
                "updated_at": a.updated_at,
            }
            result.append(entry)

        return result


    # ── Asignacion masiva ──────────────────────────────────────────────

    async def asignacion_masiva(
        self, data: AsignacionMasivaRequest
    ) -> list[Asignacion]:
        """Asigna N usuarios a un contexto academico en bloque.

        Args:
            data: Datos de la asignacion masiva.

        Returns:
            Lista de asignaciones creadas.

        Raises:
            BusinessError: Si algun usuario no existe.
        """
        materia_id = UUID(data.materia_id)
        carrera_id = UUID(data.carrera_id)
        cohorte_id = UUID(data.cohorte_id)
        responsable_id = UUID(data.responsable_id) if data.responsable_id else None

        for uid in data.usuario_ids:
            usuario = await self.usuario_repo.get_by_id(uid)
            if usuario is None:
                raise BusinessError(
                    f"No existe un usuario con id {uid} en el tenant"
                )

        asignaciones = []
        for uid in data.usuario_ids:
            a = Asignacion(
                tenant_id=self.tenant_id,
                usuario_id=uid,
                rol=data.rol,
                materia_id=materia_id,
                carrera_id=carrera_id,
                cohorte_id=cohorte_id,
                comisiones=data.comisiones,
                responsable_id=responsable_id,
                desde=data.desde,
                hasta=data.hasta,
            )
            asignaciones.append(a)

        creadas = await self.repo.bulk_create(asignaciones)

        audit = self._build_audit_service()
        await audit.register(
            accion=ACCION_ASIGNACION_MODIFICAR,
            actor_id=self.actor_id,
            tenant_id=self.tenant_id,
            detalle={
                "tipo": "asignacion_masiva",
                "usuario_ids": [str(uid) for uid in data.usuario_ids],
                "materia_id": data.materia_id,
                "carrera_id": data.carrera_id,
                "cohorte_id": data.cohorte_id,
                "rol": data.rol,
            },
            filas_afectadas=len(creadas),
            materia_id=materia_id,
        )

        return creadas

    # ── Clonar equipo ──────────────────────────────────────────────────

    async def clonar_equipo(
        self, data: ClonarEquipoRequest
    ) -> ClonarResponse:
        """Clona todas las asignaciones vigentes de origen a destino.

        Args:
            data: Datos de origen y destino.

        Returns:
            ClonarResponse con detalle de la operacion.

        Raises:
            BusinessError: Si el origen no tiene asignaciones.
        """
        origen_materia_id = UUID(data.origen_materia_id)
        origen_carrera_id = UUID(data.origen_carrera_id)
        origen_cohorte_id = UUID(data.origen_cohorte_id)
        destino_materia_id = UUID(data.destino_materia_id)
        destino_carrera_id = UUID(data.destino_carrera_id)
        destino_cohorte_id = UUID(data.destino_cohorte_id)

        origen = await self.repo.list_by_equipo(
            materia_id=origen_materia_id,
            carrera_id=origen_carrera_id,
            cohorte_id=origen_cohorte_id,
        )

        if not origen:
            raise BusinessError(
                "No hay asignaciones vigentes en el origen"
            )

        nuevas = []
        for a in origen:
            nuevas.append(Asignacion(
                tenant_id=self.tenant_id,
                usuario_id=a.usuario_id,
                rol=a.rol,
                materia_id=destino_materia_id,
                carrera_id=destino_carrera_id,
                cohorte_id=destino_cohorte_id,
                comisiones=a.comisiones,
                responsable_id=a.responsable_id,
                desde=data.destino_desde,
                hasta=data.destino_hasta,
            ))

        creadas = await self.repo.bulk_create(nuevas)

        audit = self._build_audit_service()
        await audit.register(
            accion=ACCION_ASIGNACION_MODIFICAR,
            actor_id=self.actor_id,
            tenant_id=self.tenant_id,
            detalle={
                "tipo": "clonar_equipo",
                "origen": {
                    "materia_id": data.origen_materia_id,
                    "carrera_id": data.origen_carrera_id,
                    "cohorte_id": data.origen_cohorte_id,
                },
                "destino": {
                    "materia_id": data.destino_materia_id,
                    "carrera_id": data.destino_carrera_id,
                    "cohorte_id": data.destino_cohorte_id,
                },
            },
            filas_afectadas=len(creadas),
            materia_id=destino_materia_id,
        )

        asignaciones_response = [
            AsignacionResponse(
                id=str(a.id),
                tenant_id=str(a.tenant_id),
                usuario_id=str(a.usuario_id),
                rol=a.rol,
                materia_id=str(a.materia_id) if a.materia_id else None,
                carrera_id=str(a.carrera_id) if a.carrera_id else None,
                cohorte_id=str(a.cohorte_id) if a.cohorte_id else None,
                comisiones=a.comisiones,
                responsable_id=str(a.responsable_id) if a.responsable_id else None,
                desde=a.desde,
                hasta=a.hasta,
                estado_vigencia=self._calcular_estado_vigencia(a.desde, a.hasta),
                created_at=a.created_at,
                updated_at=a.updated_at,
            )
            for a in creadas
        ]

        return ClonarResponse(
            creadas=len(creadas),
            origen=f"{data.origen_materia_id}/{data.origen_carrera_id}/{data.origen_cohorte_id}",
            destino=f"{data.destino_materia_id}/{data.destino_carrera_id}/{data.destino_cohorte_id}",
            asignaciones=asignaciones_response,
        )

    # ── Modificar vigencia ─────────────────────────────────────────────

    async def modificar_vigencia(
        self, data: VigenciaRequest
    ) -> VigenciaResponse:
        """Modifica la vigencia de todas las asignaciones de un equipo.

        Args:
            data: Datos con materia/carrera/cohorte y nuevas fechas.

        Returns:
            VigenciaResponse con cantidad de afectadas.
        """
        materia_id = UUID(data.materia_id)
        carrera_id = UUID(data.carrera_id)
        cohorte_id = UUID(data.cohorte_id)

        afectadas = await self.repo.update_vigencia_en_bloque(
            materia_id=materia_id,
            carrera_id=carrera_id,
            cohorte_id=cohorte_id,
            desde=data.desde,
            hasta=data.hasta,
        )

        if afectadas > 0:
            audit = self._build_audit_service()
            await audit.register(
                accion=ACCION_ASIGNACION_MODIFICAR,
                actor_id=self.actor_id,
                tenant_id=self.tenant_id,
                detalle={
                    "tipo": "modificar_vigencia",
                    "materia_id": data.materia_id,
                    "carrera_id": data.carrera_id,
                    "cohorte_id": data.cohorte_id,
                },
                filas_afectadas=afectadas,
                materia_id=materia_id,
            )

        return VigenciaResponse(
            afectadas=afectadas,
            desde=data.desde,
            hasta=data.hasta,
        )

    # ── Exportar equipo ────────────────────────────────────────────────

    async def exportar_equipo(
        self,
        materia_id: UUID,
        carrera_id: UUID,
        cohorte_id: UUID,
    ) -> list[dict[str, Any]]:
        """Retorna datos del equipo con nombres legibles para exportacion CSV.

        Resuelve nombres de usuarios, materias, carreras y cohortes
        para mostrar datos legibles en lugar de UUIDs.

        Args:
            materia_id: UUID de la materia.
            carrera_id: UUID de la carrera.
            cohorte_id: UUID de la cohorte.

        Returns:
            Lista de dicts con claves en espanol.
        """
        asignaciones = await self.repo.list_by_equipo(
            materia_id=materia_id,
            carrera_id=carrera_id,
            cohorte_id=cohorte_id,
        )

        # Resolver nombres de contexto
        materias, carreras, cohortes = await self._resolve_nombres_contexto(asignaciones)

        # Resolver nombres de usuarios y DNI
        usuario_ids = {a.usuario_id for a in asignaciones if a.usuario_id}
        usuarios: dict[UUID, Any] = {}
        for uid in usuario_ids:
            u = await self.usuario_repo.get_by_id(uid)
            if u:
                usuarios[uid] = u

        result = []
        for a in asignaciones:
            user = usuarios.get(a.usuario_id)
            nombre_docente = (
                f"{user.nombre} {user.apellidos}" if user else str(a.usuario_id)
            )
            documento = user.dni if user else ""
            materia_nom = materias.get(a.materia_id) if a.materia_id else ""
            carrera_nom = carreras.get(a.carrera_id) if a.carrera_id else ""
            cohorte_nom = cohortes.get(a.cohorte_id) if a.cohorte_id else ""

            entry: dict[str, Any] = {
                "docente": nombre_docente,
                "documento": documento,
                "rol": a.rol,
                "materia": materia_nom,
                "carrera": carrera_nom,
                "cohorte": cohorte_nom,
                "comisiones": ",".join(a.comisiones) if a.comisiones else "",
                "desde": a.desde.isoformat(),
                "hasta": a.hasta.isoformat() if a.hasta else "",
                "estado_vigencia": self._calcular_estado_vigencia(a.desde, a.hasta),
            }
            result.append(entry)

        return result
