"""EncuentroService — lógica de negocio para slots e instancias de encuentro (C-13).

Gestiona la creación de slots recurrentes/únicos con generación automática de
instancias, edición, eliminación (soft-delete), listado con scope según rol,
y exportación de HTML para aula virtual.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError
from app.models.enums import DiaSemana, EstadoEncuentro
from app.models.instancia_encuentro import InstanciaEncuentro
from app.models.slot_encuentro import SlotEncuentro
from app.repositories.instancia_encuentro_repository import (
    InstanciaEncuentroRepository,
)
from app.repositories.slot_encuentro_repository import SlotEncuentroRepository
from app.schemas.encuentros import (
    InstanciaEncuentroResponse,
    InstanciaEncuentroUpdate,
    SlotEncuentroCreate,
    SlotEncuentroCreateUnico,
    SlotEncuentroResponse,
    SlotEncuentroUpdate,
)
from app.services.audit_service import AuditService

# ── Audit action codes ─────────────────────────────────────────────────

ACCION_ENCUENTRO_CREAR = "ENCUENTRO_CREAR"
ACCION_ENCUENTRO_MODIFICAR = "ENCUENTRO_MODIFICAR"
ACCION_ENCUENTRO_ELIMINAR = "ENCUENTRO_ELIMINAR"


class EncuentroService:
    """Servicio de encuentros: gestión de slots e instancias con scope por rol."""

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
        self.slot_repo = SlotEncuentroRepository(session, tenant_id)
        self.instancia_repo = InstanciaEncuentroRepository(session, tenant_id)
        self._es_admin = any(r in ("COORDINADOR", "ADMIN") for r in roles)

    # ── Helpers ──────────────────────────────────────────────────────────

    def _build_audit_service(self) -> AuditService:
        from app.core.config import Settings
        from app.repositories.audit_log_repository import AuditLogRepository

        audit_repo = AuditLogRepository(self.session, self.tenant_id)
        return AuditService(audit_log_repo=audit_repo, settings=Settings())

    def _to_slot_response(
        self, slot: SlotEncuentro, cant_instancias: int = 0
    ) -> dict[str, Any]:
        return {
            "id": slot.id,
            "materia_id": slot.materia_id,
            "titulo": slot.titulo,
            "hora": slot.hora,
            "dia_semana": slot.dia_semana.value if hasattr(slot.dia_semana, "value") else str(slot.dia_semana),
            "fecha_inicio": slot.fecha_inicio,
            "cant_semanas": slot.cant_semanas,
            "fecha_unica": slot.fecha_unica,
            "meet_url": slot.meet_url,
            "vig_desde": slot.vig_desde,
            "vig_hasta": slot.vig_hasta,
            "created_at": str(slot.created_at) if slot.created_at else None,
            "updated_at": str(slot.updated_at) if slot.updated_at else None,
            "cantidad_instancias": cant_instancias,
        }

    def _to_instancia_response(
        self, instancia: InstanciaEncuentro
    ) -> dict[str, Any]:
        return {
            "id": instancia.id,
            "slot_id": instancia.slot_id,
            "materia_id": instancia.materia_id,
            "fecha": instancia.fecha,
            "hora": instancia.hora,
            "titulo": instancia.titulo,
            "estado": instancia.estado.value if hasattr(instancia.estado, "value") else str(instancia.estado),
            "meet_url": instancia.meet_url,
            "video_url": instancia.video_url,
            "comentario": instancia.comentario,
            "created_at": str(instancia.created_at) if instancia.created_at else None,
            "updated_at": str(instancia.updated_at) if instancia.updated_at else None,
            "slot_titulo": None,
        }

    # ── Validación de alcance ─────────────────────────────────────────────

    async def verificar_alcance(self, materia_id: UUID | None = None) -> bool:
        """Verifica si el usuario tiene alcance sobre una materia.

        COORDINADOR/ADMIN tienen alcance global.
        PROFESOR/TUTOR solo tienen alcance si tienen asignación activa en la materia.

        Args:
            materia_id: UUID de la materia (opcional).

        Returns:
            True si tiene alcance.
        """
        if self._es_admin:
            return True
        if materia_id is None:
            return False
        # Verificar asignación activa del usuario en la materia
        from sqlalchemy import and_, select

        from app.models.asignacion import Asignacion

        now = datetime.now(timezone.utc)
        stmt = select(Asignacion).where(
            and_(
                Asignacion.tenant_id == self.tenant_id,
                Asignacion.usuario_id == self.actor_id,
                Asignacion.materia_id == materia_id,
                Asignacion.deleted_at.is_(None),
                Asignacion.desde <= now,
            )
        )
        result = await self.session.scalar(stmt)
        return result is not None

    # ── Creación de slots recurrentes ─────────────────────────────────────

    async def crear_slot_recurrente(
        self, datos: SlotEncuentroCreate
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """Crea un slot recurrente y genera N instancias semanales.

        La generación de instancias sigue la regla D1: para i in range(cant_semanas),
        sumar i*7 días a fecha_inicio.

        Args:
            datos: Datos del slot recurrente.

        Returns:
            Tupla (slot_response, instancias_response).

        Raises:
            BusinessError: Si el usuario no tiene alcance sobre la materia.
        """
        if not await self.verificar_alcance(datos.materia_id):
            raise BusinessError("No tiene permisos para gestionar encuentros en esta materia")

        # Crear slot
        dia_enum = DiaSemana(datos.dia_semana)
        slot = SlotEncuentro(
            tenant_id=self.tenant_id,
            materia_id=datos.materia_id,
            titulo=datos.titulo,
            hora=datos.hora,
            dia_semana=dia_enum,
            fecha_inicio=datos.fecha_inicio,
            cant_semanas=datos.cant_semanas,
            meet_url=datos.meet_url,
        )
        await self.slot_repo.save(slot)

        # Generar instancias (D1: i*7 días)
        instancias: list[dict[str, Any]] = []
        instancias_orm: list[InstanciaEncuentro] = []
        for i in range(datos.cant_semanas):
            fecha_instancia = datos.fecha_inicio + timedelta(weeks=i)
            instancia = InstanciaEncuentro(
                tenant_id=self.tenant_id,
                slot_id=slot.id,
                materia_id=datos.materia_id,
                fecha=fecha_instancia,
                hora=datos.hora,
                titulo=datos.titulo,
                estado=EstadoEncuentro.PROGRAMADO,
                meet_url=datos.meet_url,
            )
            instancias_orm.append(instancia)

        await self.instancia_repo.crear_muchos(instancias_orm)

        # Construir responses
        for inst in instancias_orm:
            instancias.append(self._to_instancia_response(inst))

        slot_response = self._to_slot_response(slot, len(instancias))

        # Auditar
        audit = self._build_audit_service()
        await audit.register(
            accion=ACCION_ENCUENTRO_CREAR,
            actor_id=self.actor_id,
            tenant_id=self.tenant_id,
            materia_id=datos.materia_id,
            detalle={
                "tipo": "slot_recurrente",
                "slot_id": str(slot.id),
                "cant_semanas": datos.cant_semanas,
                "instancias_creadas": len(instancias),
            },
            filas_afectadas=len(instancias) + 1,
        )

        return slot_response, instancias

    # ── Creación de slots únicos ──────────────────────────────────────────

    async def crear_slot_unico(
        self, datos: SlotEncuentroCreateUnico
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """Crea un slot con fecha_unica + 1 instancia.

        Args:
            datos: Datos del slot único.

        Returns:
            Tupla (slot_response, instancias_response).

        Raises:
            BusinessError: Si el usuario no tiene alcance sobre la materia.
        """
        if not await self.verificar_alcance(datos.materia_id):
            raise BusinessError("No tiene permisos para gestionar encuentros en esta materia")

        dia_enum = self._fecha_a_dia_semana(datos.fecha_unica)
        slot = SlotEncuentro(
            tenant_id=self.tenant_id,
            materia_id=datos.materia_id,
            titulo=datos.titulo,
            hora=datos.hora,
            dia_semana=dia_enum,
            fecha_inicio=datos.fecha_unica,
            cant_semanas=0,
            fecha_unica=datos.fecha_unica,
            meet_url=datos.meet_url,
        )
        await self.slot_repo.save(slot)

        instancia = InstanciaEncuentro(
            tenant_id=self.tenant_id,
            slot_id=slot.id,
            materia_id=datos.materia_id,
            fecha=datos.fecha_unica,
            hora=datos.hora,
            titulo=datos.titulo,
            estado=EstadoEncuentro.PROGRAMADO,
            meet_url=datos.meet_url,
        )
        await self.instancia_repo.save(instancia)

        slot_response = self._to_slot_response(slot, 1)
        instancias = [self._to_instancia_response(instancia)]

        audit = self._build_audit_service()
        await audit.register(
            accion=ACCION_ENCUENTRO_CREAR,
            actor_id=self.actor_id,
            tenant_id=self.tenant_id,
            materia_id=datos.materia_id,
            detalle={
                "tipo": "slot_unico",
                "slot_id": str(slot.id),
                "fecha_unica": str(datos.fecha_unica),
            },
            filas_afectadas=2,
        )

        return slot_response, instancias

    # ── Creación de instancia independiente ───────────────────────────────

    async def crear_instancia_independiente(
        self, materia_id: UUID, titulo: str, fecha: date, hora, meet_url: str | None = None
    ) -> dict[str, Any]:
        """Crea una instancia sin slot asociado.

        Args:
            materia_id: UUID de la materia.
            titulo: Título del encuentro.
            fecha: Fecha del encuentro.
            hora: Hora del encuentro.
            meet_url: Enlace de videoconferencia (opcional).

        Returns:
            InstanciaResponse dict.

        Raises:
            BusinessError: Si el usuario no tiene alcance sobre la materia.
        """
        if not await self.verificar_alcance(materia_id):
            raise BusinessError("No tiene permisos para gestionar encuentros en esta materia")

        instancia = InstanciaEncuentro(
            tenant_id=self.tenant_id,
            materia_id=materia_id,
            fecha=fecha,
            hora=hora,
            titulo=titulo,
            estado=EstadoEncuentro.PROGRAMADO,
            meet_url=meet_url,
        )
        await self.instancia_repo.save(instancia)

        audit = self._build_audit_service()
        await audit.register(
            accion=ACCION_ENCUENTRO_CREAR,
            actor_id=self.actor_id,
            tenant_id=self.tenant_id,
            materia_id=materia_id,
            detalle={
                "tipo": "instancia_independiente",
                "instancia_id": str(instancia.id),
            },
            filas_afectadas=1,
        )

        return self._to_instancia_response(instancia)

    # ── Edición de instancias ─────────────────────────────────────────────

    async def editar_instancia(
        self, instancia_id: UUID, datos: InstanciaEncuentroUpdate
    ) -> dict[str, Any]:
        """Actualiza campos editables de una instancia.

        Args:
            instancia_id: UUID de la instancia.
            datos: Datos a actualizar.

        Returns:
            InstanciaResponse dict.

        Raises:
            BusinessError: Si la instancia no existe o el usuario no tiene alcance.
        """
        instancia = await self.instancia_repo.get_by_id(instancia_id)
        if instancia is None:
            raise BusinessError("Instancia no encontrada")

        if not await self.verificar_alcance(instancia.materia_id):
            raise BusinessError("No tiene permisos para modificar esta instancia")

        update_data = datos.model_dump(exclude_none=True)
        if not update_data:
            return self._to_instancia_response(instancia)

        instancia_actualizada = await self.instancia_repo.actualizar(
            instancia_id, update_data
        )
        if instancia_actualizada is None:
            raise BusinessError("Instancia no encontrada")

        audit = self._build_audit_service()
        await audit.register(
            accion=ACCION_ENCUENTRO_MODIFICAR,
            actor_id=self.actor_id,
            tenant_id=self.tenant_id,
            materia_id=instancia.materia_id,
            detalle={
                "instancia_id": str(instancia_id),
                "cambios": update_data,
            },
            filas_afectadas=1,
        )

        return self._to_instancia_response(instancia_actualizada)

    # ── Edición de slots ──────────────────────────────────────────────────

    async def editar_slot(
        self, slot_id: UUID, datos: SlotEncuentroUpdate
    ) -> dict[str, Any]:
        """Actualiza un slot sin afectar instancias ya generadas.

        Args:
            slot_id: UUID del slot.
            datos: Datos a actualizar.

        Returns:
            SlotResponse dict.

        Raises:
            BusinessError: Si el slot no existe o el usuario no tiene alcance.
        """
        slot = await self.slot_repo.get_by_id(slot_id)
        if slot is None:
            raise BusinessError("Slot no encontrado")

        if not await self.verificar_alcance(slot.materia_id):
            raise BusinessError("No tiene permisos para modificar este slot")

        update_data = datos.model_dump(exclude_none=True)
        if not update_data:
            cant = await self.slot_repo.contar_instancias(slot_id)
            return self._to_slot_response(slot, cant)

        slot_actualizado = await self.slot_repo.actualizar(slot_id, update_data)
        if slot_actualizado is None:
            raise BusinessError("Slot no encontrado")

        cant = await self.slot_repo.contar_instancias(slot_id)

        audit = self._build_audit_service()
        await audit.register(
            accion=ACCION_ENCUENTRO_MODIFICAR,
            actor_id=self.actor_id,
            tenant_id=self.tenant_id,
            materia_id=slot.materia_id,
            detalle={
                "slot_id": str(slot_id),
                "cambios": update_data,
            },
            filas_afectadas=1,
        )

        return self._to_slot_response(slot_actualizado, cant)

    # ── Eliminación de slots (soft-delete) ────────────────────────────────

    async def eliminar_slot(self, slot_id: UUID) -> None:
        """Soft-delete de slot + todas sus instancias.

        Args:
            slot_id: UUID del slot.

        Raises:
            BusinessError: Si el slot no existe o el usuario no tiene alcance.
        """
        slot = await self.slot_repo.get_by_id(slot_id)
        if slot is None:
            raise BusinessError("Slot no encontrado")

        if not await self.verificar_alcance(slot.materia_id):
            raise BusinessError("No tiene permisos para eliminar este slot")

        # Soft-delete slot
        await self.slot_repo.soft_delete(slot)

        # Soft-delete instancias asociadas
        instancias_eliminadas = await self.instancia_repo.eliminar_por_slot(slot_id)

        audit = self._build_audit_service()
        await audit.register(
            accion=ACCION_ENCUENTRO_ELIMINAR,
            actor_id=self.actor_id,
            tenant_id=self.tenant_id,
            materia_id=slot.materia_id,
            detalle={
                "slot_id": str(slot_id),
                "instancias_eliminadas": instancias_eliminadas,
            },
            filas_afectadas=1 + instancias_eliminadas,
        )

    # ── Listados ──────────────────────────────────────────────────────────

    async def listar_instancias(
        self,
        materia_id: UUID | None = None,
        slot_id: UUID | None = None,
        desde: date | None = None,
        hasta: date | None = None,
        estado: str | None = None,
    ) -> dict[str, Any]:
        """Lista instancias con filtros, aplicando scope según rol.

        Returns:
            Dict con items y total.
        """
        # Si no es admin, filtrar por sus materias
        usuario_id = None if self._es_admin else self.actor_id

        instancias = await self.instancia_repo.listar(
            materia_id=materia_id,
            slot_id=slot_id,
            desde=desde,
            hasta=hasta,
            estado=estado,
            usuario_id=usuario_id,
        )
        items = [self._to_instancia_response(i) for i in instancias]
        return {"items": items, "total": len(items)}

    async def listar_slots(
        self,
        materia_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Lista slots con filtros, aplicando scope según rol.

        Returns:
            Dict con items y total.
        """
        usuario_id = None if self._es_admin else self.actor_id
        slots = await self.slot_repo.listar(
            materia_id=materia_id,
            usuario_id=usuario_id,
        )
        items = []
        for slot in slots:
            cant = await self.slot_repo.contar_instancias(slot.id)
            items.append(self._to_slot_response(slot, cant))
        return {"items": items, "total": len(items)}

    # ── Exportación HTML para aula ────────────────────────────────────────

    async def generar_html_aula(self, materia_id: UUID) -> dict[str, str]:
        """Genera bloque HTML embebible con encuentros de una materia.

        Incluye encuentros futuros (desde hoy) y pasados SOLO si tienen
        video_url (grabación disponible).

        Args:
            materia_id: UUID de la materia.

        Returns:
            Dict con html string.

        Raises:
            BusinessError: Si el usuario no tiene alcance.
        """
        if not await self.verificar_alcance(materia_id):
            raise BusinessError("No tiene permisos para exportar encuentros de esta materia")

        instancias = await self.instancia_repo.listar_para_exportar(materia_id)

        if not instancias:
            return {"html": "<p>No hay encuentros programados</p>"}

        rows = ""
        for inst in instancias:
            estado_label = {
                "Programado": "🟢 Programado",
                "Realizado": "✅ Realizado",
                "Cancelado": "❌ Cancelado",
            }.get(
                inst.estado.value if hasattr(inst.estado, "value") else str(inst.estado),
                str(inst.estado),
            )
            meet_link = (
                f'<a href="{inst.meet_url}" target="_blank">Enlace</a>'
                if inst.meet_url
                else "—"
            )
            grabacion = (
                f'<a href="{inst.video_url}" target="_blank">Grabación disponible</a>'
                if inst.video_url
                else "—"
            )
            rows += (
                f"<tr>"
                f"<td>{inst.fecha}</td>"
                f"<td>{inst.hora}</td>"
                f"<td>{inst.titulo}</td>"
                f"<td>{estado_label}</td>"
                f"<td>{meet_link}</td>"
                f"<td>{grabacion}</td>"
                f"</tr>\n"
            )

        html = (
            "<table style='width:100%; border-collapse: collapse; font-family: Arial, sans-serif;'>\n"
            "<thead>\n"
            "<tr style='background-color: #4A90D9; color: white;'>\n"
            "<th style='padding: 8px; border: 1px solid #ddd;'>Fecha</th>\n"
            "<th style='padding: 8px; border: 1px solid #ddd;'>Hora</th>\n"
            "<th style='padding: 8px; border: 1px solid #ddd;'>Título</th>\n"
            "<th style='padding: 8px; border: 1px solid #ddd;'>Estado</th>\n"
            "<th style='padding: 8px; border: 1px solid #ddd;'>Enlace</th>\n"
            "<th style='padding: 8px; border: 1px solid #ddd;'>Grabación</th>\n"
            "</tr>\n"
            "</thead>\n"
            "<tbody>\n"
            f"{rows}"
            "</tbody>\n"
            "</table>"
        )

        return {"html": html}

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _fecha_a_dia_semana(fecha: date) -> DiaSemana:
        """Convierte una fecha a DiaSemana.

        Args:
            fecha: Fecha a convertir.

        Returns:
            DiaSemana correspondiente.
        """
        dias = [
            DiaSemana.LUNES,
            DiaSemana.MARTES,
            DiaSemana.MIERCOLES,
            DiaSemana.JUEVES,
            DiaSemana.VIERNES,
            DiaSemana.SABADO,
            DiaSemana.DOMINGO,
        ]
        return dias[fecha.weekday()]
