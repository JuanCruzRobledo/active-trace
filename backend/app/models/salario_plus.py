"""Modelo SalarioPlus — plus salarial por grupo (clave de materia) y rol.

Define el monto adicional que percibe un docente según:
  - El grupo temático de la materia (PROG, BD, etc.)
  - El rol que cumple (PROFESOR, TUTOR, etc.)

El monto_plus de una liquidación se calcula como:
  N_comisiones × SalarioPlus(grupo, rol)
"""

from datetime import date

from sqlalchemy import Column, Date, Index, Numeric, String

from app.core.database import Base
from app.models.base import BaseMixin


class SalarioPlus(Base, BaseMixin):
    __tablename__ = "salario_plus"

    grupo = Column(String(20), nullable=False)
    rol = Column(String(50), nullable=False)
    descripcion = Column(String(200), nullable=True)
    monto = Column(Numeric(12, 2), nullable=False)
    desde = Column(Date, nullable=False)
    hasta = Column(Date, nullable=True)

    __table_args__ = (
        Index("ix_salario_plus_tenant_id", "tenant_id"),
        Index(
            "ix_salario_plus_grupo_rol_vigencia",
            "tenant_id",
            "grupo",
            "rol",
            "desde",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<SalarioPlus id={self.id} tenant_id={self.tenant_id} "
            f"grupo={self.grupo!r} rol={self.rol!r} "
            f"monto={self.monto}>"
        )
