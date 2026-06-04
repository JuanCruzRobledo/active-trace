"""Modelo EntradaPadron — entrada individual del padron de alumnos.

Cada entrada representa un alumno dentro de una version de padron.
El email se almacena cifrado (PII). usuario_id puede ser nulo si el
alumno aun no tiene cuenta en el sistema.
"""

from sqlalchemy import Column, ForeignKey, Index, String

from app.core.database import Base
from app.core.encryption import EncryptedColumn
from app.models.base import BaseMixin


class EntradaPadron(Base, BaseMixin):
    __tablename__ = "entrada_padron"

    version_id = Column(
        ForeignKey("version_padron.id", ondelete="CASCADE"), nullable=False
    )
    usuario_id = Column(
        ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True
    )

    # ── Datos desnormalizados (para historico) ─────────────────────────
    nombre = Column(String(100), nullable=False)
    apellidos = Column(String(200), nullable=False)
    email = Column(
        EncryptedColumn(key="placeholder_replace_in_init_engine"), nullable=False
    )
    comision = Column(String(50), nullable=True)
    regional = Column(String(100), nullable=True)

    __table_args__ = (
        Index("ix_entrada_padron_tenant_id", "tenant_id"),
        Index("ix_entrada_padron_version_id", "version_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<EntradaPadron id={self.id} version_id={self.version_id} "
            f"nombre={self.nombre!r} apellidos={self.apellidos!r}>"
        )
