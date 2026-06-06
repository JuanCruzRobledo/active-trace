"""Modelo Factura — factura de honorarios de docentes facturadores.

Solo aplica a docentes con ``usuario.facturador = True``.
Cuando un docente factura, su liquidación se marca como
``excluido_por_factura = True`` y no genera pago por trace.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String

from app.core.database import Base
from app.models.base import BaseMixin
from app.models.enums import EstadoFactura


class Factura(Base, BaseMixin):
    __tablename__ = "factura"

    usuario_id = Column(
        ForeignKey("usuario.id", ondelete="CASCADE"),
        nullable=False,
    )
    periodo = Column(String(7), nullable=False)  # YYYY-MM
    detalle = Column(String(1000), nullable=True)
    referencia_archivo = Column(String(500), nullable=True)
    tamano_kb = Column(Integer, nullable=True)
    estado = Column(
        String(20),
        nullable=False,
        default=EstadoFactura.PENDIENTE.value,
    )
    cargada_at = Column(DateTime(timezone=True), nullable=False)
    abonada_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_factura_tenant_id", "tenant_id"),
        Index("ix_factura_usuario_id", "usuario_id"),
        Index("ix_factura_periodo", "periodo"),
    )

    def __repr__(self) -> str:
        return (
            f"<Factura id={self.id} tenant_id={self.tenant_id} "
            f"periodo={self.periodo!r} usuario_id={self.usuario_id} "
            f"estado={self.estado!r}>"
        )
