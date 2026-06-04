"""AnalisisService — logica de computo de atrasados, ranking, reportes y monitores (C-11).

Toda la logica opera en dos capas:
1. Repository: queries de agregacion sobre Calificacion y modelos relacionados.
2. Service: clasifica, filtra y estructura los resultados segun RN-06, RN-07, RN-08, RN-09.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError
from app.repositories.analisis_repository import AnalisisRepository

UMBRAL_DEFAULT = 60


class AnalisisService:
    """Servicio de analisis academico — atrasados, ranking, reportes, monitores."""

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.repo = AnalisisRepository(session, tenant_id)

    # ── Atrasados ───────────────────────────────────────────────────

    async def obtener_atrasados(
        self,
        materia_id: UUID,
        cohorte_id: UUID | None = None,
        comision: str | None = None,
    ) -> dict:
        """Computa alumnos atrasados segun RN-06.

        Un alumno esta atrasado si tiene actividades faltantes (sin calificacion)
        o calificaciones con nota_numerica < umbral.
        """
        calificaciones = await self.repo.listar_calificaciones_por_materia(
            materia_id, cohorte_id
        )
        umbral = await self.repo.obtener_umbral_materia(materia_id)
        umbral_pct = umbral.umbral_pct if umbral else UMBRAL_DEFAULT

        # Agrupar calificaciones por entrada_padron_id
        from collections import defaultdict

        agrupadas: dict[UUID, dict] = defaultdict(
            lambda: {
                "actividades_faltantes": 0,
                "actividades_bajo_umbral": 0,
                "nombre": "",
                "apellidos": "",
                "comision": "",
            }
        )

        # Obtener actividades distintas en la materia
        total_actividades = set()
        for c in calificaciones:
            total_actividades.add(c.actividad)
            entry = agrupadas[c.entrada_padron_id]
            entry["nombre"] = getattr(c, "_nombre", "")
            entry["apellidos"] = getattr(c, "_apellidos", "")

            if c.nota_numerica is not None:
                if Decimal(str(c.nota_numerica)) < Decimal(str(umbral_pct)):
                    entry["actividades_bajo_umbral"] += 1
            elif c.nota_textual is not None and umbral and umbral.valores_aprobatorios:
                if c.nota_textual not in umbral.valores_aprobatorios:
                    entry["actividades_bajo_umbral"] += 1

        total_act_count = len(total_actividades)

        # Clasificar atrasados
        alumnos_atrasados = []
        # Necesitamos obtener entrada_padron info - hacemos una query adicional
        # para enriquecer los datos de alumnos
        alumnos_info = await self._enriquecer_alumnos(
            list(agrupadas.keys()), materia_id, cohorte_id, comision
        )

        for ep_id, info in agrupadas.items():
            # Actividades faltantes = total - actividades con calificacion
            calificadas = sum(
                1
                for c in calificaciones
                if c.entrada_padron_id == ep_id
            )
            faltantes = total_act_count - calificadas
            info["actividades_faltantes"] = max(0, faltantes)

            alumno_data = alumnos_info.get(ep_id, {})
            es_atrasado = (
                info["actividades_faltantes"] > 0
                or info["actividades_bajo_umbral"] > 0
            )
            if es_atrasado:
                alumnos_atrasados.append(
                    {
                        "alumno_id": alumno_data.get("usuario_id"),
                        "nombre": alumno_data.get("nombre", info["nombre"]),
                        "apellidos": alumno_data.get("apellidos", info["apellidos"]),
                        "actividades_faltantes": info["actividades_faltantes"],
                        "actividades_bajo_umbral": info["actividades_bajo_umbral"],
                        "comision": alumno_data.get("comision"),
                    }
                )

        total_alumnos = len(agrupadas)
        return {
            "alumnos_atrasados": alumnos_atrasados,
            "total_alumnos": total_alumnos,
            "porcentaje": round(
                (len(alumnos_atrasados) / total_alumnos * 100), 1
            )
            if total_alumnos > 0
            else 0.0,
        }

    async def _enriquecer_alumnos(
        self,
        entrada_padron_ids: list[UUID],
        materia_id: UUID,
        cohorte_id: UUID | None = None,
        comision: str | None = None,
    ) -> dict:
        """Obtiene datos de EntradaPadron para las IDs dadas."""
        from sqlalchemy import select, and_

        from app.models.entrada_padron import EntradaPadron
        from app.models.version_padron import VersionPadron

        filters = [
            EntradaPadron.id.in_(entrada_padron_ids),
            EntradaPadron.tenant_id == self.tenant_id,
            EntradaPadron.deleted_at.is_(None),
        ]
        if comision:
            filters.append(EntradaPadron.comision == comision)

        stmt = (
            select(
                EntradaPadron.id,
                EntradaPadron.usuario_id,
                EntradaPadron.nombre,
                EntradaPadron.apellidos,
                EntradaPadron.comision,
            )
            .select_from(EntradaPadron)
            .join(VersionPadron, EntradaPadron.version_id == VersionPadron.id)
            .where(
                and_(
                    *filters,
                    VersionPadron.materia_id == materia_id,
                    VersionPadron.deleted_at.is_(None),
                    VersionPadron.activa.is_(True),
                )
            )
        )
        if cohorte_id:
            stmt = stmt.where(VersionPadron.cohorte_id == cohorte_id)

        result = await self.session.execute(stmt)
        rows = result.all()
        return {
            row.id: {
                "usuario_id": row.usuario_id,
                "nombre": row.nombre,
                "apellidos": row.apellidos,
                "comision": row.comision,
            }
            for row in rows
        }

    # ── Ranking ─────────────────────────────────────────────────────

    async def obtener_ranking(
        self,
        materia_id: UUID,
        cohorte_id: UUID | None = None,
    ) -> list[dict]:
        """Ranking de actividades aprobadas (RN-09).

        Solo incluye alumnos con >= 1 actividad aprobada. Orden descendente.
        """
        total_act = await self.repo.total_actividades_materia(materia_id)
        ranking = await self.repo.ranking_aprobados(materia_id, cohorte_id)

        for entry in ranking:
            entry["total_actividades"] = total_act

        return ranking

    # ── Reporte Rapido ─────────────────────────────────────────────

    async def obtener_reporte_rapido(
        self,
        materia_id: UUID,
        cohorte_id: UUID | None = None,
    ) -> dict:
        """Metricas consolidadas de una materia."""
        return await self.repo.reporte_rapido(materia_id, cohorte_id)

    # ── Notas Finales ──────────────────────────────────────────────

    async def obtener_notas_finales(
        self,
        materia_id: UUID,
        cohorte_id: UUID | None = None,
        actividades: list[str] | None = None,
    ) -> list[dict]:
        """Notas finales: promedio por alumno + bandera aprobado."""
        umbral = await self.repo.obtener_umbral_materia(materia_id)
        umbral_pct = umbral.umbral_pct if umbral else UMBRAL_DEFAULT

        notas = await self.repo.notas_finales(materia_id, cohorte_id, actividades)
        for entry in notas:
            promedio = entry.get("promedio")
            if promedio is not None:
                entry["aprobado"] = promedio >= umbral_pct
            else:
                entry["aprobado"] = False

        return notas

    # ── TPs sin corregir ───────────────────────────────────────────

    async def obtener_tps_sin_corregir(
        self,
        materia_id: UUID,
        cohorte_id: UUID | None = None,
    ) -> list[dict]:
        """Detecta TPs textuales finalizados sin calificacion (RN-07, RN-08).

        Solo aplica a actividades de escala textual (RN-08).
        """
        actividades_textuales = await self.repo.actividades_textuales_materia(
            materia_id
        )
        pendientes: list[dict] = []
        for act in actividades_textuales:
            entradas = await self.repo.entradas_sin_calificacion_textual(
                materia_id, act, cohorte_id
            )
            pendientes.extend(entradas)

        return pendientes

    # ── Monitores ──────────────────────────────────────────────────

    async def obtener_monitor_general(
        self,
        materia_id: UUID | None = None,
        regional: str | None = None,
        comision: str | None = None,
        q: str | None = None,
    ) -> dict:
        """Monitor general transversal (F2.7)."""
        alumnos = await self.repo.monitor_general(
            materia_id=materia_id,
            regional=regional,
            comision=comision,
            q=q,
        )
        # Enriquecer con actividades (por ahora lista vacía; implementación
        # completa requeriría join a Calificacion por alumno)
        for alumno in alumnos:
            alumno["actividades"] = []
        return {
            "alumnos": alumnos,
            "total": len(alumnos),
        }

    async def obtener_monitor_seguimiento(
        self,
        usuario_id: UUID,
        actividad: str | None = None,
        min_aprobadas: int | None = None,
        fecha_desde: datetime | None = None,
        fecha_hasta: datetime | None = None,
    ) -> dict:
        """Monitor de seguimiento para tutor/profesor (F2.8) o coordinacion/admin (F2.9)."""
        # Obtener alumnos del usuario por sus asignaciones
        alumno_ids = await self.repo.obtener_alumnos_por_asignacion(usuario_id)

        if not alumno_ids:
            return {"alumnos": [], "total": 0}

        rows = await self.repo.monitor_seguimiento(
            usuario_ids=alumno_ids,
            actividad=actividad,
            min_aprobadas=min_aprobadas,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
        )

        # Agrupar por alumno
        from collections import defaultdict

        agrupados: dict[UUID, dict] = defaultdict(
            lambda: {"alumno_id": None, "nombre": "", "apellidos": "", "actividades": []}
        )
        for row in rows:
            uid = row["alumno_id"]
            if uid is None:
                continue
            entry = agrupados[uid]
            entry["alumno_id"] = uid
            entry["nombre"] = row.get("nombre", "")
            entry["apellidos"] = row.get("apellidos", "")
            entry["actividades"].append(
                {
                    "actividad": row["actividad"],
                    "nota_numerica": row.get("nota_numerica"),
                    "nota_textual": row.get("nota_textual"),
                    "aprobado": row.get("aprobado"),
                }
            )

        return {
            "alumnos": list(agrupados.values()),
            "total": len(agrupados),
        }
