"""Modelo ResultadoEvaluacion — nota final de un alumno en una evaluacion.

Los resultados son independientes de las reservas: un alumno puede tener
resultado sin reserva (ej. eximido) y viceversa. Se usa upsert para evitar
duplicados por alumno + evaluacion.
"""

from __future__ import annotations

from sqlalchemy import Column, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.database import Base
from app.models.base import BaseMixin


class ResultadoEvaluacion(Base, BaseMixin):
    __tablename__ = "resultado_evaluacion"

    evaluacion_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("evaluacion.id", ondelete="CASCADE"),
        nullable=False,
    )
    alumno_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="CASCADE"),
        nullable=False,
    )
    nota_final = Column(String(100), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "evaluacion_id", "alumno_id", "tenant_id",
            name="uq_resultado_evaluacion_alumno",
        ),
        *BaseMixin.__table_args__,
    )

    def __repr__(self) -> str:
        return (
            f"<ResultadoEvaluacion id={self.id} "
            f"evaluacion_id={self.evaluacion_id} nota={self.nota_final!r}>"
        )
