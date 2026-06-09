"""ProgramaService — logica de negocio para programas de materia (C-17).

Gestiona el ciclo completo: subir programa, listar, obtener detalle y
eliminar (hard delete). Toda accion significativa genera un evento de
auditoria.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError
from app.models.programa_materia import ProgramaMateria
from app.repositories.programa_repository import ProgramaMateriaRepository
from app.schemas.programas import (
    ProgramaMateriaCreate,
    ProgramaMateriaListItem,
    ProgramaMateriaResponse,
)
from app.services.audit_service import (
    ACCION_PROGRAMA_ELIMINAR,
    ACCION_PROGRAMA_SUBIR,
    AuditService,
)

PERMISO_ESTRUCTURA_GESTIONAR = "estructura:gestionar"


class ProgramaService:
    """Servicio de programas de materia: subir, listar, obtener, eliminar."""

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
        self.repo = ProgramaMateriaRepository(session, tenant_id)

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

    async def _validar_carrera_en_tenant(self, carrera_id: UUID) -> None:
        """Verifica que una carrera exista y pertenezca al tenant.

        Args:
            carrera_id: UUID de la carrera a verificar.

        Raises:
            BusinessError: Si la carrera no existe en el tenant.
        """
        from app.models.carrera import Carrera  # noqa: PLC0415

        stmt = select(Carrera).where(
            Carrera.id == carrera_id,
            Carrera.tenant_id == self.tenant_id,
            Carrera.deleted_at.is_(None),
        )
        result = await self.session.scalar(stmt)
        if result is None:
            raise BusinessError("Carrera no encontrada en el tenant")

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

    async def _to_response(self, programa: ProgramaMateria) -> dict:
        """Convierte un ProgramaMateria a dict de respuesta completo.

        Args:
            programa: Instancia de ProgramaMateria.

        Returns:
            Dict con datos completos (incluye referencia_archivo).
        """
        return {
            "id": programa.id,
            "titulo": programa.titulo,
            "materia_id": programa.materia_id,
            "carrera_id": programa.carrera_id,
            "cohorte_id": programa.cohorte_id,
            "referencia_archivo": programa.referencia_archivo,
            "cargado_at": programa.cargado_at,
            "created_at": programa.created_at,
            "updated_at": programa.updated_at,
        }

    async def _to_list_item(self, programa: ProgramaMateria) -> dict:
        """Convierte un ProgramaMateria a dict de item de lista.

        Args:
            programa: Instancia de ProgramaMateria.

        Returns:
            Dict con datos basicos (sin referencia_archivo).
        """
        return {
            "id": programa.id,
            "titulo": programa.titulo,
            "materia_id": programa.materia_id,
            "carrera_id": programa.carrera_id,
            "cohorte_id": programa.cohorte_id,
            "cargado_at": programa.cargado_at,
            "created_at": programa.created_at,
        }

    # ── Subir programa ────────────────────────────────────────────────────

    async def subir_programa(self, datos: ProgramaMateriaCreate) -> dict:
        """Sube un nuevo programa de materia.

        Args:
            datos: Datos del programa a crear.

        Returns:
            ProgramaMateriaResponse dict.

        Raises:
            BusinessError: Si la materia/carrera/cohorte no existe en el
                tenant, o si ya existe un programa para la misma combinacion.
        """
        await self._validar_materia_en_tenant(datos.materia_id)
        await self._validar_carrera_en_tenant(datos.carrera_id)
        await self._validar_cohorte_en_tenant(datos.cohorte_id)

        # Verificar unicidad: misma materia x carrera x cohorte
        existing = await self.repo.list(
            materia_id=datos.materia_id,
            carrera_id=datos.carrera_id,
            cohorte_id=datos.cohorte_id,
        )
        if existing:
            raise BusinessError(
                "Ya existe un programa para esta combinacion de materia, "
                "carrera y cohorte"
            )

        ahora = datetime.now(timezone.utc)
        programa = ProgramaMateria(
            tenant_id=self.tenant_id,
            materia_id=datos.materia_id,
            carrera_id=datos.carrera_id,
            cohorte_id=datos.cohorte_id,
            titulo=datos.titulo,
            referencia_archivo=datos.referencia_archivo,
            cargado_at=ahora,
        )
        await self.repo.create(programa)

        audit = self._build_audit_service()
        await audit.register(
            accion=ACCION_PROGRAMA_SUBIR,
            actor_id=self.actor_id,
            tenant_id=self.tenant_id,
            detalle={
                "programa_id": str(programa.id),
                "materia_id": str(datos.materia_id),
                "carrera_id": str(datos.carrera_id),
                "cohorte_id": str(datos.cohorte_id),
                "titulo": datos.titulo,
            },
            materia_id=datos.materia_id,
            filas_afectadas=1,
        )

        return await self._to_response(programa)

    # ── Listar programas ──────────────────────────────────────────────────

    async def listar_programas(
        self,
        materia_id: UUID | None = None,
        carrera_id: UUID | None = None,
        cohorte_id: UUID | None = None,
    ) -> dict:
        """Lista programas con filtros combinables.

        Args:
            materia_id: Filtrar por materia (opcional).
            carrera_id: Filtrar por carrera (opcional).
            cohorte_id: Filtrar por cohorte (opcional).

        Returns:
            ProgramaMateriaListResponse dict (sin referencia_archivo).
        """
        programas = await self.repo.list(
            materia_id=materia_id,
            carrera_id=carrera_id,
            cohorte_id=cohorte_id,
        )
        items = [await self._to_list_item(p) for p in programas]
        return {"items": items, "total": len(items)}

    # ── Obtener programa ──────────────────────────────────────────────────

    async def obtener_programa(self, programa_id: UUID) -> dict:
        """Obtiene el detalle completo de un programa.

        Args:
            programa_id: UUID del programa.

        Returns:
            ProgramaMateriaResponse dict con referencia_archivo.

        Raises:
            BusinessError: Si el programa no existe.
        """
        programa = await self.repo.get_by_id(programa_id)
        if programa is None:
            raise BusinessError("Programa no encontrado")
        return await self._to_response(programa)

    # ── Eliminar programa ─────────────────────────────────────────────────

    async def eliminar_programa(self, programa_id: UUID) -> None:
        """Elimina fisicamente un programa de materia.

        Args:
            programa_id: UUID del programa a eliminar.

        Raises:
            BusinessError: Si el programa no existe.
        """
        # Verificar existencia antes de eliminar (necesario para el audit)
        programa = await self.repo.get_by_id(programa_id)
        if programa is None:
            raise BusinessError("Programa no encontrado")

        materia_id = programa.materia_id
        eliminado = await self.repo.delete(programa_id)
        if not eliminado:
            raise BusinessError("Programa no encontrado")

        audit = self._build_audit_service()
        await audit.register(
            accion=ACCION_PROGRAMA_ELIMINAR,
            actor_id=self.actor_id,
            tenant_id=self.tenant_id,
            detalle={
                "programa_id": str(programa_id),
                "materia_id": str(materia_id),
            },
            materia_id=materia_id,
            filas_afectadas=1,
        )
