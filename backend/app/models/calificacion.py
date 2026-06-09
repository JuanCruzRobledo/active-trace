"""Modelo Calificacion — calificacion de un alumno en una actividad.

Cada calificacion pertenece a una entrada del padron y a una materia.
La nota puede ser numerica (nota_numerica), textual (nota_textual),
o ambas. Al menos una de las dos debe estar presente.

El campo aprobado se calcula al importar segun el umbral configurado
en UmbralMateria para la asignacion correspondiente.
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    event,
    func,
)
from sqlalchemy.orm import validates

from app.core.database import Base
from app.models.base import BaseMixin
from app.models.enums import OrigenCalificacion


class Calificacion(Base, BaseMixin):
    __tablename__ = "calificacion"

    entrada_padron_id = Column(
        ForeignKey("entrada_padron.id", ondelete="CASCADE"), nullable=False
    )
    materia_id = Column(
        ForeignKey("materia.id", ondelete="CASCADE"), nullable=False
    )
    actividad = Column(String(200), nullable=False)
    nota_numerica = Column(Numeric(5, 2), nullable=True)
    nota_textual = Column(String(100), nullable=True)
    aprobado = Column(Boolean, nullable=True)
    origen = Column(
        String(20),
        nullable=False,
        default=OrigenCalificacion.IMPORTADO.value,
    )
    importado_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_calificacion_tenant_id", "tenant_id"),
        Index(
            "ix_calificacion_entrada_materia_actividad",
            "entrada_padron_id",
            "materia_id",
            "actividad",
        ),
        Index("ix_calificacion_materia_id", "materia_id"),
    )

    @validates("origen")
    def _validate_origen(self, key: str, value: str | OrigenCalificacion) -> str:
        if isinstance(value, OrigenCalificacion):
            return value.value
        return value

    def __repr__(self) -> str:
        return (
            f"<Calificacion id={self.id} entrada_padron_id={self.entrada_padron_id} "
            f"materia_id={self.materia_id} actividad={self.actividad!r} "
            f"nota_numerica={self.nota_numerica}>"
        )


@event.listens_for(Calificacion, "before_insert")
@event.listens_for(Calificacion, "before_update")
def _check_tiene_nota(
    mapper: object,
    connection: object,
    target: Calificacion,
) -> None:
    """Valida que al menos nota_numerica o nota_textual no sea nulo."""
    if target.nota_numerica is None and target.nota_textual is None:
        raise ValueError(
            "Debe especificarse al menos una nota (nota_numerica o nota_textual)"
        )
