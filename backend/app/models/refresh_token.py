"""Modelo RefreshToken — token opaco con rotación y reuso-detection.

Los refresh tokens se generan con ``secrets.token_urlsafe(32)`` (256 bits
de entropía), se devuelven al cliente una sola vez en claro, y se guardan
en DB hasheados con SHA-256 (``token_hash``). Cada ``POST /refresh`` rota
el token (marca ``revoked_at`` y ``replaced_by_id``); si se detecta reuso
de un token ya revocado, se invalida toda la familia del mismo ``user_id``.

Soft delete: hereda ``BaseMixin.deleted_at``. Las queries por defecto los
excluyen via el scope de :class:`~app.repositories.base.BaseRepository`.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import declared_attr

from app.core.database import Base
from app.models.base import BaseMixin


class RefreshToken(Base, BaseMixin):
    """Refresh token opaco con tracking de rotación y revocación.

    Attributes:
        user_id: FK al ``User`` dueño del token.
        token_hash: SHA-256 hex (64 chars) del token opaco. UNIQUE.
        expires_at: Timestamp de expiración absoluta.
        revoked_at: ``NULL`` mientras está activo; timestamp al rotar/revocar.
        replaced_by_id: FK al nuevo token que sustituyó a este. ``NULL`` si
            nunca se rotó o si fue la última versión.
        user_agent: User-Agent del cliente que originó el token.
        created_ip: IP del cliente que originó el token.
    """

    __tablename__ = "refresh_token"

    user_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash = Column(String(128), nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    # Self-reference para tracking de rotación. La FK se crea con ALTER
    # en la migración para evitar problemas de orden de creación.
    replaced_by_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("refresh_token.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_agent = Column(Text, nullable=True)
    created_ip = Column(String(64), nullable=True)

    # Índice de tenant_id (de BaseMixin, explícito porque __table_args__ pisa
    # el del mixin) + índices de user_id para lookups por usuario.
    __table_args__ = (
        Index("ix_refresh_token_tenant_id", "tenant_id"),
        Index("ix_refresh_token_user_id", "user_id"),
    )

    def is_revoked(self) -> bool:
        """True si el token está revocado."""
        return self.revoked_at is not None

    def is_expired(self, now: datetime | None = None) -> bool:
        """True si ``expires_at < now`` (o ``now`` provisto)."""
        if now is None:
            from datetime import timezone

            now = datetime.now(timezone.utc)
        return self.expires_at < now

    def __repr__(self) -> str:
        return (
            f"<RefreshToken id={self.id} user_id={self.user_id} "
            f"revoked={'yes' if self.revoked_at else 'no'} "
            f"replaced_by={self.replaced_by_id}>"
        )
