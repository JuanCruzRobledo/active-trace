"""ResultadoEvaluacionRepository — acceso a datos de resultados de evaluacion (C-14).

Soporta upsert para evitar duplicados por (evaluacion_id, alumno_id, tenant_id).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resultado_evaluacion import ResultadoEvaluacion
from app.repositories.base import BaseRepository


class ResultadoEvaluacionRepository(BaseRepository[ResultadoEvaluacion]):
    """Repository de resultados de evaluacion."""

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        super().__init__(session, ResultadoEvaluacion, tenant_id)

    async def upsert(
        self, evaluacion_id: UUID, alumno_id: UUID, nota_final: str
    ) -> ResultadoEvaluacion:
        """Crea o actualiza el resultado de un alumno en una evaluacion.

        Si ya existe un registro para (evaluacion_id, alumno_id), lo actualiza.
        Si no existe, lo crea.

        Args:
            evaluacion_id: UUID de la evaluacion.
            alumno_id: UUID del alumno.
            nota_final: Nota final del alumno.

        Returns:
            ResultadoEvaluacion creado o actualizado.
        """
        existente = await self.buscar_por_alumno(evaluacion_id, alumno_id)
        if existente is not None:
            existente.nota_final = nota_final
            await self.save(existente)
            return existente

        resultado = ResultadoEvaluacion(
            tenant_id=self.tenant_id,
            evaluacion_id=evaluacion_id,
            alumno_id=alumno_id,
            nota_final=nota_final,
        )
        await self.save(resultado)
        return resultado

    async def buscar_por_alumno(
        self, evaluacion_id: UUID, alumno_id: UUID
    ) -> ResultadoEvaluacion | None:
        """Busca el resultado de un alumno en una evaluacion.

        Args:
            evaluacion_id: UUID de la evaluacion.
            alumno_id: UUID del alumno.

        Returns:
            ResultadoEvaluacion o None.
        """
        stmt = self._scope_query(
            select(self.model).where(
                and_(
                    self.model.evaluacion_id == evaluacion_id,
                    self.model.alumno_id == alumno_id,
                )
            )
        )
        result = await self.session.scalar(stmt)
        return result

    async def listar_por_evaluacion(
        self, evaluacion_id: UUID
    ) -> list[ResultadoEvaluacion]:
        """Lista todos los resultados de una evaluacion.

        Args:
            evaluacion_id: UUID de la evaluacion.

        Returns:
            Lista de resultados.
        """
        stmt = self._scope_query(
            select(self.model).where(
                self.model.evaluacion_id == evaluacion_id
            )
        ).order_by(self.model.created_at)
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def contar_por_evaluacion(self, evaluacion_id: UUID) -> int:
        """Cuenta resultados registrados en una evaluacion.

        Args:
            evaluacion_id: UUID de la evaluacion.

        Returns:
            Cantidad de resultados.
        """
        from sqlalchemy import func

        stmt = (
            select(func.count())
            .select_from(self.model)
            .where(
                and_(
                    self.model.evaluacion_id == evaluacion_id,
                    self.model.tenant_id == self.tenant_id,
                    self.model.deleted_at.is_(None),
                )
            )
        )
        result = await self.session.scalar(stmt)
        return result or 0
