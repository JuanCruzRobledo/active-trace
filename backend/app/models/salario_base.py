"""Modelo SalarioBase — grilla salarial base por rol y tenant.

Vigencia por período (desde/hasta). Al actualizar un salario, se cierra
la vigencia anterior (hasta = nueva_desde - 1 día) y se crea un nuevo
registro con ``desde = nueva_desde``.
"""

from datetime import date

from sqlalchemy import Column, Date, Index, Numeric, String

from app.core.database import Base
from app.models.base import BaseMixin


class SalarioBase(Base, BaseMixin):
    __tablename__ = "salario_base"

    rol = Column(String(50), nullable=False)
    monto = Column(Numeric(12, 2), nullable=False)
    desde = Column(Date, nullable=False)
    hasta = Column(Date, nullable=True)

    __table_args__ = (
        Index("ix_salario_base_tenant_id", "tenant_id"),
        Index("ix_salario_base_rol_vigencia", "tenant_id", "rol", "desde"),
    )

    def __repr__(self) -> str:
        return (
            f"<SalarioBase id={self.id} tenant_id={self.tenant_id} "
            f"rol={self.rol!r} monto={self.monto} "
            f"desde={self.desde} hasta={self.hasta}>"
        )
