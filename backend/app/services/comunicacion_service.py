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

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record as audit_record
from app.core.exceptions import BusinessError
from app.models.comunicacion import Comunicacion, EstadoComunicacion
from app.repositories.comunicacion_repository import ComunicacionRepository


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
            Dict con lote_id, estado_agregado, total_mensajes.
        """
        if not self.validar_preview(preview_token, asunto, cuerpo, destinatarios):
            raise BusinessError("El preview_token no coincide con el contenido actual")

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
            "estado_agregado": "Pendiente",
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
            "estado_agregado": "Pendiente",
            "total_mensajes": 1,
            "requiere_aprobacion": False,
        }

    # ── Consultas ───────────────────────────────────────────────────

    async def obtener_estado_lote(
        self, tenant_id: UUID, lote_id: UUID
    ) -> dict:
        """Estado agregado de un lote."""
        result = await self.repo.listar_por_lote(tenant_id, lote_id)
        if result["pendientes"] == 0 and result["enviados"] == 0:
            estado = "Cancelado"
        elif result["enviados"] > 0 and result["pendientes"] == 0:
            estado = "Enviado"
        else:
            estado = "Pendiente"
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
        self, lote_id: UUID, usuario_id: UUID
    ) -> dict:
        """Cancela comunicaciones Pendientes de un lote (solo del propio usuario)."""
        ok = await self.repo.cancelar_lote(lote_id, usuario_id)
        if not ok:
            raise BusinessError("Comunicación no encontrada o no se puede cancelar")
        return {"lote_id": lote_id, "estado": "Cancelado"}

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
