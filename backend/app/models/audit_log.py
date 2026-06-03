"""Modelo AuditLog — registro persistente append-only de auditoría (C-05).

NO hereda BaseMixin: no tiene ``updated_at`` ni ``deleted_at``.
Es append-only: una vez insertado, no se puede modificar ni eliminar
(a nivel aplicación y a nivel DB via trigger).

La tabla es ``audit_log``. El campo ``detalle`` es JSONB para payload
estructurado variable según la acción.
"""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, DateTime, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditLog(Base):
    """Registro inmutable de una acción significativa en el sistema.

    Attributes:
        id: UUID (PK), autogenerado.
        tenant_id: UUID del tenant (NOT NULL) — aislamiento multi-tenant.
        fecha_hora: Timestamp UTC de la acción (default: ahora).
        actor_id: UUID del usuario que ejecutó la acción (NOT NULL).
        impersonado_id: UUID del usuario impersonado (nullable).
        materia_id: UUID de la materia asociada (nullable).
        accion: Código estandarizado VARCHAR(100) (NOT NULL).
        detalle: JSONB con contexto adicional (nullable).
        filas_afectadas: Cantidad de registros involucrados (nullable).
        ip: Dirección IP del cliente VARCHAR(45) (nullable).
        user_agent: User-Agent del cliente (nullable).
    """

    __tablename__ = "audit_log"

    id = Column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    tenant_id = Column(
        PGUUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    fecha_hora = Column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )
    actor_id = Column(
        PGUUID(as_uuid=True),
        nullable=False,
    )
    impersonado_id = Column(
        PGUUID(as_uuid=True),
        nullable=True,
    )
    materia_id = Column(
        PGUUID(as_uuid=True),
        nullable=True,
    )
    accion = Column(
        Text,
        nullable=False,
    )
    detalle = Column(
        JSONB,
        nullable=True,
    )
    filas_afectadas = Column(
        Integer,
        nullable=True,
    )
    ip = Column(
        Text,
        nullable=True,
    )
    user_agent = Column(
        Text,
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} tenant_id={self.tenant_id} "
            f"actor_id={self.actor_id} accion={self.accion!r}>"
        )
