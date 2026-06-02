"""Modelos base: mixin transversal con soporte multi-tenant, timestamps y soft delete.

Todo modelo del dominio SHALL heredar de :class:`BaseMixin` para obtener
automáticamente ``id``, ``tenant_id``, timestamps de auditoría y soporte
de soft delete.

El flujo de creación de un nuevo modelo es::

    from app.models.base import BaseMixin
    from app.core.database import Base

    class MiModelo(Base, BaseMixin):
        __tablename__ = "mi_modelo"
        nombre = Column(String(100))
"""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import Column, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import declared_attr


def _utcnow() -> datetime:
    """Retorna datetime actual con timezone-aware UTC.

    Reemplaza ``datetime.utcnow`` (deprecated en Python 3.12+, pendiente de
    remoción) con la variante moderna timezone-aware.
    """
    return datetime.now(timezone.utc)


class BaseMixin:
    """Mixin transversal — todo modelo del dominio hereda de este mixin.

    Columnas provistas:
    - ``id``: UUID primary key, autogenerado via :func:`uuid.uuid4`.
    - ``tenant_id``: UUID, NOT NULL, indexado — raíz del aislamiento multi-tenant.
    - ``created_at``: timestamp UTC de creación (autoset al insert).
    - ``updated_at``: timestamp UTC de última modificación (autoset al update).
    - ``deleted_at``: nullable — soft delete. ``NULL`` = registro activo.
    """

    id = Column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    tenant_id = Column(
        PGUUID(as_uuid=True),
        nullable=False,
        # NOTA: el índice se define en __table_args__,
        # no aquí, para tener control del nombre del índice.
    )
    created_at = Column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )
    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    @declared_attr  # type: ignore[arg-type]
    def __table_args__(cls) -> tuple[Any, ...]:  # noqa: N805
        """Table args: incluye índice sobre tenant_id para performance."""
        tablename = getattr(cls, "__tablename__", "unknown")
        return (
            Index(f"ix_{tablename}_tenant_id", "tenant_id"),
        )
