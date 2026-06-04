"""AnalisisRepository — queries de agregacion para analisis de calificaciones (C-11).

Todas las queries filtran por tenant_id (multi-tenancy row-level) y excluyen
registros soft-delete.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asignacion import Asignacion
from app.models.calificacion import Calificacion
from app.models.entrada_padron import EntradaPadron
from app.models.umbral_materia import UmbralMateria
from app.models.version_padron import VersionPadron
from app.repositories.base import BaseRepository


class AnalisisRepository(BaseRepository[Calificacion]):
    """Repository de consultas de agregacion para el modulo de analisis."""

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        super().__init__(session, Calificacion, tenant_id)

    # ── Helpers ─────────────────────────────────────────────────────

    def _tenant_filter(self) -> list:
        """Retorna lista de condiciones base: tenant + soft-delete."""
        return [
            self.model.tenant_id == self.tenant_id,
            self.model.deleted_at.is_(None),
        ]

    # ── Atrasados ───────────────────────────────────────────────────

    async def listar_calificaciones_por_materia(
        self, materia_id: UUID, cohorte_id: UUID | None = None
    ) -> list[Calificacion]:
        """Obtiene todas las calificaciones de una materia, opcionalmente filtradas por cohorte."""
        filters = [
            *self._tenant_filter(),
            self.model.materia_id == materia_id,
        ]
        if cohorte_id:
            # Join con entrada_padron → version_padron para filtrar por cohorte
            stmt = (
                select(self.model)
                .join(EntradaPadron, self.model.entrada_padron_id == EntradaPadron.id)
                .join(VersionPadron, EntradaPadron.version_id == VersionPadron.id)
                .where(
                    and_(
                        *filters,
                        VersionPadron.cohorte_id == cohorte_id,
                        VersionPadron.deleted_at.is_(None),
                    )
                )
            )
        else:
            stmt = select(self.model).where(and_(*filters))
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def obtener_umbral_materia(
        self, materia_id: UUID
    ) -> UmbralMateria | None:
        """Obtiene el umbral configurado para la materia (primer registro activo)."""
        stmt = (
            select(UmbralMateria)
            .where(
                and_(
                    UmbralMateria.materia_id == materia_id,
                    UmbralMateria.tenant_id == self.tenant_id,
                    UmbralMateria.deleted_at.is_(None),
                )
            )
            .limit(1)
        )
        result = await self.session.scalars(stmt)
        return result.one_or_none()

    # ── Ranking ─────────────────────────────────────────────────────

    async def ranking_aprobados(
        self, materia_id: UUID, cohorte_id: UUID | None = None
    ) -> list[dict]:
        """Retorna ranking de alumnos con >= 1 actividad aprobada, ordenado descendente."""
        filters = [
            *self._tenant_filter(),
            self.model.materia_id == materia_id,
            self.model.aprobado.is_(True),
        ]
        base_query = select(self.model).where(and_(*filters))

        if cohorte_id:
            base_query = (
                base_query.join(
                    EntradaPadron, self.model.entrada_padron_id == EntradaPadron.id
                )
                .join(VersionPadron, EntradaPadron.version_id == VersionPadron.id)
                .where(
                    and_(
                        VersionPadron.cohorte_id == cohorte_id,
                        VersionPadron.deleted_at.is_(None),
                    )
                )
            )

        stmt = (
            select(
                EntradaPadron.usuario_id,
                EntradaPadron.nombre,
                EntradaPadron.apellidos,
                func.count(self.model.id).label("cantidad_aprobadas"),
                func.count().over().label("total_actividades"),  # noqa
            )
            .select_from(self.model)
            .join(EntradaPadron, self.model.entrada_padron_id == EntradaPadron.id)
            .where(base_query.whereclause)  # type: ignore[arg-type]
            .group_by(
                EntradaPadron.usuario_id,
                EntradaPadron.nombre,
                EntradaPadron.apellidos,
            )
            .having(func.count(self.model.id) >= 1)
            .order_by(func.count(self.model.id).desc())
        )
        result = await self.session.execute(stmt)
        rows = result.all()
        return [
            {
                "alumno_id": row.usuario_id,
                "nombre": row.nombre,
                "apellidos": row.apellidos,
                "cantidad_aprobadas": row.cantidad_aprobadas,
                "total_actividades": 0,  # Se completa en service
            }
            for row in rows
        ]

    async def total_actividades_materia(self, materia_id: UUID) -> int:
        """Cuantas actividades distintas tiene una materia."""
        stmt = (
            select(func.count(func.distinct(self.model.actividad)))
            .where(
                and_(
                    self.model.materia_id == materia_id,
                    self.model.tenant_id == self.tenant_id,
                    self.model.deleted_at.is_(None),
                )
            )
        )
        result = await self.session.scalar(stmt)
        return result or 0

    # ── Reporte Rapido ──────────────────────────────────────────────

    async def reporte_rapido(
        self, materia_id: UUID, cohorte_id: UUID | None = None
    ) -> dict:
        """Retorna metricas agregadas de una materia."""
        filters = [
            *self._tenant_filter(),
            self.model.materia_id == materia_id,
        ]
        base = select(self.model).where(and_(*filters))

        if cohorte_id:
            base = (
                base.join(
                    EntradaPadron, self.model.entrada_padron_id == EntradaPadron.id
                )
                .join(VersionPadron, EntradaPadron.version_id == VersionPadron.id)
                .where(
                    and_(
                        VersionPadron.cohorte_id == cohorte_id,
                        VersionPadron.deleted_at.is_(None),
                    )
                )
            )

        # Alumnos distintos con calificaciones
        alumnos_count_q = (
            select(func.count(func.distinct(self.model.entrada_padron_id)))
            .select_from(self.model)
            .where(base.whereclause)  # type: ignore[arg-type]
        )
        total_alumnos = await self.session.scalar(alumnos_count_q) or 0

        # Aprobados distintos
        aprobados_q = (
            select(func.count(func.distinct(self.model.entrada_padron_id)))
            .select_from(self.model)
            .where(
                and_(
                    base.whereclause,  # type: ignore[arg-type]
                    self.model.aprobado.is_(True),
                )
            )
        )
        aprobados = await self.session.scalar(aprobados_q) or 0

        # Cantidad de actividades distintas
        actividades_q = (
            select(func.count(func.distinct(self.model.actividad)))
            .select_from(self.model)
            .where(base.whereclause)  # type: ignore[arg-type]
        )
        cantidad_actividades = await self.session.scalar(actividades_q) or 0

        atrasados = total_alumnos - aprobados if total_alumnos > 0 else 0
        porcentaje = round((aprobados / total_alumnos * 100), 1) if total_alumnos > 0 else 0.0

        return {
            "total_alumnos": total_alumnos,
            "aprobados": aprobados,
            "atrasados": atrasados,
            "porcentaje_aprobacion": porcentaje,
            "cantidad_actividades": cantidad_actividades,
        }

    # ── Notas Finales ───────────────────────────────────────────────

    async def notas_finales(
        self,
        materia_id: UUID,
        cohorte_id: UUID | None = None,
        actividades: list[str] | None = None,
    ) -> list[dict]:
        """Promedio de calificaciones por alumno, opcionalmente filtrado por actividades."""
        filters = [
            *self._tenant_filter(),
            self.model.materia_id == materia_id,
        ]
        if actividades:
            filters.append(self.model.actividad.in_(actividades))

        base = (
            select(self.model)
            .where(and_(*filters))
        )
        if cohorte_id:
            base = (
                base.join(
                    EntradaPadron, self.model.entrada_padron_id == EntradaPadron.id
                )
                .join(VersionPadron, EntradaPadron.version_id == VersionPadron.id)
                .where(
                    and_(
                        VersionPadron.cohorte_id == cohorte_id,
                        VersionPadron.deleted_at.is_(None),
                    )
                )
            )

        stmt = (
            select(
                EntradaPadron.usuario_id,
                EntradaPadron.nombre,
                EntradaPadron.apellidos,
                func.avg(self.model.nota_numerica).label("promedio"),
            )
            .select_from(self.model)
            .join(EntradaPadron, self.model.entrada_padron_id == EntradaPadron.id)
            .where(and_(base.whereclause, self.model.nota_numerica.isnot(None)))  # type: ignore[arg-type]
            .group_by(
                EntradaPadron.usuario_id,
                EntradaPadron.nombre,
                EntradaPadron.apellidos,
            )
        )
        result = await self.session.execute(stmt)
        rows = result.all()
        return [
            {
                "alumno_id": row.usuario_id,
                "nombre": row.nombre,
                "apellidos": row.apellidos,
                "promedio": float(row.promedio) if row.promedio else None,
            }
            for row in rows
        ]

    # ── TPs sin corregir ────────────────────────────────────────────

    async def actividades_textuales_materia(self, materia_id: UUID) -> list[str]:
        """Lista de actividades textuales (sin nota_numerica) en una materia."""
        stmt = (
            select(func.distinct(self.model.actividad))
            .where(
                and_(
                    self.model.materia_id == materia_id,
                    self.model.tenant_id == self.tenant_id,
                    self.model.deleted_at.is_(None),
                    self.model.nota_numerica.is_(None),
                    self.model.nota_textual.isnot(None),
                )
            )
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def entradas_sin_calificacion_textual(
        self,
        materia_id: UUID,
        actividad: str,
        cohorte_id: UUID | None = None,
    ) -> list[dict]:
        """Entradas del padron sin calificacion para una actividad textual especifica."""
        # Subquery: entradas que SI tienen calificacion para esta actividad
        calificadas_subq = (
            select(self.model.entrada_padron_id)
            .where(
                and_(
                    self.model.materia_id == materia_id,
                    self.model.actividad == actividad,
                    self.model.tenant_id == self.tenant_id,
                    self.model.deleted_at.is_(None),
                )
            )
            .scalar_subquery()
        )

        filters = [
            EntradaPadron.tenant_id == self.tenant_id,
            EntradaPadron.deleted_at.is_(None),
            EntradaPadron.id.notin_(calificadas_subq),
        ]
        if cohorte_id:
            filters.append(VersionPadron.cohorte_id == cohorte_id)

        stmt = (
            select(
                EntradaPadron.usuario_id,
                EntradaPadron.nombre,
                EntradaPadron.apellidos,
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
        result = await self.session.execute(stmt)
        rows = result.all()
        return [
            {
                "alumno_id": row.usuario_id,
                "nombre": row.nombre,
                "apellidos": row.apellidos,
                "actividad": actividad,
            }
            for row in rows
        ]

    # ── Monitores ───────────────────────────────────────────────────

    async def monitor_general(
        self,
        materia_id: UUID | None = None,
        regional: str | None = None,
        comision: str | None = None,
        q: str | None = None,
    ) -> list[dict]:
        """Vista transversal de alumnos con estado de actividades (F2.7)."""
        filters = [
            EntradaPadron.tenant_id == self.tenant_id,
            EntradaPadron.deleted_at.is_(None),
        ]
        version_filters = [
            VersionPadron.tenant_id == self.tenant_id,
            VersionPadron.deleted_at.is_(None),
            VersionPadron.activa.is_(True),
        ]
        if materia_id:
            version_filters.append(VersionPadron.materia_id == materia_id)
        if regional:
            filters.append(EntradaPadron.regional == regional)
        if comision:
            filters.append(EntradaPadron.comision == comision)
        if q:
            filters.append(
                EntradaPadron.nombre.ilike(f"%{q}%")
                | EntradaPadron.apellidos.ilike(f"%{q}%")
            )

        stmt = (
            select(
                EntradaPadron.usuario_id,
                EntradaPadron.nombre,
                EntradaPadron.apellidos,
                EntradaPadron.comision,
            )
            .select_from(EntradaPadron)
            .join(VersionPadron, EntradaPadron.version_id == VersionPadron.id)
            .where(and_(*filters, *version_filters))
            .distinct()
        )
        result = await self.session.execute(stmt)
        rows = result.all()
        return [
            {
                "alumno_id": row.usuario_id,
                "nombre": row.nombre,
                "apellidos": row.apellidos,
                "comision": row.comision,
            }
            for row in rows
        ]

    async def monitor_seguimiento(
        self,
        usuario_ids: list[UUID],
        actividad: str | None = None,
        min_aprobadas: int | None = None,
        fecha_desde: datetime | None = None,
        fecha_hasta: datetime | None = None,
    ) -> list[dict]:
        """Vista de seguimiento para un conjunto de alumnos (F2.8 / F2.9)."""
        filters = [
            *self._tenant_filter(),
            EntradaPadron.usuario_id.in_(usuario_ids),
            EntradaPadron.deleted_at.is_(None),
        ]
        if fecha_desde:
            filters.append(self.model.importado_at >= fecha_desde)
        if fecha_hasta:
            filters.append(self.model.importado_at <= fecha_hasta)

        base = (
            select(self.model)
            .join(EntradaPadron, self.model.entrada_padron_id == EntradaPadron.id)
            .where(and_(*filters))
        )

        # Si hay filtro de actividad, aplicarlo
        if actividad:
            base = base.where(self.model.actividad == actividad)

        # Si hay min_aprobadas, filtrar alumnos que cumplan
        if min_aprobadas is not None:
            aprobadas_subq = (
                select(
                    EntradaPadron.usuario_id,
                    func.count(self.model.id).label("aprobadas"),
                )
                .select_from(self.model)
                .join(EntradaPadron, self.model.entrada_padron_id == EntradaPadron.id)
                .where(
                    and_(
                        *filters,
                        self.model.aprobado.is_(True),
                    )
                )
                .group_by(EntradaPadron.usuario_id)
                .having(func.count(self.model.id) >= min_aprobadas)
                .subquery()
            )
            base = base.join(
                aprobadas_subq,
                EntradaPadron.usuario_id == aprobadas_subq.c.usuario_id,
            )

        stmt = (
            select(
                EntradaPadron.usuario_id,
                EntradaPadron.nombre,
                EntradaPadron.apellidos,
                self.model.actividad,
                self.model.nota_numerica,
                self.model.nota_textual,
                self.model.aprobado,
            )
            .select_from(self.model)
            .join(EntradaPadron, self.model.entrada_padron_id == EntradaPadron.id)
            .where(base.whereclause)  # type: ignore[arg-type]
            .order_by(EntradaPadron.nombre, self.model.actividad)
        )
        result = await self.session.execute(stmt)
        rows = result.all()
        return [
            {
                "alumno_id": row.usuario_id,
                "nombre": row.nombre,
                "apellidos": row.apellidos,
                "actividad": row.actividad,
                "nota_numerica": float(row.nota_numerica) if row.nota_numerica else None,
                "nota_textual": row.nota_textual,
                "aprobado": row.aprobado,
            }
            for row in rows
        ]

    async def obtener_alumnos_por_asignacion(
        self, usuario_id: UUID
    ) -> list[UUID]:
        """Obtiene los alumnos (entrada_padron.usuario_id) de las materias donde un usuario tiene asignacion."""
        stmt = (
            select(func.distinct(EntradaPadron.usuario_id))
            .select_from(Asignacion)
            .join(VersionPadron, Asignacion.materia_id == VersionPadron.materia_id)
            .join(EntradaPadron, EntradaPadron.version_id == VersionPadron.id)
            .where(
                and_(
                    Asignacion.usuario_id == usuario_id,
                    Asignacion.tenant_id == self.tenant_id,
                    Asignacion.deleted_at.is_(None),
                    Asignacion.materia_id.isnot(None),
                    VersionPadron.activa.is_(True),
                    VersionPadron.deleted_at.is_(None),
                    EntradaPadron.tenant_id == self.tenant_id,
                    EntradaPadron.deleted_at.is_(None),
                    EntradaPadron.usuario_id.isnot(None),
                )
            )
        )
        result = await self.session.scalars(stmt)
        return list(result.all())
