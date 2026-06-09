"""ReservaEvaluacionRepository — acceso a datos de reservas de evaluacion (C-14).

Incluye control de cupo atomico: al crear una reserva se verifica que el cupo
total (cupos_por_dia * dias_disponibles) no haya sido superado por las reservas
activas existentes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.cohorte import Cohorte
from app.models.evaluacion import Evaluacion
from app.models.materia import Materia
from app.models.reserva_evaluacion import ReservaEvaluacion
from app.models.usuario import Usuario
from app.repositories.base import BaseRepository


@dataclass
class AgendaItem:
    """Item de agenda con datos de las tablas relacionadas."""

    id: UUID
    evaluacion_id: UUID
    alumno_id: UUID
    fecha_hora: datetime
    estado: str
    alumno_nombre: str | None = None
    materia_nombre: str | None = None
    cohorte_nombre: str | None = None
    instancia: str | None = None


class ReservaEvaluacionRepository(BaseRepository[ReservaEvaluacion]):
    """Repository de reservas de evaluacion con control de cupo."""

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        super().__init__(session, ReservaEvaluacion, tenant_id)

    async def crear_con_control_cupo(
        self, evaluacion_id: UUID, alumno_id: UUID, fecha_hora: datetime
    ) -> ReservaEvaluacion | None:
        """Crea una reserva si hay cupo disponible (operacion atomica).

        Usa SELECT ... FOR UPDATE sobre la evaluacion para evitar condicion
        de carrera en la verificacion de cupo.

        Args:
            evaluacion_id: UUID de la evaluacion.
            alumno_id: UUID del alumno.
            fecha_hora: Fecha y hora de la reserva.

        Returns:
            ReservaEvaluacion creada o None si no hay cupo.

        Raises:
            ValueError: Si el alumno ya tiene una reserva activa en esta evaluacion.
        """
        # Verificar que el alumno no tenga ya una reserva activa
        reserva_existente = await self.buscar_activa_por_alumno(
            evaluacion_id, alumno_id
        )
        if reserva_existente is not None:
            raise ValueError("El alumno ya tiene una reserva activa en esta evaluacion")

        # Obtener evaluacion con lock
        stmt = (
            select(Evaluacion)
            .where(
                and_(
                    Evaluacion.id == evaluacion_id,
                    Evaluacion.tenant_id == self.tenant_id,
                    Evaluacion.deleted_at.is_(None),
                )
            )
            .with_for_update()
        )
        result = await self.session.scalar(stmt)
        if result is None:
            return None

        evaluacion: Evaluacion = result
        if evaluacion.estado != "Activa":
            raise ValueError("La convocatoria no esta activa")

        # Verificar cupo total
        cupo_total = evaluacion.cupos_por_dia * evaluacion.dias_disponibles
        reservas_activas = await self.contar_activas_por_evaluacion(evaluacion_id)
        if reservas_activas >= cupo_total:
            return None  # Sin cupo

        # Crear reserva
        reserva = ReservaEvaluacion(
            tenant_id=self.tenant_id,
            evaluacion_id=evaluacion_id,
            alumno_id=alumno_id,
            fecha_hora=fecha_hora,
            estado="Activa",
        )
        await self.save(reserva)
        return reserva

    async def cancelar(self, reserva_id: UUID, alumno_id: UUID) -> ReservaEvaluacion | None:
        """Cancela una reserva verificando pertenencia.

        Args:
            reserva_id: UUID de la reserva.
            alumno_id: UUID del alumno (debe coincidir).

        Returns:
            ReservaEvaluacion cancelada o None si no existe.
        """
        reserva = await self.get_by_id(reserva_id)
        if reserva is None:
            return None
        if reserva.alumno_id != alumno_id:
            return None
        reserva.estado = "Cancelada"
        await self.save(reserva)
        return reserva

    async def buscar_activa_por_alumno(
        self, evaluacion_id: UUID, alumno_id: UUID
    ) -> ReservaEvaluacion | None:
        """Busca una reserva activa de un alumno en una evaluacion.

        Args:
            evaluacion_id: UUID de la evaluacion.
            alumno_id: UUID del alumno.

        Returns:
            ReservaEvaluacion o None.
        """
        stmt = self._scope_query(
            select(self.model).where(
                and_(
                    self.model.evaluacion_id == evaluacion_id,
                    self.model.alumno_id == alumno_id,
                    self.model.estado == "Activa",
                )
            )
        )
        result = await self.session.scalar(stmt)
        return result

    async def listar_por_evaluacion(
        self, evaluacion_id: UUID, solo_activas: bool = True
    ) -> list[ReservaEvaluacion]:
        """Lista reservas de una evaluacion.

        Args:
            evaluacion_id: UUID de la evaluacion.
            solo_activas: Si True, solo reservas activas.

        Returns:
            Lista de reservas.
        """
        conditions = [self.model.evaluacion_id == evaluacion_id]
        if solo_activas:
            conditions.append(self.model.estado == "Activa")

        stmt = self._scope_query(
            select(self.model).where(and_(*conditions))
        ).order_by(self.model.fecha_hora)
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def listar_por_alumno(
        self, alumno_id: UUID
    ) -> list[ReservaEvaluacion]:
        """Lista reservas de un alumno.

        Args:
            alumno_id: UUID del alumno.

        Returns:
            Lista de reservas del alumno.
        """
        stmt = self._scope_query(
            select(self.model).where(self.model.alumno_id == alumno_id)
        ).order_by(self.model.fecha_hora.desc())
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def contar_activas_por_evaluacion(self, evaluacion_id: UUID) -> int:
        """Cuenta reservas activas de una evaluacion.

        Args:
            evaluacion_id: UUID de la evaluacion.

        Returns:
            Cantidad de reservas activas.
        """
        stmt = (
            select(func.count())
            .select_from(self.model)
            .where(
                and_(
                    self.model.evaluacion_id == evaluacion_id,
                    self.model.estado == "Activa",
                    self.model.tenant_id == self.tenant_id,
                    self.model.deleted_at.is_(None),
                )
            )
        )
        result = await self.session.scalar(stmt)
        return result or 0

    async def listar_agenda(
        self, evaluacion_id: UUID | None = None
    ) -> list[AgendaItem]:
        """Lista reservas activas con datos de tablas relacionadas.

        Hace JOIN con evaluacion, materia, cohorte y usuario para poblar
        los nombres en la agenda consolidada.

        Args:
            evaluacion_id: Filtrar por evaluacion (opcional).

        Returns:
            Lista de AgendaItem con datos completos.
        """
        conditions = [self.model.estado == "Activa"]
        if evaluacion_id is not None:
            conditions.append(self.model.evaluacion_id == evaluacion_id)

        stmt = (
            select(
                self.model.id,
                self.model.evaluacion_id,
                self.model.alumno_id,
                self.model.fecha_hora,
                self.model.estado,
                Usuario.nombre,
                Usuario.apellidos,
                Materia.nombre.label("materia_nombre"),
                Cohorte.nombre.label("cohorte_nombre"),
                Evaluacion.instancia,
            )
            .join(Evaluacion, self.model.evaluacion_id == Evaluacion.id)
            .join(Usuario, self.model.alumno_id == Usuario.id)
            .join(Materia, Evaluacion.materia_id == Materia.id)
            .join(Cohorte, Evaluacion.cohorte_id == Cohorte.id)
            .where(
                and_(
                    *conditions,
                    self.model.deleted_at.is_(None),
                    Evaluacion.deleted_at.is_(None),
                    Usuario.deleted_at.is_(None),
                )
            )
            .order_by(self.model.fecha_hora)
        )
        # Aplicar scope de tenant
        stmt = self._scope_query(stmt)
        rows = await self.session.execute(stmt)
        items = []
        for row in rows:
            nombre = f"{row.nombre} {row.apellidos}" if row.nombre else None
            items.append(
                AgendaItem(
                    id=row.id,
                    evaluacion_id=row.evaluacion_id,
                    alumno_id=row.alumno_id,
                    fecha_hora=row.fecha_hora,
                    estado=row.estado.value
                    if hasattr(row.estado, "value")
                    else str(row.estado),
                    alumno_nombre=nombre,
                    materia_nombre=row.materia_nombre,
                    cohorte_nombre=row.cohorte_nombre,
                    instancia=row.instancia,
                )
            )
        return items
