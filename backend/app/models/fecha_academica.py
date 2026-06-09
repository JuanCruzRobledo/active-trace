"""Modelo FechaAcademica — instancia evaluativa en el calendario academico (C-17).

Cada FechaAcademica representa una instancia evaluativa (Parcial, TP,
Coloquio o Recuperatorio) asociada a una materia y cohorte dentro del
tenant, con numero de instancia, periodo, fecha y titulo.

La combinacion ``(tenant_id, materia_id, cohorte_id, tipo, numero)`` es
unica dentro del tenant.

Usa soft delete estandar (BaseMixin). Las fechas eliminadas no aparecen
en listados ni en exportacion LMS, pero se conservan en BD para trazabilidad.
"""

from sqlalchemy import Column, Date, Enum, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.database import Base
from app.models.base import BaseMixin
from app.models.enums import TipoFechaAcademica


class FechaAcademica(Base, BaseMixin):
    __tablename__ = "fecha_academica"

    materia_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("materia.id", ondelete="CASCADE"),
        nullable=False,
    )
    cohorte_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("cohorte.id", ondelete="CASCADE"),
        nullable=False,
    )
    tipo = Column(
        Enum(
            TipoFechaAcademica,
            name="tipo_fecha_academica",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    numero = Column(Integer, nullable=False)
    periodo = Column(String(20), nullable=False)
    fecha = Column(Date, nullable=False)
    titulo = Column(String(300), nullable=False)

    __table_args__ = (
        Index("ix_fecha_academica_tenant_id", "tenant_id"),
        Index("ix_fecha_academica_materia_id", "materia_id"),
        Index("ix_fecha_academica_cohorte_id", "cohorte_id"),
        Index(
            "uq_fecha_academica_tenant_materia_cohorte_tipo_numero",
            "tenant_id",
            "materia_id",
            "cohorte_id",
            "tipo",
            "numero",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<FechaAcademica id={self.id} materia_id={self.materia_id} "
            f"cohorte_id={self.cohorte_id} tipo={self.tipo} "
            f"numero={self.numero} fecha={self.fecha}>"
        )
