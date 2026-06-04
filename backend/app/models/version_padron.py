"""Modelo VersionPadron — versiones del padron de alumnos por materia x cohorte.

Cada importacion genera una nueva version. Solo una version puede estar activa
por combinacion (materia_id, cohorte_id) en simultaneo.
"""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String, text, func

from app.core.database import Base
from app.models.base import BaseMixin


class VersionPadron(Base, BaseMixin):
    __tablename__ = "version_padron"

    materia_id = Column(
        ForeignKey("materia.id", ondelete="CASCADE"), nullable=False
    )
    cohorte_id = Column(
        ForeignKey("cohorte.id", ondelete="CASCADE"), nullable=False
    )
    cargado_por = Column(
        ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True
    )
    cargado_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    activa = Column(Boolean, nullable=False, default=True)

    __table_args__ = (
        Index("ix_version_padron_tenant_id", "tenant_id"),
        Index("ix_version_padron_materia_cohorte", "materia_id", "cohorte_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<VersionPadron id={self.id} materia_id={self.materia_id} "
            f"cohorte_id={self.cohorte_id} activa={self.activa}>"
        )
