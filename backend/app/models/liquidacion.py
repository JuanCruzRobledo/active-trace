"""Modelo Liquidacion — documento inmutable de liquidación mensual docente.

Cada liquidación representa el cálculo mensual para un docente en un rol
dentro de una cohorte. Una vez cerrada es INMUTABLE (no se modifica,
no tiene soft delete — se usa ``AUDIT_LOG`` para tracking de cambios).

Reglas:
  - ``monto_base``: salario base del rol vigente al período.
  - ``monto_plus``: suma de N_comisiones × plus(grupo, rol).
  - ``total = monto_base + monto_plus``, salvo ``excluido_por_factura = True``.
  - ``es_nexo``: separa visualmente liquidaciones de NEXO (no generan plus).
  - ``excluido_por_factura``: true para docentes facturadores (pago vía factura).
"""

from datetime import date

from sqlalchemy import Boolean, Column, Date, ForeignKey, Index, Numeric, String, text
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base
from app.models.base import BaseMixin
from app.models.enums import EstadoLiquidacion


class Liquidacion(Base, BaseMixin):
    __tablename__ = "liquidacion"

    cohorte_id = Column(
        ForeignKey("cohorte.id", ondelete="CASCADE"),
        nullable=False,
    )
    periodo = Column(String(7), nullable=False)  # YYYY-MM
    usuario_id = Column(
        ForeignKey("usuario.id", ondelete="CASCADE"),
        nullable=False,
    )
    rol = Column(String(50), nullable=False)
    comisiones = Column(JSONB, nullable=True)
    monto_base = Column(Numeric(12, 2), nullable=False)
    monto_plus = Column(Numeric(12, 2), nullable=False, default=0)
    total = Column(Numeric(12, 2), nullable=False)
    es_nexo = Column(Boolean, nullable=False, default=False)
    excluido_por_factura = Column(Boolean, nullable=False, default=False)
    estado = Column(
        String(20),
        nullable=False,
        default=EstadoLiquidacion.ABIERTA.value,
    )
    cerrada_at = Column(
        ForeignKey("audit_log.id", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (
        Index("ix_liquidacion_tenant_id", "tenant_id"),
        Index("ix_liquidacion_periodo", "periodo"),
        Index("ix_liquidacion_usuario_id", "usuario_id"),
        Index("ix_liquidacion_cohorte_id", "cohorte_id"),
        Index(
            "uq_liquidacion_periodo_usuario_rol_active",
            "tenant_id",
            "periodo",
            "usuario_id",
            "rol",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Liquidacion id={self.id} tenant_id={self.tenant_id} "
            f"periodo={self.periodo!r} usuario_id={self.usuario_id} "
            f"rol={self.rol!r} total={self.total} "
            f"estado={self.estado!r}>"
        )
