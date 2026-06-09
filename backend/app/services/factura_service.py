"""FacturaService — lógica de negocio para facturas.

Reglas:
  - Solo docentes con usuario.facturador=true pueden tener factura.
  - Factura abonada es INMUTABLE (service rechaza modificaciones).
  - Factura Pendiente → Abonada (transición única).
  - Al abonar, registra evento FACTURA_ABONAR en AuditLog.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError
from app.models.audit_log import AuditLog
from app.models.enums import EstadoFactura
from app.models.factura import Factura
from app.models.usuario import Usuario
from app.repositories.factura_repository import FacturaRepository


class FacturaService:
    """Service for tenant-scoped factura operations."""

    def __init__(
        self,
        session: AsyncSession,
        tenant_id: UUID,
    ) -> None:
        self.repo = FacturaRepository(session, Factura, tenant_id)
        self.session = session
        self.tenant_id = tenant_id

    async def crear(
        self,
        usuario_id: UUID,
        periodo: str,
        detalle: str | None = None,
        referencia_archivo: str | None = None,
        tamano_kb: int | None = None,
    ) -> Factura:
        """Crea una factura para un docente facturador.

        Args:
            usuario_id: Docente facturador.
            periodo: YYYY-MM.
            detalle: Descripción (opcional).
            referencia_archivo: Ruta/URL al archivo (opcional).
            tamano_kb: Tamaño en KB (opcional).

        Returns:
            Factura creada (estado Pendiente).

        Raises:
            BusinessError: Si el usuario no existe, no es facturador,
                o ya tiene factura para el período.
        """
        usuario = await self.session.get(Usuario, usuario_id)
        if usuario is None:
            raise BusinessError("El usuario no existe")
        if usuario.tenant_id != self.tenant_id:
            raise BusinessError("El usuario no pertenece al tenant")
        if not usuario.facturador:
            raise BusinessError(
                "El usuario no está habilitado como facturador"
            )

        # Verificar duplicado
        existe = await self.repo.find_by_periodo_usuario(periodo, usuario_id)
        if existe:
            raise BusinessError(
                "Ya existe una factura para ese usuario y período"
            )

        factura = Factura(
            tenant_id=self.tenant_id,
            usuario_id=usuario_id,
            periodo=periodo,
            detalle=detalle,
            referencia_archivo=referencia_archivo,
            tamano_kb=tamano_kb,
            estado=EstadoFactura.PENDIENTE.value,
            cargada_at=datetime.now(timezone.utc),
        )
        self.session.add(factura)
        await self.session.flush()
        return factura

    async def abonar(self, factura_id: UUID, actor_id: UUID) -> Factura:
        """Marca una factura como abonada y registra auditoría.

        Args:
            factura_id: UUID de la factura a abonar.
            actor_id: UUID del usuario que ejecuta la acción.

        Returns:
            Factura con estado=Abonada.

        Raises:
            BusinessError: Si no existe o ya está abonada.
        """
        factura = await self.repo.get_by_id(factura_id)
        if factura is None:
            raise BusinessError("La factura no existe")
        if factura.estado == EstadoFactura.ABONADA.value:
            raise BusinessError("La factura ya está abonada")

        factura.estado = EstadoFactura.ABONADA.value
        factura.abonada_at = datetime.now(timezone.utc)

        # Registrar auditoría
        audit = AuditLog(
            id=uuid4(),
            tenant_id=self.tenant_id,
            fecha_hora=datetime.now(timezone.utc),
            actor_id=actor_id,
            accion="FACTURA_ABONAR",
            detalle={
                "factura_id": str(factura_id),
                "periodo": factura.periodo,
                "usuario_id": str(factura.usuario_id),
            },
            filas_afectadas=1,
        )
        self.session.add(audit)
        await self.session.flush()
        return factura

    async def listar_pendientes(self) -> list[Factura]:
        """Lista facturas pendientes del tenant."""
        return await self.repo.list_pendientes()

    async def listar_por_usuario(self, usuario_id: UUID) -> list[Factura]:
        """Lista facturas de un usuario."""
        return await self.repo.list_by_usuario(usuario_id)

    async def obtener(self, factura_id: UUID) -> Factura | None:
        """Obtiene una factura por ID."""
        return await self.repo.get_by_id(factura_id)
