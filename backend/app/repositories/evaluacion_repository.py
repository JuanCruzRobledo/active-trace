"""EvaluacionRepository — acceso a datos de convocatorias de evaluacion (C-14).

Todas las queries filtran por tenant_id y excluyen registros soft-delete.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evaluacion import Evaluacion
from app.models.reserva_evaluacion import ReservaEvaluacion
from app.repositories.base import BaseRepository


class EvaluacionRepository(BaseRepository[Evaluacion]):
    """Repository de convocatorias de evaluacion con filtros."""

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        super().__init__(session, Evaluacion, tenant_id)
        from app.models.reserva_evaluacion import ReservaEvaluacion

        self._reserva_model = ReservaEvaluacion

    async def listar(
        self,
        materia_id: UUID | None = None,
        cohorte_id: UUID | None = None,
        estado: str | None = None,
    ) -> list[Evaluacion]:
        """Lista convocatorias con filtros opcionales.

        Args:
            materia_id: Filtrar por materia.
            cohorte_id: Filtrar por cohorte.
            estado: Filtrar por estado.

        Returns:
            Lista de evaluaciones activas del tenant.
        """
        stmt = self._scope_query(select(self.model))
        if materia_id is not None:
            stmt = stmt.where(self.model.materia_id == materia_id)
        if cohorte_id is not None:
            stmt = stmt.where(self.model.cohorte_id == cohorte_id)
        if estado is not None:
            stmt = stmt.where(self.model.estado == estado)

        stmt = stmt.order_by(self.model.fecha_inicio.desc())
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def listar_activas(self) -> list[Evaluacion]:
        """Lista todas las convocatorias activas del tenant."""
        stmt = self._scope_query(
            select(self.model).where(self.model.estado == "Activa")
        ).order_by(self.model.fecha_inicio.desc())
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def actualizar(
        self, evaluacion_id: UUID, datos: dict
    ) -> Evaluacion | None:
        """Actualiza parcialmente una convocatoria.

        Args:
            evaluacion_id: UUID de la evaluacion.
            datos: Dict con campos a actualizar.

        Returns:
            Evaluacion actualizada o None si no existe.
        """
        evaluacion = await self.get_by_id(evaluacion_id)
        if evaluacion is None:
            return None
        for key, value in datos.items():
            if hasattr(evaluacion, key):
                setattr(evaluacion, key, value)
        await self.save(evaluacion)
        return evaluacion

    async def cerrar(self, evaluacion_id: UUID) -> Evaluacion | None:
        """Cierra una convocatoria: estado Inactiva + cancela reservas activas.

        Args:
            evaluacion_id: UUID de la evaluacion.

        Returns:
            Evaluacion actualizada o None si no existe.
        """
        evaluacion = await self.get_by_id(evaluacion_id)
        if evaluacion is None:
            return None
        evaluacion.estado = "Inactiva"
        await self.save(evaluacion)

        # Cancelar reservas activas sin resultado
        from app.models.resultado_evaluacion import ResultadoEvaluacion

        # Buscar alumnos con resultado
        subq = (
            select(ResultadoEvaluacion.alumno_id)
            .where(
                and_(
                    ResultadoEvaluacion.evaluacion_id == evaluacion_id,
                    ResultadoEvaluacion.tenant_id == self.tenant_id,
                    ResultadoEvaluacion.deleted_at.is_(None),
                )
            )
        ).subquery()

        # Cancelar reservas activas de alumnos SIN resultado
        stmt = (
            update(ReservaEvaluacion)
            .where(
                and_(
                    ReservaEvaluacion.evaluacion_id == evaluacion_id,
                    ReservaEvaluacion.tenant_id == self.tenant_id,
                    ReservaEvaluacion.estado == "Activa",
                    ReservaEvaluacion.deleted_at.is_(None),
                    ~ReservaEvaluacion.alumno_id.in_(subq),
                )
            )
            .values(estado="Cancelada")
        )
        await self.session.execute(stmt)
        return evaluacion

    async def contar_convocados(self, evaluacion_id: UUID) -> int:
        """Cuenta alumnos importados a una convocatoria (los que tienen reserva).

        Args:
            evaluacion_id: UUID de la evaluacion.

        Returns:
            Cantidad de alumnos distintos con reserva en la convocatoria.
        """
        stmt = (
            select(func.count(func.distinct(self._reserva_model.alumno_id)))
            .select_from(self._reserva_model)
            .where(
                and_(
                    self._reserva_model.evaluacion_id == evaluacion_id,
                    self._reserva_model.tenant_id == self.tenant_id,
                    self._reserva_model.deleted_at.is_(None),
                )
            )
        )
        result = await self.session.scalar(stmt)
        return result or 0

    async def contar_reservas_activas(self, evaluacion_id: UUID) -> int:
        """Cuenta reservas activas de una convocatoria.

        Args:
            evaluacion_id: UUID de la evaluacion.

        Returns:
            Cantidad de reservas activas.
        """
        stmt = (
            select(func.count())
            .select_from(self._reserva_model)
            .where(
                and_(
                    self._reserva_model.evaluacion_id == evaluacion_id,
                    self._reserva_model.tenant_id == self.tenant_id,
                    self._reserva_model.estado == "Activa",
                    self._reserva_model.deleted_at.is_(None),
                )
            )
        )
        result = await self.session.scalar(stmt)
        return result or 0

    async def contar_resultados(self, evaluacion_id: UUID) -> int:
        """Cuenta resultados registrados de una convocatoria.

        Args:
            evaluacion_id: UUID de la evaluacion.

        Returns:
            Cantidad de resultados.
        """
        from app.models.resultado_evaluacion import ResultadoEvaluacion

        stmt = (
            select(func.count())
            .select_from(ResultadoEvaluacion)
            .where(
                and_(
                    ResultadoEvaluacion.evaluacion_id == evaluacion_id,
                    ResultadoEvaluacion.tenant_id == self.tenant_id,
                    ResultadoEvaluacion.deleted_at.is_(None),
                )
            )
        )
        result = await self.session.scalar(stmt)
        return result or 0
