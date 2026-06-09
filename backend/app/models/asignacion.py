"""Modelo Asignacion — vincula Usuario ↔ Rol ↔ contexto académico.

Cada asignacion asocia un usuario con un rol dentro de un contexto academico
opcional (materia, carrera, cohorte, comisiones). La vigencia se define con
``desde``/``hasta``; el ``estado_vigencia`` es derivado (no almacenado).

Soporta jerarquia via ``responsable_id`` (FK al propio Usuario) y soft-delete
para preservar historico.
"""

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base
from app.models.base import BaseMixin


class Asignacion(Base, BaseMixin):
    __tablename__ = "asignacion"

    usuario_id = Column(
        ForeignKey("usuario.id", ondelete="CASCADE"),
        nullable=False,
    )
    rol = Column(String(50), nullable=False)
    materia_id = Column(
        ForeignKey("materia.id", ondelete="SET NULL"),
        nullable=True,
    )
    carrera_id = Column(
        ForeignKey("carrera.id", ondelete="SET NULL"),
        nullable=True,
    )
    cohorte_id = Column(
        ForeignKey("cohorte.id", ondelete="SET NULL"),
        nullable=True,
    )
    comisiones = Column(JSONB, nullable=True)
    responsable_id = Column(
        ForeignKey("usuario.id", ondelete="SET NULL"),
        nullable=True,
    )
    desde = Column(DateTime(timezone=True), nullable=False)
    hasta = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_asignacion_tenant_id", "tenant_id"),
        Index("ix_asignacion_usuario_id", "usuario_id"),
        Index("ix_asignacion_materia_id", "materia_id"),
        Index("ix_asignacion_carrera_id", "carrera_id"),
        Index("ix_asignacion_cohorte_id", "cohorte_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<Asignacion id={self.id} usuario_id={self.usuario_id} "
            f"rol={self.rol!r} desde={self.desde} hasta={self.hasta}>"
        )
