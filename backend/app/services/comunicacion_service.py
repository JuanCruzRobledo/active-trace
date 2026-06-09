"""ComunicacionService — lógica de preview, encolado, aprobación y cancelación (C-12).

Flujo:
1. Preview: genera token hash del contenido (RN-16).
2. Encolar: valida preview token, verifica alcance según rol, crea Pendientes.
3. Aprobación: si tenant requiere aprobación, lotes >1 destinatario quedan en espera.
4. Worker: procesa Pendientes → Enviado/Error.
"""

from __future__ import annotations

import hashlib
import json
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record as audit_record
from app.core.exceptions import BusinessError
from app.models.asignacion import Asignacion
from app.models.comunicacion import Comunicacion, EstadoComunicacion
from app.models.entrada_padron import EntradaPadron
from app.repositories.comunicacion_repository import ComunicacionRepository
from app.schemas.comunicacion import CancelarResponse


def hash_destinatarios(destinatarios: list[dict]) -> str:
    """Genera hash determinístico de la lista de destinatarios."""
    raw = json.dumps(destinatarios, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class ComunicacionService:
    """Servicio de comunicaciones: preview, encolado, aprobación, cancelación."""

    def __init__(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        repo: ComunicacionRepository | None = None,
    ) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.repo = repo or ComunicacionRepository(session, tenant_id)

    # ── Preview ─────────────────────────────────────────────────────

    async def generar_preview(
        self,
        asunto: str,
        cuerpo: str,
        destinatarios: list[dict],
    ) -> dict:
        """Genera preview token y renderiza el contenido.

        Returns:
            Dict con preview_token, preview_html, cantidad_destinatarios.
        """
        preview_html = f"<strong>{asunto}</strong><br><p>{cuerpo}</p>"
        token = self._generar_hash(asunto, cuerpo, destinatarios)
        return {
            "preview_token": token,
            "preview_html": preview_html,
            "cantidad_destinatarios": len(destinatarios),
        }

    def _generar_hash(
        self,
        asunto: str,
        cuerpo: str,
        destinatarios: list[dict],
    ) -> str:
        """Hash SHA-256 del contenido para validación de preview."""
        raw = f"{asunto}::{cuerpo}::" + hash_destinatarios(destinatarios)
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    def validar_preview(
        self,
        preview_token: str,
        asunto: str,
        cuerpo: str,
        destinatarios: list[dict],
    ) -> bool:
        """Valida que el preview_token coincida con el contenido actual."""
        expected = self._generar_hash(asunto, cuerpo, destinatarios)
        return preview_token == expected

    # ── Validación de alcance ────────────────────────────────────────

    async def _validar_alcance_profesor(
        self,
        usuario_id: UUID,
        materia_id: UUID,
        destinatarios: list[dict],
        roles: list[str],
    ) -> None:
        """Valida que un PROFESOR solo envíe a alumnos de sus comisiones.

        Si ``Asignacion.comisiones`` es NULL, no hay restricción.
        ADMIN y COORDINADOR no pasan por esta validación.
        """
        if "PROFESOR" not in roles or "ADMIN" in roles or "COORDINADOR" in roles:
            return

        stmt = select(Asignacion).where(
            Asignacion.usuario_id == usuario_id,
            Asignacion.materia_id == materia_id,
            Asignacion.rol == "PROFESOR",
            Asignacion.tenant_id == self.tenant_id,
        )
        asig = await self.session.scalar(stmt)

        # Sin asignación o sin comisiones definidas → sin restricción
        if asig is None or asig.comisiones is None:
            return

        comisiones_permitidas = set(asig.comisiones)

        for dest in destinatarios:
            tipo = dest["tipo"]
            valor = dest["valor"]
            comision = None

            if tipo == "entrada_padron_id":
                ep = await self.session.get(EntradaPadron, UUID(valor))
                if ep is not None:
                    comision = ep.comision
            elif tipo == "email":
                stmt_ep = select(EntradaPadron).where(
                    EntradaPadron.email == valor,
                    EntradaPadron.tenant_id == self.tenant_id,
                )
                ep = await self.session.scalar(stmt_ep)
                if ep is not None:
                    comision = ep.comision

            if comision is None or comision not in comisiones_permitidas:
                raise BusinessError(
                    "No tiene permisos para enviar a este alumno "
                    "(comisión no asignada)"
                )

    async def _validar_alcance_profesor_individual(
        self,
        usuario_id: UUID,
        materia_id: UUID,
        entrada_padron_id: UUID,
        roles: list[str],
    ) -> None:
        """Valida alcance de PROFESOR para envío individual."""
        if "PROFESOR" not in roles or "ADMIN" in roles or "COORDINADOR" in roles:
            return

        stmt = select(Asignacion).where(
            Asignacion.usuario_id == usuario_id,
            Asignacion.materia_id == materia_id,
            Asignacion.rol == "PROFESOR",
            Asignacion.tenant_id == self.tenant_id,
        )
        asig = await self.session.scalar(stmt)

        if asig is None or asig.comisiones is None:
            return

        comisiones_permitidas = set(asig.comisiones)

        ep = await self.session.get(EntradaPadron, entrada_padron_id)
        if ep is None or ep.comision not in comisiones_permitidas:
            raise BusinessError(
                "No tiene permisos para enviar a este alumno "
                "(comisión no asignada)"
            )

    # ── Encolar ─────────────────────────────────────────────────────

    async def encolar_envio(
        self,
        usuario_id: UUID,
        tenant_id: UUID,
        preview_token: str,
        asunto: str,
        cuerpo: str,
        materia_id: UUID,
        destinatarios: list[dict],
        roles: list[str],
        requiere_aprobacion: bool = False,
    ) -> dict:
        """Valida preview_token, verifica alcance y encola comunicaciones.

        Args:
            usuario_id: UUID del usuario que envía.
            tenant_id: UUID del tenant.
            preview_token: Token de validación de preview.
            asunto: Asunto del mensaje.
            cuerpo: Cuerpo del mensaje.
            materia_id: UUID de la materia.
            destinatarios: Lista de {tipo, valor}.
            roles: Roles del usuario.
            requiere_aprobacion: Si el envío masivo requiere aprobación.

        Returns:
            Dict con lote_id, estado, total_mensajes.
        """
        if not self.validar_preview(preview_token, asunto, cuerpo, destinatarios):
            raise BusinessError("El preview_token no coincide con el contenido actual")

        await self._validar_alcance_profesor(
            usuario_id, materia_id, destinatarios, roles
        )

        necesita_aprobacion = requiere_aprobacion and len(destinatarios) > 1

        lote_id = uuid4()
        creadas = await self.repo.crear_muchos(
            tenant_id=tenant_id,
            enviado_por_id=usuario_id,
            materia_id=materia_id,
            lote_id=lote_id,
            asunto=asunto,
            cuerpo=cuerpo,
            destinatarios=destinatarios,
        )

        if necesita_aprobacion:
            for c in creadas:
                c.necesita_aprobacion = lote_id
            await self.session.flush()

        # Audit log
        audit_record(
            "COMUNICACION_ENVIAR",
            {
                "actor_id": str(usuario_id),
                "tenant_id": str(tenant_id),
                "lote_id": str(lote_id),
                "cantidad": len(creadas),
                "accion": "encolar",
            },
        )

        return {
            "lote_id": lote_id,
            "estado": "Pendiente",
            "total_mensajes": len(creadas),
            "requiere_aprobacion": necesita_aprobacion,
        }

    async def encolar_envio_individual(
        self,
        usuario_id: UUID,
        tenant_id: UUID,
        preview_token: str,
        asunto: str,
        cuerpo: str,
        materia_id: UUID,
        entrada_padron_id: UUID,
        roles: list[str],
    ) -> dict:
        """Encola una comunicación individual (1 destinatario).

        No requiere aprobación aunque el flag esté activo.
        """
        if not self.validar_preview(
            preview_token, asunto, cuerpo,
            [{"tipo": "entrada_padron_id", "valor": str(entrada_padron_id)}],
        ):
            raise BusinessError("El preview_token no coincide con el contenido actual")

        await self._validar_alcance_profesor_individual(
            usuario_id, materia_id, entrada_padron_id, roles
        )

        lote_id = uuid4()
        destinatarios = [{"tipo": "entrada_padron_id", "valor": str(entrada_padron_id)}]

        creadas = await self.repo.crear_muchos(
            tenant_id=tenant_id,
            enviado_por_id=usuario_id,
            materia_id=materia_id,
            lote_id=lote_id,
            asunto=asunto,
            cuerpo=cuerpo,
            destinatarios=destinatarios,
        )

        audit_record(
            "COMUNICACION_ENVIAR",
            {
                "actor_id": str(usuario_id),
                "tenant_id": str(tenant_id),
                "lote_id": str(lote_id),
                "cantidad": 1,
                "accion": "encolar_individual",
            },
        )

        return {
            "lote_id": lote_id,
            "estado": "Pendiente",
            "total_mensajes": 1,
            "requiere_aprobacion": False,
        }

    # ── Consultas ───────────────────────────────────────────────────

    async def obtener_estado_lote(
        self, tenant_id: UUID, lote_id: UUID
    ) -> dict:
        """Estado agregado de un lote."""
        result = await self.repo.listar_por_lote(tenant_id, lote_id)
        pendientes = result["pendientes"]
        enviados = result["enviados"]
        fallidos = result["fallidos"]
        cancelados = result["cancelados"]

        if pendientes > 0:
            estado = "Pendiente"
        elif enviados > 0 and fallidos == 0 and cancelados == 0:
            estado = "Enviado"
        elif fallidos > 0 and enviados == 0 and cancelados == 0:
            estado = "Error"
        elif cancelados > 0 and enviados == 0 and fallidos == 0:
            estado = "Cancelado"
        else:
            estado = "Mixto"
        result["estado"] = estado
        result["necesita_aprobacion"] = False
        return result

    async def obtener_mis_envios(
        self,
        usuario_id: UUID,
        tenant_id: UUID,
        pagina: int = 1,
        tamano: int = 20,
    ) -> dict:
        """Historial paginado de envíos del usuario."""
        items, total = await self.repo.listar_por_usuario(
            tenant_id, usuario_id, pagina, tamano
        )
        return {
            "items": [
                {
                    "lote_id": c.lote_id,
                    "materia_nombre": None,
                    "created_at": c.created_at,
                    "total": 1,
                    "estado": c.estado.value,
                }
                for c in items
            ],
            "total": total,
            "pagina": pagina,
        }

    # ── Cancelación ─────────────────────────────────────────────────

    async def cancelar_comunicacion(
        self, comunicacion_id: UUID, usuario_id: UUID
    ) -> CancelarResponse:
        """Cancela una comunicación Pendiente individual (solo del propio usuario)."""
        ok = await self.repo.cancelar(comunicacion_id, usuario_id)
        if not ok:
            raise BusinessError("Comunicación no encontrada o no se puede cancelar")
        return CancelarResponse(
            comunicacion_id=comunicacion_id, estado="Cancelado"
        )

    # ── Aprobación ──────────────────────────────────────────────────

    async def aprobar_lote(
        self, lote_id: UUID, aprobador_id: UUID
    ) -> None:
        """Aprueba un lote de comunicaciones."""
        await self.repo.aprobar_lote(lote_id, aprobador_id)
        audit_record(
            "COMUNICACION_ENVIAR",
            {
                "actor_id": str(aprobador_id),
                "tenant_id": str(self.tenant_id),
                "lote_id": str(lote_id),
                "accion": "aprobar",
            },
        )

    async def rechazar_lote(
        self, lote_id: UUID, aprobador_id: UUID
    ) -> None:
        """Rechaza un lote de comunicaciones (las cancela)."""
        await self.repo.rechazar_lote(lote_id, aprobador_id)
        audit_record(
            "COMUNICACION_ENVIAR",
            {
                "actor_id": str(aprobador_id),
                "tenant_id": str(self.tenant_id),
                "lote_id": str(lote_id),
                "accion": "rechazar",
            },
        )

    async def requiere_aprobacion(
        self, tenant_id: UUID, cantidad_destinatarios: int
    ) -> bool:
        """Consulta si un envío con N destinatarios requiere aprobación.

        Por defecto: requiere aprobación si cantidad > 1 (configurable
        por tenant vía flag aprobacion_comunicaciones_requerida).
        """
        return cantidad_destinatarios > 1
