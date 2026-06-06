"""AuditoriaService — panel de auditoría y métricas (C-19).

Consulta datos existentes de ``AuditLog``, ``Comunicacion`` y ``Asignacion``
con agregaciones SQL. No escribe ni modifica registros — solo lectura.

Dependencias:
    - ``AuditLog`` (C-05): registro append-only de acciones.
    - ``Comunicacion`` (C-12): comunicaciones con ciclo de estados.
    - ``Asignacion`` (C-07): asignaciones para scope propio de COORDINADOR.
    - ``Usuario`` / ``Materia``: joins para nombres legibles.
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Select, String, cast, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asignacion import Asignacion
from app.models.audit_log import AuditLog
from app.models.comunicacion import Comunicacion, EstadoComunicacion
from app.models.materia import Materia
from app.models.usuario import Usuario


class AuditoriaService:
    """Servicio de consultas agregadas para el panel de auditoría.

    Args:
        session: Sesión async de SQLAlchemy.
        tenant_id: UUID del tenant — filtra todas las queries.
    """

    def __init__(
        self,
        session: AsyncSession,
        tenant_id: UUID,
    ) -> None:
        self.session = session
        self.tenant_id = tenant_id

    # ── Helpers ──────────────────────────────────────────────────────

    def _filtros_base_audit(self, stmt: Select) -> Select:
        """Aplica filtro de tenant a queries sobre AuditLog."""
        return stmt.where(AuditLog.tenant_id == self.tenant_id)

    def _filtros_audit(
        self,
        stmt: Select,
        *,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
        materia_id: UUID | None = None,
    ) -> Select:
        """Aplica filtros combinables opcionales a queries de AuditLog."""
        if fecha_desde is not None:
            stmt = stmt.where(AuditLog.fecha_hora >= datetime.combine(fecha_desde, datetime.min.time()))
        if fecha_hasta is not None:
            stmt = stmt.where(AuditLog.fecha_hora <= datetime.combine(fecha_hasta, datetime.max.time()))
        if materia_id is not None:
            stmt = stmt.where(AuditLog.materia_id == materia_id)
        return stmt

    async def _scope_materias(
        self,
        usuario_id: UUID,
        roles: list[str],
    ) -> list[UUID] | None:
        """Retorna materia_ids si COORDINADOR (scope propio), None si ADMIN.

        Args:
            usuario_id: UUID del usuario a verificar.
            roles: Lista de roles del usuario.

        Returns:
            Lista de UUIDs de materias si el rol es COORDINADOR,
            None si es ADMIN (sin restricción de scope).
        """
        if "ADMIN" in roles:
            return None

        if "COORDINADOR" in roles:
            stmt = select(Asignacion.materia_id).where(
                Asignacion.tenant_id == self.tenant_id,
                Asignacion.usuario_id == usuario_id,
                Asignacion.rol == "COORDINADOR",
                Asignacion.deleted_at.is_(None),
                Asignacion.materia_id.isnot(None),
            )
            result = await self.session.scalars(stmt)
            materias = list(result.all())
            return materias if materias else [UUID(int=0)]  # dummy UUID si vacío

        return None

    def _aplicar_scope_materias(
        self,
        stmt: Select,
        col_materia_id,
        scope_materias: list[UUID] | None,
    ) -> Select:
        """Aplica filtro de scope propio a una query, si corresponde.

        Args:
            stmt: Query SQLAlchemy a modificar.
            col_materia_id: Columna de materia_id a filtrar.
            scope_materias: Lista de materia_ids permitidos, o None si sin restricción.

        Returns:
            Query con filtro de scope aplicado (si corresponde).
        """
        if scope_materias is not None:
            stmt = stmt.where(col_materia_id.in_(scope_materias))
        return stmt

    # ── Panel de interacciones (F9.1) ───────────────────────────────

    async def acciones_por_dia(
        self,
        *,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
        materia_id: UUID | None = None,
        scope_materias: list[UUID] | None = None,
    ) -> list[dict]:
        """Agregación de acciones por día.

        Returns:
            Lista de dicts con ``fecha`` (date) y ``total`` (int).
        """
        stmt = self._filtros_base_audit(
            select(
                func.date_trunc("day", AuditLog.fecha_hora).label("fecha"),
                func.count().label("total"),
            )
        )
        stmt = self._filtros_audit(
            stmt,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            materia_id=materia_id,
        )
        stmt = self._aplicar_scope_materias(stmt, AuditLog.materia_id, scope_materias)
        stmt = stmt.group_by(text("fecha"))
        stmt = stmt.order_by(text("fecha DESC"))

        result = await self.session.execute(stmt)
        rows = result.all()
        return [
            {"fecha": row.fecha.date() if hasattr(row.fecha, "date") else row.fecha,
             "total": row.total}
            for row in rows
        ]

    async def comunicaciones_por_docente(
        self,
        *,
        materia_id: UUID | None = None,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
        scope_materias: list[UUID] | None = None,
    ) -> list[dict]:
        """Distribución de estados de comunicación por docente.

        Returns:
            Lista de dicts con ``usuario_id``, ``nombre`` y conteo por estado.
        """
        estado_col = cast(Comunicacion.estado, String)
        stmt = (
            select(
                Comunicacion.enviado_por_id.label("usuario_id"),
                Usuario.nombre,
                func.count().filter(estado_col == EstadoComunicacion.Pendiente).label("Pendiente"),
                func.count().filter(estado_col == EstadoComunicacion.Enviando).label("Enviando"),
                func.count().filter(estado_col == EstadoComunicacion.Enviado).label("OK"),
                func.count().filter(estado_col == EstadoComunicacion.Error).label("Fallido"),
                func.count().filter(estado_col == EstadoComunicacion.Cancelado).label("Cancelado"),
            )
            .join(Usuario, Comunicacion.enviado_por_id == Usuario.id)
            .where(
                Comunicacion.tenant_id == self.tenant_id,
                Comunicacion.deleted_at.is_(None),
                Usuario.deleted_at.is_(None),
            )
            .group_by(Comunicacion.enviado_por_id, Usuario.nombre)
        )
        if materia_id is not None:
            stmt = stmt.where(Comunicacion.materia_id == materia_id)
        if fecha_desde is not None:
            stmt = stmt.where(Comunicacion.created_at >= fecha_desde)
        if fecha_hasta is not None:
            stmt = stmt.where(Comunicacion.created_at <= datetime.combine(fecha_hasta, datetime.max.time()))
        stmt = self._aplicar_scope_materias(stmt, Comunicacion.materia_id, scope_materias)
        stmt = stmt.order_by(Usuario.nombre)

        result = await self.session.execute(stmt)
        rows = result.all()
        return [
            {
                "usuario_id": row.usuario_id,
                "nombre": row.nombre,
                "Pendiente": row.Pendiente,
                "Enviando": row.Enviando,
                "OK": row.OK,
                "Fallido": row.Fallido,
                "Cancelado": row.Cancelado,
            }
            for row in rows
        ]

    async def interacciones_por_docente_materia(
        self,
        *,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
        scope_materias: list[UUID] | None = None,
    ) -> list[dict]:
        """Agregación de interacciones (audit_log) por docente × materia.

        Returns:
            Lista de dicts con datos del docente, materia y desglose por acción.
        """
        stmt = (
            select(
                AuditLog.actor_id.label("usuario_id"),
                Usuario.nombre,
                AuditLog.materia_id,
                Materia.nombre.label("materia_nombre"),
                AuditLog.accion,
                func.count().label("cnt"),
            )
            .join(Usuario, AuditLog.actor_id == Usuario.auth_user_id)
            .join(Materia, AuditLog.materia_id == Materia.id)
            .where(
                AuditLog.tenant_id == self.tenant_id,
                Usuario.deleted_at.is_(None),
                Materia.deleted_at.is_(None),
                AuditLog.materia_id.isnot(None),
            )
        )
        stmt = self._filtros_audit(
            stmt,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
        )
        stmt = self._aplicar_scope_materias(stmt, AuditLog.materia_id, scope_materias)
        stmt = stmt.group_by(
            AuditLog.actor_id, Usuario.nombre,
            AuditLog.materia_id, Materia.nombre,
            AuditLog.accion,
        )
        stmt = stmt.order_by(Usuario.nombre, Materia.nombre)

        result = await self.session.execute(stmt)
        rows = result.all()

        # Agrupar por (usuario_id, nombre, materia_id, materia_nombre)
        grouped: dict[tuple, dict] = {}
        for row in rows:
            key = (row.usuario_id, row.nombre, row.materia_id, row.materia_nombre)
            if key not in grouped:
                grouped[key] = {
                    "usuario_id": row.usuario_id,
                    "nombre": row.nombre,
                    "materia_id": row.materia_id,
                    "materia_nombre": row.materia_nombre,
                    "acciones": {},
                    "total": 0,
                }
            grouped[key]["acciones"][row.accion] = row.cnt
            grouped[key]["total"] += row.cnt

        return list(grouped.values())

    async def ultimas_acciones(
        self,
        *,
        limit: int = 200,
        scope_materias: list[UUID] | None = None,
    ) -> list[dict]:
        """Últimas acciones registradas, con límite configurable.

        Args:
            limit: Cantidad máxima de registros (default 200, techo duro 1000).

        Returns:
            Lista de dicts con id, fecha_hora, actor_nombre, accion,
            materia_nombre, detalle, ip.
        """
        if limit > 1000:
            limit = 1000

        stmt = (
            select(
                AuditLog.id,
                AuditLog.fecha_hora,
                Usuario.nombre.label("actor_nombre"),
                AuditLog.accion,
                Materia.nombre.label("materia_nombre"),
                AuditLog.detalle,
                AuditLog.ip,
            )
            .join(Usuario, AuditLog.actor_id == Usuario.auth_user_id)
            .outerjoin(Materia, AuditLog.materia_id == Materia.id)
            .where(
                AuditLog.tenant_id == self.tenant_id,
                Usuario.deleted_at.is_(None),
            )
        )
        # Materia puede ser NULL; outerjoin + filtro condicional
        # Usamos outerjoin así que no filtramos Materia.deleted_at
        stmt = self._aplicar_scope_materias(stmt, AuditLog.materia_id, scope_materias)
        stmt = stmt.order_by(AuditLog.fecha_hora.desc())
        stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        rows = result.all()
        return [
            {
                "id": row.id,
                "fecha_hora": row.fecha_hora,
                "actor_nombre": row.actor_nombre,
                "accion": row.accion,
                "materia_nombre": row.materia_nombre,
                "detalle": row.detalle,
                "ip": row.ip,
            }
            for row in rows
        ]

    # ── Log completo de auditoría (F9.2) ─────────────────────────────

    async def log_completo(
        self,
        *,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
        materia_id: UUID | None = None,
        usuario_id: UUID | None = None,
        accion: str | None = None,
        offset: int = 0,
        limit: int = 50,
        scope_materias: list[UUID] | None = None,
    ) -> dict:
        """Log completo de auditoría paginado y filtrable.

        Args:
            offset: Desplazamiento para paginación (default 0).
            limit: Máximo de registros (default 50).

        Returns:
            Dict con ``items`` (list[dict]), ``total`` (int), ``offset``, ``limit``.
        """
        # ── Query de datos ──
        stmt = (
            select(
                AuditLog.id,
                AuditLog.fecha_hora,
                AuditLog.actor_id,
                Usuario.nombre.label("actor_nombre"),
                AuditLog.materia_id,
                Materia.nombre.label("materia_nombre"),
                AuditLog.accion,
                AuditLog.detalle,
                AuditLog.filas_afectadas,
                AuditLog.ip,
                AuditLog.user_agent,
            )
            .join(Usuario, AuditLog.actor_id == Usuario.auth_user_id)
            .outerjoin(Materia, AuditLog.materia_id == Materia.id)
            .where(
                AuditLog.tenant_id == self.tenant_id,
                Usuario.deleted_at.is_(None),
            )
        )

        # Filtros combinables
        if fecha_desde is not None:
            stmt = stmt.where(AuditLog.fecha_hora >= datetime.combine(fecha_desde, datetime.min.time()))
        if fecha_hasta is not None:
            stmt = stmt.where(AuditLog.fecha_hora <= datetime.combine(fecha_hasta, datetime.max.time()))
        if materia_id is not None:
            stmt = stmt.where(AuditLog.materia_id == materia_id)
        if usuario_id is not None:
            stmt = stmt.where(AuditLog.actor_id == usuario_id)
        if accion is not None:
            stmt = stmt.where(AuditLog.accion == accion)

        stmt = self._aplicar_scope_materias(stmt, AuditLog.materia_id, scope_materias)
        stmt = stmt.order_by(AuditLog.fecha_hora.desc())
        stmt = stmt.offset(offset).limit(limit)

        # ── Query de conteo total ──
        count_stmt = select(func.count(AuditLog.id)).where(
            AuditLog.tenant_id == self.tenant_id,
        )
        if fecha_desde is not None:
            count_stmt = count_stmt.where(AuditLog.fecha_hora >= datetime.combine(fecha_desde, datetime.min.time()))
        if fecha_hasta is not None:
            count_stmt = count_stmt.where(AuditLog.fecha_hora <= datetime.combine(fecha_hasta, datetime.max.time()))
        if materia_id is not None:
            count_stmt = count_stmt.where(AuditLog.materia_id == materia_id)
        if usuario_id is not None:
            count_stmt = count_stmt.where(AuditLog.actor_id == usuario_id)
        if accion is not None:
            count_stmt = count_stmt.where(AuditLog.accion == accion)
        count_stmt = self._aplicar_scope_materias(count_stmt, AuditLog.materia_id, scope_materias)

        result = await self.session.execute(stmt)
        total_result = await self.session.scalar(count_stmt)

        rows = result.all()
        items = [
            {
                "id": row.id,
                "fecha_hora": row.fecha_hora,
                "actor_id": row.actor_id,
                "actor_nombre": row.actor_nombre,
                "materia_id": row.materia_id,
                "materia_nombre": row.materia_nombre,
                "accion": row.accion,
                "detalle": row.detalle,
                "filas_afectadas": row.filas_afectadas,
                "ip": row.ip,
                "user_agent": row.user_agent,
            }
            for row in rows
        ]

        return {
            "items": items,
            "total": total_result or 0,
            "offset": offset,
            "limit": limit,
        }
