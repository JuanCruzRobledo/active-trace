"""Modelo UmbralMateria — umbral de aprobacion configurable por asignacion y materia.

Cada combinacion (asignacion_id, materia_id) activa es unica (partial unique
index con deleted_at IS NULL). Esto permite que una misma asignacion (docente)
pueda tener distintos umbrales para distintas materias, y se pueda actualizar
el umbral soft-deleteando el registro anterior y creando uno nuevo.

valores_aprobatorios (JSONB) lista de strings que se consideran aprobados
para calificaciones textuales (ej: ["Aprobado", "Promocionado"]).
"""

from sqlalchemy import Column, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base
from app.models.base import BaseMixin


class UmbralMateria(Base, BaseMixin):
    __tablename__ = "umbral_materia"

    asignacion_id = Column(
        ForeignKey("asignacion.id", ondelete="CASCADE"), nullable=False
    )
    materia_id = Column(
        ForeignKey("materia.id", ondelete="CASCADE"), nullable=False
    )
    umbral_pct = Column(Integer, nullable=False, default=60)
    valores_aprobatorios = Column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_umbral_materia_tenant_id", "tenant_id"),
        Index(
            "ix_umbral_materia_asignacion_materia",
            "asignacion_id",
            "materia_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<UmbralMateria id={self.id} asignacion_id={self.asignacion_id} "
            f"materia_id={self.materia_id} umbral_pct={self.umbral_pct}>"
        )
