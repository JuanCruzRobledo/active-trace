"""Modelo ProgramaMateria — documento oficial por materia, carrera y cohorte (C-17).

Cada ProgramaMateria representa un documento oficial (programa de la materia)
asociado a una combinacion unica de materia × carrera × cohorte dentro del tenant.
La referencia_archivo es un UUID opaco que apunta al archivo real en storage
(cuando el servicio de storage este disponible — FASE 2).

Soft delete NO aplica: eliminacion es fisica (hard delete). El audit log
captura la trazabilidad mediante codigo ``PROGRAMA_ELIMINAR``.
"""

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.database import Base
from app.models.base import BaseMixin


class ProgramaMateria(Base, BaseMixin):
    __tablename__ = "programa_materia"

    materia_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("materia.id", ondelete="CASCADE"),
        nullable=False,
    )
    carrera_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("carrera.id", ondelete="CASCADE"),
        nullable=False,
    )
    cohorte_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("cohorte.id", ondelete="CASCADE"),
        nullable=False,
    )
    titulo = Column(String(300), nullable=False)
    referencia_archivo = Column(PGUUID(as_uuid=True), nullable=False)
    cargado_at = Column(
        DateTime(timezone=True),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_programa_materia_tenant_id", "tenant_id"),
        Index("ix_programa_materia_materia_id", "materia_id"),
        Index("ix_programa_materia_carrera_id", "carrera_id"),
        Index("ix_programa_materia_cohorte_id", "cohorte_id"),
        # Unica combinacion materia x carrera x cohorte dentro del tenant
        # Sin WHERE deleted_at porque es hard delete
        Index(
            "uq_programa_materia_tenant_materia_carrera_cohorte",
            "tenant_id",
            "materia_id",
            "carrera_id",
            "cohorte_id",
            unique=True,
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<ProgramaMateria id={self.id} materia_id={self.materia_id} "
            f"carrera_id={self.carrera_id} cohorte_id={self.cohorte_id} "
            f"titulo={self.titulo!r}>"
        )
