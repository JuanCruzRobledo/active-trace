"""UmbralService — configuracion de umbrales de aprobacion y recalculo.

Permite obtener y configurar umbrales por asignacion+materia, y
recalcula el campo ``aprobado`` de las calificaciones existentes
cuando el umbral cambia.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError
from app.models.umbral_materia import UmbralMateria
from app.repositories.calificacion_repository import CalificacionRepository
from app.repositories.umbral_materia_repository import UmbralMateriaRepository


_DEFAULT_UMBRAL_PCT = 60
_DEFAULT_VALORES_APROBATORIOS = ["Satisfactorio", "Supera lo esperado"]


class UmbralService:
    """Servicio de umbrales de aprobacion."""

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.umbral_repo = UmbralMateriaRepository(session, tenant_id)
        self.calificacion_repo = CalificacionRepository(session, tenant_id)

    # ── Obtener ─────────────────────────────────────────────────────────

    async def obtener_umbral(
        self, materia_id: UUID, asignacion_id: UUID
    ) -> dict:
        """Retorna la configuracion de umbral para una asignacion+materia.

        Si no existe configuracion, retorna valores por defecto.

        Args:
            materia_id: UUID de la materia.
            asignacion_id: UUID de la asignacion.

        Returns:
            Dict con umbral_pct y valores_aprobatorios.
        """
        umbral = await self.umbral_repo.find_by_asignacion(asignacion_id)

        if umbral is not None:
            return {
                "umbral_pct": umbral.umbral_pct,
                "valores_aprobatorios": umbral.valores_aprobatorios or [],
            }

        return {
            "umbral_pct": _DEFAULT_UMBRAL_PCT,
            "valores_aprobatorios": list(_DEFAULT_VALORES_APROBATORIOS),
        }

    async def _obtener_umbral_interno(
        self, asignacion_id: UUID
    ) -> UmbralMateria | None:
        """Version privada que retorna la instancia del modelo."""
        return await self.umbral_repo.find_by_asignacion(asignacion_id)

    # ── Configurar ──────────────────────────────────────────────────────

    async def configurar_umbral(
        self,
        materia_id: UUID,
        asignacion_id: UUID,
        umbral_pct: int | None,
        valores_aprobatorios: list[str] | None,
        usuario_id: UUID,
    ) -> dict[str, Any]:
        """Configura o actualiza el umbral de una asignacion+materia.

        Si el umbral cambio, recalcula el campo ``aprobado`` de todas
        las calificaciones de la materia.

        Args:
            materia_id: UUID de la materia.
            asignacion_id: UUID de la asignacion.
            umbral_pct: Nuevo porcentaje (0-100) o None para mantener.
            valores_aprobatorios: Nuevos valores textuales aprobatorios
                o None para mantener.
            usuario_id: UUID del usuario que configura.

        Returns:
            Dict con el UmbralMateria actualizado y cantidad de
            calificaciones recalculadas.

        Raises:
            BusinessError: Si umbral_pct esta fuera de rango.
        """
        umbral_pct_final = umbral_pct
        valores_finales = valores_aprobatorios

        # Obtener config actual
        actual = await self._obtener_umbral_interno(asignacion_id)

        if actual is not None:
            if umbral_pct is None:
                umbral_pct_final = actual.umbral_pct
            if valores_aprobatorios is None:
                valores_finales = actual.valores_aprobatorios

        if umbral_pct is not None and not (0 <= umbral_pct <= 100):
            raise BusinessError(
                f"umbral_pct debe estar entre 0 y 100, se recibio {umbral_pct}"
            )

        if umbral_pct_final is None:
            umbral_pct_final = _DEFAULT_UMBRAL_PCT
        if valores_finales is None:
            valores_finales = _DEFAULT_VALORES_APROBATORIOS

        # Detectar si hubo cambios
        hubo_cambio = True
        if actual is not None:
            hubo_cambio = (
                actual.umbral_pct != umbral_pct_final
                or actual.valores_aprobatorios != valores_finales
            )

        # Upsert
        umbral = await self.umbral_repo.upsert(
            asignacion_id=asignacion_id,
            materia_id=materia_id,
            umbral_pct=umbral_pct_final,
            valores_aprobatorios=valores_finales,
        )

        # Recalcular si hubo cambios
        recalculadas = 0
        if hubo_cambio:
            recalculadas = await self.calificacion_repo.recalcular_aprobado(
                materia_id=materia_id,
                umbral_pct=umbral_pct_final,
                valores_aprobatorios=valores_finales,
            )

        return {
            "umbral_pct": umbral.umbral_pct,
            "valores_aprobatorios": umbral.valores_aprobatorios or [],
            "calificaciones_recalculadas": recalculadas,
        }

    # ── Recalculo en lote ──────────────────────────────────────────────

    async def _recalcular_en_lote(
        self,
        materia_id: UUID,
        umbral_pct: int,
        valores_aprobatorios: list[str],
    ) -> int:
        """Recalcula el campo aprobado de todas las calificaciones
        de una materia.

        Args:
            materia_id: UUID de la materia.
            umbral_pct: Porcentaje minimo para aprobar.
            valores_aprobatorios: Valores textuales aprobatorios.

        Returns:
            Cantidad de calificaciones actualizadas.
        """
        return await self.calificacion_repo.recalcular_aprobado(
            materia_id=materia_id,
            umbral_pct=umbral_pct,
            valores_aprobatorios=valores_aprobatorios,
        )
