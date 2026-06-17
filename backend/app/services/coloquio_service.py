"""ColoquioService — logica de negocio para evaluaciones y coloquios (C-14).

Gestiona el ciclo completo: creacion de convocatorias, importacion de alumnos,
reserva de turnos con control de cupo atomico, cancelacion, registro de
resultados, cierre de convocatorias, metricas y agenda consolidada.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError
from app.models.evaluacion import Evaluacion
from app.models.reserva_evaluacion import ReservaEvaluacion
from app.repositories.evaluacion_repository import EvaluacionRepository
from app.repositories.reserva_evaluacion_repository import (
    ReservaEvaluacionRepository,
)
from app.repositories.resultado_evaluacion_repository import (
    ResultadoEvaluacionRepository,
)
from app.schemas.coloquios import (
    EvaluacionCreate,
    EvaluacionResponse,
    EvaluacionUpdate,
    ReservaCreate,
    ReservaResponse,
    ResultadoCreate,
    ResultadoResponse,
    ImportarAlumnosRequest,
    ImportarAlumnosResponse,
    MetricasColoquiosResponse,
    AgendaResponse,
    AgendaItemResponse,
)
from app.services.audit_service import AuditService

# ── Audit action codes ─────────────────────────────────────────────────

ACCION_COLOQUIO_CREAR = "COLOQUIO_CREAR"
ACCION_COLOQUIO_IMPORTAR = "COLOQUIO_IMPORTAR"
ACCION_COLOQUIO_RESERVAR = "COLOQUIO_RESERVAR"
ACCION_COLOQUIO_CANCELAR = "COLOQUIO_CANCELAR"
ACCION_COLOQUIO_RESULTADO = "COLOQUIO_RESULTADO"
ACCION_COLOQUIO_CERRAR = "COLOQUIO_CERRAR"


class ColoquioService:
    """Servicio de coloquios: convocatorias, reservas, resultados y metricas."""

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
        self.evaluacion_repo = EvaluacionRepository(session, tenant_id)
        self.reserva_repo = ReservaEvaluacionRepository(session, tenant_id)
        self.resultado_repo = ResultadoEvaluacionRepository(session, tenant_id)

    # ── Helpers ──────────────────────────────────────────────────────────

    def _build_audit_service(self) -> AuditService:
        from app.core.config import Settings
        from app.repositories.audit_log_repository import AuditLogRepository

        audit_repo = AuditLogRepository(self.session, self.tenant_id)
        return AuditService(audit_log_repo=audit_repo, settings=Settings())

    async def _to_evaluacion_response(
        self, evaluacion: Evaluacion
    ) -> dict:
        """Construye respuesta con metricas incluidas."""
        convocados = await self.evaluacion_repo.contar_convocados(evaluacion.id)
        reservas_activas = await self.evaluacion_repo.contar_reservas_activas(evaluacion.id)
        resultados = await self.evaluacion_repo.contar_resultados(evaluacion.id)
        cupo_total = evaluacion.cupos_por_dia * evaluacion.dias_disponibles
        cupos_libres = max(0, cupo_total - reservas_activas)

        return {
            "id": evaluacion.id,
            "materia_id": evaluacion.materia_id,
            "cohorte_id": evaluacion.cohorte_id,
            "tipo": evaluacion.tipo.value if hasattr(evaluacion.tipo, "value") else str(evaluacion.tipo),
            "instancia": evaluacion.instancia,
            "dias_disponibles": evaluacion.dias_disponibles,
            "cupos_por_dia": evaluacion.cupos_por_dia,
            "fecha_inicio": evaluacion.fecha_inicio,
            "fecha_fin": evaluacion.fecha_fin,
            "estado": evaluacion.estado.value if hasattr(evaluacion.estado, "value") else str(evaluacion.estado),
            "created_at": str(evaluacion.created_at) if evaluacion.created_at else None,
            "updated_at": str(evaluacion.updated_at) if evaluacion.updated_at else None,
            "convocados": convocados,
            "reservas_activas": reservas_activas,
            "cupos_libres": cupos_libres,
            "resultados": resultados,
        }

    @staticmethod
    def _to_reserva_response(reserva: ReservaEvaluacion) -> dict:
        return {
            "id": reserva.id,
            "evaluacion_id": reserva.evaluacion_id,
            "alumno_id": reserva.alumno_id,
            "fecha_hora": reserva.fecha_hora,
            "estado": reserva.estado.value if hasattr(reserva.estado, "value") else str(reserva.estado),
            "created_at": str(reserva.created_at) if reserva.created_at else None,
            "updated_at": str(reserva.updated_at) if reserva.updated_at else None,
            "alumno_nombre": None,
            "alumno_email": None,
        }

    # ── Creacion de convocatoria ─────────────────────────────────────────

    async def crear_convocatoria(self, datos: EvaluacionCreate) -> dict:
        """Crea una nueva convocatoria de evaluacion.

        Args:
            datos: Datos de la convocatoria.

        Returns:
            EvaluacionResponse dict.

        Raises:
            BusinessError: Si la materia o cohorte no existen.
        """
        # Validar materia y cohorte existen
        from app.models.materia import Materia
        from app.models.cohorte import Cohorte

        materia = await self.session.get(Materia, datos.materia_id)
        if materia is None:
            raise BusinessError("Materia no encontrada")

        cohorte = await self.session.get(Cohorte, datos.cohorte_id)
        if cohorte is None:
            raise BusinessError("Cohorte no encontrada")

        evaluacion = Evaluacion(
            tenant_id=self.tenant_id,
            materia_id=datos.materia_id,
            cohorte_id=datos.cohorte_id,
            tipo=datos.tipo,
            instancia=datos.instancia,
            dias_disponibles=datos.dias_disponibles,
            cupos_por_dia=datos.cupos_por_dia,
            fecha_inicio=datos.fecha_inicio,
            fecha_fin=datos.fecha_fin,
            estado="Activa",
        )
        await self.evaluacion_repo.save(evaluacion)

        audit = self._build_audit_service()
        await audit.register(
            accion=ACCION_COLOQUIO_CREAR,
            actor_id=self.actor_id,
            tenant_id=self.tenant_id,
            materia_id=datos.materia_id,
            detalle={
                "evaluacion_id": str(evaluacion.id),
                "tipo": datos.tipo,
                "instancia": datos.instancia,
            },
            filas_afectadas=1,
        )

        return await self._to_evaluacion_response(evaluacion)

    # ── Obtener convocatoria por ID ──────────────────────────────────────

    async def obtener_convocatoria(self, evaluacion_id: UUID) -> dict:
        """Obtiene una convocatoria por ID.

        Args:
            evaluacion_id: UUID de la evaluacion.

        Returns:
            EvaluacionResponse dict.

        Raises:
            BusinessError: Si la convocatoria no existe.
        """
        evaluacion = await self.evaluacion_repo.get_by_id(evaluacion_id)
        if evaluacion is None:
            raise BusinessError("Convocatoria no encontrada")
        return await self._to_evaluacion_response(evaluacion)

    # ── Actualizacion de convocatoria ────────────────────────────────────

    async def actualizar_convocatoria(
        self, evaluacion_id: UUID, datos: EvaluacionUpdate
    ) -> dict:
        """Actualiza una convocatoria existente.

        Args:
            evaluacion_id: UUID de la evaluacion.
            datos: Datos a actualizar.

        Returns:
            EvaluacionResponse dict.

        Raises:
            BusinessError: Si la convocatoria no existe.
        """
        evaluacion = await self.evaluacion_repo.get_by_id(evaluacion_id)
        if evaluacion is None:
            raise BusinessError("Convocatoria no encontrada")

        update_data = datos.model_dump(exclude_none=True)
        if not update_data:
            return await self._to_evaluacion_response(evaluacion)

        evaluacion_actualizada = await self.evaluacion_repo.actualizar(
            evaluacion_id, update_data
        )
        if evaluacion_actualizada is None:
            raise BusinessError("Convocatoria no encontrada")

        return await self._to_evaluacion_response(evaluacion_actualizada)

    # ── Importacion de alumnos ───────────────────────────────────────────

    async def importar_alumnos(
        self, evaluacion_id: UUID, datos: ImportarAlumnosRequest
    ) -> ImportarAlumnosResponse:
        """Importa alumnos a una convocatoria creando reservas sin fecha.

        Crea registros de reserva sin fecha_hora como marcadores de "importado".
        Los alumnos ya importados se omiten.

        Args:
            evaluacion_id: UUID de la evaluacion.
            datos: Lista de alumno_ids.

        Returns:
            ImportarAlumnosResponse con conteo de importados y omitidos.

        Raises:
            BusinessError: Si la convocatoria no existe.
        """
        evaluacion = await self.evaluacion_repo.get_by_id(evaluacion_id)
        if evaluacion is None:
            raise BusinessError("Convocatoria no encontrada")

        importados = 0
        omitidos = 0

        for alumno_id in datos.alumno_ids:
            # Verificar si ya existe reserva para este alumno
            existente = await self.reserva_repo.buscar_activa_por_alumno(
                evaluacion_id, alumno_id
            )
            if existente is not None:
                omitidos += 1
                continue

            # Crear reserva sin fecha (solo marca de importado)
            reserva = ReservaEvaluacion(
                tenant_id=self.tenant_id,
                evaluacion_id=evaluacion_id,
                alumno_id=alumno_id,
                fecha_hora=datetime.now(timezone.utc),
                estado="Activa",
            )
            await self.reserva_repo.save(reserva)
            importados += 1

        audit = self._build_audit_service()
        await audit.register(
            accion=ACCION_COLOQUIO_IMPORTAR,
            actor_id=self.actor_id,
            tenant_id=self.tenant_id,
            detalle={
                "evaluacion_id": str(evaluacion_id),
                "importados": importados,
                "omitidos": omitidos,
            },
            filas_afectadas=importados,
        )

        return ImportarAlumnosResponse(importados=importados, omitidos=omitidos)

    # ── Reserva de turno ─────────────────────────────────────────────────

    async def reservar_turno(self, datos: ReservaCreate, alumno_id: UUID) -> dict:
        """Reserva un turno de coloquio con control de cupo atomico.

        Args:
            datos: Datos de la reserva.
            alumno_id: UUID del alumno (desde el token, no del body).

        Returns:
            ReservaResponse dict.

        Raises:
            BusinessError: Si no hay cupo, la convocatoria no existe,
                o el alumno ya tiene reserva.
        """
        try:
            reserva = await self.reserva_repo.crear_con_control_cupo(
                evaluacion_id=datos.evaluacion_id,
                alumno_id=alumno_id,
                fecha_hora=datos.fecha_hora,
            )
        except ValueError as exc:
            raise BusinessError(str(exc)) from exc

        if reserva is None:
            # Verificar si la evaluacion existe (el repo devuelve None si no existe)
            evaluacion = await self.evaluacion_repo.get_by_id(datos.evaluacion_id)
            if evaluacion is None:
                raise BusinessError("Convocatoria no encontrada")
            raise BusinessError("No hay cupo disponible para esta convocatoria")

        audit = self._build_audit_service()
        await audit.register(
            accion=ACCION_COLOQUIO_RESERVAR,
            actor_id=self.actor_id,
            tenant_id=self.tenant_id,
            detalle={
                "evaluacion_id": str(datos.evaluacion_id),
                "reserva_id": str(reserva.id),
            },
            filas_afectadas=1,
        )

        return self._to_reserva_response(reserva)

    # ── Cancelacion de reserva ───────────────────────────────────────────

    async def cancelar_reserva(self, reserva_id: UUID) -> dict:
        """Cancela una reserva propia del alumno autenticado.

        Args:
            reserva_id: UUID de la reserva.

        Returns:
            ReservaResponse dict.

        Raises:
            BusinessError: Si la reserva no existe o no pertenece al alumno.
        """
        reserva = await self.reserva_repo.cancelar(reserva_id, self.actor_id)
        if reserva is None:
            raise BusinessError("Reserva no encontrada o no le pertenece")

        audit = self._build_audit_service()
        await audit.register(
            accion=ACCION_COLOQUIO_CANCELAR,
            actor_id=self.actor_id,
            tenant_id=self.tenant_id,
            detalle={
                "reserva_id": str(reserva_id),
                "evaluacion_id": str(reserva.evaluacion_id),
            },
            filas_afectadas=1,
        )

        return self._to_reserva_response(reserva)

    # ── Registro de resultado ────────────────────────────────────────────

    async def registrar_resultado(self, datos: ResultadoCreate) -> dict:
        """Registra o actualiza el resultado de un alumno.

        Args:
            datos: Datos del resultado.

        Returns:
            ResultadoResponse dict.

        Raises:
            BusinessError: Si la evaluacion no existe.
        """
        evaluacion = await self.evaluacion_repo.get_by_id(datos.evaluacion_id)
        if evaluacion is None:
            raise BusinessError("Convocatoria no encontrada")

        resultado = await self.resultado_repo.upsert(
            evaluacion_id=datos.evaluacion_id,
            alumno_id=datos.alumno_id,
            nota_final=datos.nota_final,
        )

        audit = self._build_audit_service()
        await audit.register(
            accion=ACCION_COLOQUIO_RESULTADO,
            actor_id=self.actor_id,
            tenant_id=self.tenant_id,
            detalle={
                "evaluacion_id": str(datos.evaluacion_id),
                "alumno_id": str(datos.alumno_id),
                "nota_final": datos.nota_final,
            },
            filas_afectadas=1,
        )

        return {
            "id": resultado.id,
            "evaluacion_id": resultado.evaluacion_id,
            "alumno_id": resultado.alumno_id,
            "nota_final": resultado.nota_final,
            "created_at": str(resultado.created_at) if resultado.created_at else None,
            "updated_at": str(resultado.updated_at) if resultado.updated_at else None,
        }

    # ── Cierre de convocatoria ───────────────────────────────────────────

    async def cerrar_convocatoria(self, evaluacion_id: UUID) -> dict:
        """Cierra una convocatoria: estado Inactiva + cancela reservas activas sin resultado.

        Args:
            evaluacion_id: UUID de la evaluacion.

        Returns:
            EvaluacionResponse dict.

        Raises:
            BusinessError: Si la convocatoria no existe o ya esta cerrada.
        """
        evaluacion = await self.evaluacion_repo.get_by_id(evaluacion_id)
        if evaluacion is None:
            raise BusinessError("Convocatoria no encontrada")
        if evaluacion.estado != "Activa":
            raise BusinessError("La convocatoria ya esta cerrada")

        evaluacion = await self.evaluacion_repo.cerrar(evaluacion_id)
        if evaluacion is None:
            raise BusinessError("Convocatoria no encontrada")

        audit = self._build_audit_service()
        await audit.register(
            accion=ACCION_COLOQUIO_CERRAR,
            actor_id=self.actor_id,
            tenant_id=self.tenant_id,
            detalle={
                "evaluacion_id": str(evaluacion_id),
            },
            filas_afectadas=1,
        )

        return await self._to_evaluacion_response(evaluacion)

    # ── Listados ─────────────────────────────────────────────────────────

    async def listar_convocatorias(
        self,
        materia_id: UUID | None = None,
        cohorte_id: UUID | None = None,
        estado: str | None = None,
    ) -> dict:
        """Lista convocatorias con filtros.

        Returns:
            Dict con items y total.
        """
        evaluaciones = await self.evaluacion_repo.listar(
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            estado=estado,
        )
        items = []
        for ev in evaluaciones:
            items.append(await self._to_evaluacion_response(ev))
        return {"items": items, "total": len(items)}

    # ── Metricas ─────────────────────────────────────────────────────────

    async def obtener_metricas(self) -> MetricasColoquiosResponse:
        """Obtiene metricas globales del modulo de coloquios.

        Returns:
            MetricasColoquiosResponse con totales.
        """
        evaluaciones = await self.evaluacion_repo.listar()
        total_convocatorias = len(evaluaciones)

        total_alumnos = 0
        reservas_activas = 0
        resultados = 0

        for ev in evaluaciones:
            total_alumnos += await self.evaluacion_repo.contar_convocados(ev.id)
            reservas_activas += await self.evaluacion_repo.contar_reservas_activas(ev.id)
            resultados += await self.evaluacion_repo.contar_resultados(ev.id)

        return MetricasColoquiosResponse(
            total_convocatorias=total_convocatorias,
            total_alumnos_importados=total_alumnos,
            reservas_activas=reservas_activas,
            resultados_registrados=resultados,
        )

    # ── Agenda ──────────────────────────────────────────────────────────

    async def obtener_agenda(
        self, evaluacion_id: UUID | None = None
    ) -> AgendaResponse:
        """Obtiene la agenda consolidada de reservas activas.

        Args:
            evaluacion_id: Filtrar por evaluacion (opcional).

        Returns:
            AgendaResponse con items y total.
        """
        items_data = await self.reserva_repo.listar_agenda(
            evaluacion_id=evaluacion_id
        )

        items = []
        for r in items_data:
            items.append(
                AgendaItemResponse(
                    id=r.id,
                    evaluacion_id=r.evaluacion_id,
                    alumno_id=r.alumno_id,
                    fecha_hora=r.fecha_hora,
                    estado=r.estado,
                    alumno_nombre=r.alumno_nombre,
                    materia_nombre=r.materia_nombre,
                    cohorte_nombre=r.cohorte_nombre,
                    instancia=r.instancia,
                )
            )

        return AgendaResponse(items=items, total=len(items))

    # ── Listado de reservas del alumno ───────────────────────────────────

    async def listar_mis_reservas(self) -> dict:
        """Lista las reservas del alumno autenticado.

        Returns:
            Dict con items y total.
        """
        reservas = await self.reserva_repo.listar_por_alumno(self.actor_id)
        items = [self._to_reserva_response(r) for r in reservas]

        # Poblar nombre/email del alumno desde tabla usuario
        # El ORM desencripta automaticamente EncryptedColumn
        if reservas and items:
            from sqlalchemy import select

            from app.models.usuario import Usuario

            result = await self.session.execute(
                select(Usuario.nombre, Usuario.apellidos, Usuario.email).where(
                    Usuario.id == self.actor_id
                )
            )
            row = result.one_or_none()
            if row:
                nombre_completo = f"{row.nombre} {row.apellidos}".strip()
                for item in items:
                    item["alumno_nombre"] = nombre_completo
                    item["alumno_email"] = row.email

        return {"items": items, "total": len(items)}
