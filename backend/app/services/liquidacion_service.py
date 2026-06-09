"""LiquidacionService — lógica de negocio para liquidaciones.

Reglas:
  - RN-33: Acumulación de Plus sin tope (N comisiones activas × Plus).
  - RN-34: Docentes facturadores → excluidos del pago por trace.
  - NEXO no genera plus (es_nexo=true, monto_plus=0).
  - Liquidación cerrada es INMUTABLE (service rechaza modificaciones).
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError
from app.models.audit_log import AuditLog
from app.models.clave_plus import ClavePlus
from app.models.liquidacion import Liquidacion
from app.models.materia import Materia
from app.models.salario_base import SalarioBase
from app.models.salario_plus import SalarioPlus
from app.models.usuario import Usuario
from app.models.enums import EstadoLiquidacion
from app.repositories.clave_plus_repository import ClavePlusRepository
from app.repositories.liquidacion_repository import LiquidacionRepository
from app.repositories.salario_base_repository import SalarioBaseRepository
from app.repositories.salario_plus_repository import SalarioPlusRepository


class LiquidacionService:
    """Service for tenant-scoped liquidacion operations."""

    def __init__(
        self,
        session: AsyncSession,
        tenant_id: UUID,
    ) -> None:
        self.liq_repo = LiquidacionRepository(session, Liquidacion, tenant_id)
        self.sb_repo = SalarioBaseRepository(session, SalarioBase, tenant_id)
        self.sp_repo = SalarioPlusRepository(session, SalarioPlus, tenant_id)
        self.cp_repo = ClavePlusRepository(session, ClavePlus, tenant_id)
        self.session = session
        self.tenant_id = tenant_id

    # ── Cálculo de liquidación ────────────────────────────────────────────

    async def calcular(
        self,
        cohorte_id: UUID,
        periodo: str,
        usuario_id: UUID,
        rol: str,
        comisiones: list[str] | None,
    ) -> Liquidacion:
        """Calcula y persiste una liquidación mensual.

        Args:
            cohorte_id: Cohorte de referencia.
            periodo: Período YYYY-MM.
            usuario_id: Docente a liquidar.
            rol: Rol del docente.
            comisiones: IDs de las comisiones activas (opcional).

        Returns:
            Liquidacion persistida (estado Abierta).

        Raises:
            BusinessError: Si el usuario no tiene facturador=true o no existe.
        """
        # Obtener usuario
        usuario = await self.session.get(Usuario, usuario_id)
        if usuario is None:
            raise BusinessError("El usuario no existe")
        if usuario.tenant_id != self.tenant_id:
            raise BusinessError("El usuario no pertenece al tenant")

        # Determinar si es NEXO
        es_nexo = (rol.upper() == "NEXO")

        # Obtener salario base vigente
        salario_base = await self.sb_repo.find_vigente(rol, date.today())
        monto_base = salario_base.monto if salario_base else Decimal("0")

        # Calcular plus salarial
        monto_plus = Decimal("0")
        if not es_nexo and comisiones:
            # Obtener materias vinculadas a las comisiones
            for comision_id in comisiones:
                materia = await self.session.get(Materia, UUID(comision_id))
                if materia and materia.clave_plus_id:
                    clave = await self.session.get(ClavePlus, materia.clave_plus_id)
                    if clave and clave.activa:
                        sp = await self.sp_repo.find_vigente(clave.codigo, rol, date.today())
                        if sp:
                            monto_plus += sp.monto

        # Docente facturador → excluido
        excluido = bool(usuario.facturador)
        total = Decimal("0") if excluido else (monto_base + monto_plus)

        liq = Liquidacion(
            tenant_id=self.tenant_id,
            cohorte_id=cohorte_id,
            periodo=periodo,
            usuario_id=usuario_id,
            rol=rol,
            comisiones=comisiones,
            monto_base=monto_base,
            monto_plus=monto_plus,
            total=total,
            es_nexo=es_nexo,
            excluido_por_factura=excluido,
            estado=EstadoLiquidacion.ABIERTA.value,
        )
        self.session.add(liq)
        await self.session.flush()
        return liq

    # ── Cierre de liquidación ─────────────────────────────────────────────

    async def cerrar(self, liquidacion_id: UUID, actor_id: UUID) -> Liquidacion:
        """Cierra una liquidación abierta (inmutable tras cierre).

        Crea un registro de auditoría (``audit_log``) con la acción y lo
        vincula via ``liq.cerrada_at``, que es FK a ``audit_log.id``.

        Args:
            liquidacion_id: UUID de la liquidación a cerrar.
            actor_id: UUID del usuario que ejecuta el cierre.

        Returns:
            Liquidacion con estado=Cerrada.

        Raises:
            BusinessError: Si ya está cerrada o no existe.
        """
        liq = await self.liq_repo.get_by_id(liquidacion_id)
        if liq is None:
            raise BusinessError("La liquidación no existe")
        if liq.estado == EstadoLiquidacion.CERRADA.value:
            raise BusinessError("La liquidación ya está cerrada")

        # Crear registro de auditoría
        audit = AuditLog(
            id=uuid4(),
            tenant_id=self.tenant_id,
            fecha_hora=datetime.now(timezone.utc),
            actor_id=actor_id,
            accion="liquidacion.cerrar",
            detalle={
                "liquidacion_id": str(liquidacion_id),
                "periodo": liq.periodo,
                "total": str(liq.total),
            },
            filas_afectadas=1,
        )
        self.session.add(audit)
        await self.session.flush()

        liq.estado = EstadoLiquidacion.CERRADA.value
        liq.cerrada_at = audit.id
        await self.session.flush()
        return liq

    # ── Consultas ─────────────────────────────────────────────────────────

    async def listar_por_periodo(self, periodo: str) -> list[Liquidacion]:
        """Lista liquidaciones de un período.

        Args:
            periodo: YYYY-MM.

        Returns:
            Lista de Liquidaciones.
        """
        return await self.liq_repo.list_by_periodo(periodo)

    async def listar_abiertas(self) -> list[Liquidacion]:
        """Lista liquidaciones abiertas del tenant."""
        return await self.liq_repo.list_abiertas()

    async def obtener(self, liquidacion_id: UUID) -> Liquidacion | None:
        """Obtiene una liquidación por ID."""
        return await self.liq_repo.get_by_id(liquidacion_id)
