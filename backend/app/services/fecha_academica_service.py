"""FechaAcademicaService — logica de negocio para fechas academicas (C-17).

Gestiona el ciclo completo: crear, listar, obtener, actualizar y eliminar
(soft delete) fechas evaluativas. Incluye generacion de exportacion HTML
para LMS. Toda accion significativa genera un evento de auditoria.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError
from app.models.enums import TipoFechaAcademica
from app.models.fecha_academica import FechaAcademica
from app.repositories.fecha_academica_repository import FechaAcademicaRepository
from app.schemas.fechas_academicas import (
    FechaAcademicaCreate,
    FechaAcademicaUpdate,
)
from app.services.audit_service import (
    ACCION_FECHA_ACADEMICA_CREAR,
    ACCION_FECHA_ACADEMICA_ELIMINAR,
    ACCION_FECHA_ACADEMICA_MODIFICAR,
    AuditService,
)

PERMISO_ESTRUCTURA_GESTIONAR = "estructura:gestionar"


class FechaAcademicaService:
    """Servicio de fechas academicas: CRUD, export LMS."""

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
        self.repo = FechaAcademicaRepository(session, tenant_id)

    def _build_audit_service(self) -> AuditService:
        from app.core.config import Settings  # noqa: PLC0415
        from app.repositories.audit_log_repository import AuditLogRepository  # noqa: PLC0415

        audit_repo = AuditLogRepository(self.session, self.tenant_id)
        return AuditService(audit_log_repo=audit_repo, settings=Settings())

    async def _validar_materia_en_tenant(self, materia_id: UUID) -> None:
        """Verifica que una materia exista y pertenezca al tenant.

        Args:
            materia_id: UUID de la materia a verificar.

        Raises:
            BusinessError: Si la materia no existe en el tenant.
        """
        from app.models.materia import Materia  # noqa: PLC0415

        stmt = select(Materia).where(
            Materia.id == materia_id,
            Materia.tenant_id == self.tenant_id,
            Materia.deleted_at.is_(None),
        )
        result = await self.session.scalar(stmt)
        if result is None:
            raise BusinessError("Materia no encontrada en el tenant")

    async def _validar_cohorte_en_tenant(self, cohorte_id: UUID) -> None:
        """Verifica que una cohorte exista y pertenezca al tenant.

        Args:
            cohorte_id: UUID de la cohorte a verificar.

        Raises:
            BusinessError: Si la cohorte no existe en el tenant.
        """
        from app.models.cohorte import Cohorte  # noqa: PLC0415

        stmt = select(Cohorte).where(
            Cohorte.id == cohorte_id,
            Cohorte.tenant_id == self.tenant_id,
            Cohorte.deleted_at.is_(None),
        )
        result = await self.session.scalar(stmt)
        if result is None:
            raise BusinessError("Cohorte no encontrada en el tenant")

    async def _validar_unicidad(
        self,
        materia_id: UUID,
        cohorte_id: UUID,
        tipo: TipoFechaAcademica,
        numero: int,
        *,
        exclude_id: UUID | None = None,
    ) -> None:
        """Verifica que no exista duplicado (materia, cohorte, tipo, numero).

        Args:
            materia_id: UUID de la materia.
            cohorte_id: UUID de la cohorte.
            tipo: Tipo de fecha academica.
            numero: Numero de instancia.
            exclude_id: Si se provee, excluye este ID de la busqueda
                (util para update).

        Raises:
            BusinessError: Si ya existe una fecha con la misma combinacion.
        """
        existing = await self.repo.list(
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            tipo=tipo,
        )
        for fe in existing:
            if fe.numero == numero:
                if exclude_id is None or fe.id != exclude_id:
                    raise BusinessError(
                        "Ya existe una fecha academica con el mismo tipo "
                        "y numero para esta materia y cohorte"
                    )

    async def _to_response(self, fecha: FechaAcademica) -> dict:
        """Convierte una FechaAcademica a dict de respuesta.

        Args:
            fecha: Instancia de FechaAcademica.

        Returns:
            Dict con datos de la fecha.
        """
        return {
            "id": fecha.id,
            "materia_id": fecha.materia_id,
            "cohorte_id": fecha.cohorte_id,
            "tipo": fecha.tipo.value if hasattr(fecha.tipo, "value") else str(fecha.tipo),
            "numero": fecha.numero,
            "periodo": fecha.periodo,
            "fecha": fecha.fecha,
            "titulo": fecha.titulo,
            "created_at": fecha.created_at,
            "updated_at": fecha.updated_at,
        }

    # ── Crear fecha ───────────────────────────────────────────────────────

    async def crear_fecha(self, datos: FechaAcademicaCreate) -> dict:
        """Crea una nueva fecha academica.

        Args:
            datos: Datos de la fecha a crear.

        Returns:
            FechaAcademicaResponse dict.

        Raises:
            BusinessError: Si la materia/cohorte no existe en el tenant,
                o si ya existe una fecha con el mismo tipo y numero.
        """
        await self._validar_materia_en_tenant(datos.materia_id)
        await self._validar_cohorte_en_tenant(datos.cohorte_id)
        await self._validar_unicidad(
            datos.materia_id, datos.cohorte_id, datos.tipo, datos.numero,
        )

        fecha = FechaAcademica(
            tenant_id=self.tenant_id,
            materia_id=datos.materia_id,
            cohorte_id=datos.cohorte_id,
            tipo=datos.tipo,
            numero=datos.numero,
            periodo=datos.periodo,
            fecha=datos.fecha,
            titulo=datos.titulo,
        )
        await self.repo.create(fecha)

        audit = self._build_audit_service()
        await audit.register(
            accion=ACCION_FECHA_ACADEMICA_CREAR,
            actor_id=self.actor_id,
            tenant_id=self.tenant_id,
            detalle={
                "fecha_id": str(fecha.id),
                "materia_id": str(datos.materia_id),
                "cohorte_id": str(datos.cohorte_id),
                "tipo": str(datos.tipo),
                "numero": datos.numero,
                "periodo": datos.periodo,
            },
            materia_id=datos.materia_id,
            filas_afectadas=1,
        )

        return await self._to_response(fecha)

    # ── Listar fechas ─────────────────────────────────────────────────────

    async def listar_fechas(
        self,
        materia_id: UUID | None = None,
        cohorte_id: UUID | None = None,
        tipo: TipoFechaAcademica | None = None,
        periodo: str | None = None,
    ) -> dict:
        """Lista fechas academicas con filtros combinables.

        Los filtros se aplican como AND. Sin paginacion inicial.
        Resultados ordenados por fecha ASC.

        Args:
            materia_id: Filtrar por materia (opcional).
            cohorte_id: Filtrar por cohorte (opcional).
            tipo: Filtrar por tipo (opcional).
            periodo: Filtrar por periodo (opcional).

        Returns:
            FechaAcademicaListResponse dict.
        """
        fechas = await self.repo.list(
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            tipo=tipo,
            periodo=periodo,
        )
        items = [await self._to_response(f) for f in fechas]
        return {"items": items, "total": len(items)}

    # ── Obtener fecha ─────────────────────────────────────────────────────

    async def obtener_fecha(self, fecha_id: UUID) -> dict:
        """Obtiene el detalle de una fecha academica.

        Args:
            fecha_id: UUID de la fecha.

        Returns:
            FechaAcademicaResponse dict.

        Raises:
            BusinessError: Si la fecha no existe.
        """
        fecha = await self.repo.get_by_id(fecha_id)
        if fecha is None:
            raise BusinessError("Fecha academica no encontrada")
        return await self._to_response(fecha)

    # ── Actualizar fecha ──────────────────────────────────────────────────

    async def actualizar_fecha(
        self, fecha_id: UUID, datos: FechaAcademicaUpdate
    ) -> dict:
        """Actualiza una fecha academica.

        Valida unicidad si cambia tipo/numero.

        Args:
            fecha_id: UUID de la fecha a actualizar.
            datos: Campos a actualizar.

        Returns:
            FechaAcademicaResponse dict.

        Raises:
            BusinessError: Si la fecha no existe o se viola unicidad.
        """
        fecha = await self.repo.get_by_id(fecha_id)
        if fecha is None:
            raise BusinessError("Fecha academica no encontrada")

        # Determinar valores finales para validacion de unicidad
        nuevo_tipo = datos.tipo if datos.tipo is not None else fecha.tipo
        nuevo_numero = datos.numero if datos.numero is not None else fecha.numero

        # Verificar unicidad si cambia tipo o numero
        tipo_cambio = nuevo_tipo != fecha.tipo or nuevo_numero != fecha.numero
        if tipo_cambio:
            await self._validar_unicidad(
                fecha.materia_id,
                fecha.cohorte_id,
                nuevo_tipo,
                nuevo_numero,
                exclude_id=fecha_id,
            )

        update_data: dict[str, object] = {}
        if datos.tipo is not None:
            update_data["tipo"] = datos.tipo
        if datos.numero is not None:
            update_data["numero"] = datos.numero
        if datos.periodo is not None:
            update_data["periodo"] = datos.periodo
        if datos.fecha is not None:
            update_data["fecha"] = datos.fecha
        if datos.titulo is not None:
            update_data["titulo"] = datos.titulo

        if not update_data:
            return await self._to_response(fecha)

        fecha_actualizada = await self.repo.update(fecha_id, update_data)
        if fecha_actualizada is None:
            raise BusinessError("Fecha academica no encontrada")

        # Serializar cambios para el audit log (JSONB no acepta date/enum)
        cambios_serializados: dict[str, object] = {}
        for key, value in update_data.items():
            if isinstance(value, date):
                cambios_serializados[key] = value.isoformat()
            elif hasattr(value, "value"):
                cambios_serializados[key] = str(value.value)
            else:
                cambios_serializados[key] = value  # type: ignore[assignment]

        audit = self._build_audit_service()
        await audit.register(
            accion=ACCION_FECHA_ACADEMICA_MODIFICAR,
            actor_id=self.actor_id,
            tenant_id=self.tenant_id,
            detalle={
                "fecha_id": str(fecha_id),
                "cambios": cambios_serializados,
            },
            materia_id=fecha.materia_id,
            filas_afectadas=1,
        )

        return await self._to_response(fecha_actualizada)

    # ── Eliminar fecha (soft delete) ──────────────────────────────────────

    async def eliminar_fecha(self, fecha_id: UUID) -> None:
        """Elimina (soft delete) una fecha academica.

        Args:
            fecha_id: UUID de la fecha a eliminar.

        Raises:
            BusinessError: Si la fecha no existe.
        """
        fecha = await self.repo.get_by_id(fecha_id)
        if fecha is None:
            raise BusinessError("Fecha academica no encontrada")

        await self.repo.soft_delete(fecha)

        audit = self._build_audit_service()
        await audit.register(
            accion=ACCION_FECHA_ACADEMICA_ELIMINAR,
            actor_id=self.actor_id,
            tenant_id=self.tenant_id,
            detalle={
                "fecha_id": str(fecha_id),
                "materia_id": str(fecha.materia_id),
                "cohorte_id": str(fecha.cohorte_id),
                "tipo": str(fecha.tipo),
                "numero": fecha.numero,
            },
            materia_id=fecha.materia_id,
            filas_afectadas=1,
        )

    # ── Export LMS ────────────────────────────────────────────────────────

    async def generar_lms_export(
        self,
        materia_id: UUID,
        cohorte_id: UUID,
    ) -> dict:
        """Genera un fragmento HTML con las fechas de una materia x cohorte.

        Args:
            materia_id: UUID de la materia.
            cohorte_id: UUID de la cohorte.

        Returns:
            LmsExportResponse dict con contenido_html.
        """
        fechas = await self.repo.list(
            materia_id=materia_id,
            cohorte_id=cohorte_id,
        )

        if not fechas:
            html = "<p>No hay fechas registradas</p>"
        else:
            rows = []
            for f in fechas:
                tipo_str = f.tipo.value if hasattr(f.tipo, "value") else str(f.tipo)
                rows.append(
                    f"<tr>"
                    f"<td>{tipo_str}</td>"
                    f"<td>{f.numero}</td>"
                    f"<td>{f.fecha.isoformat()}</td>"
                    f"<td>{f.titulo}</td>"
                    f"</tr>"
                )
            html = (
                "<table border='1' cellpadding='6' cellspacing='0' "
                "style='border-collapse: collapse; width: 100%;'>"
                "<thead>"
                "<tr style='background-color: #f2f2f2;'>"
                "<th>Tipo</th><th>N°</th><th>Fecha</th><th>Título</th>"
                "</tr>"
                "</thead>"
                "<tbody>"
                f"{''.join(rows)}"
                "</tbody>"
                "</table>"
            )

        return {"contenido_html": html}
