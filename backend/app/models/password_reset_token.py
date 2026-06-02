"""Modelo PasswordResetToken — token de un solo uso para recuperación.

Se genera con ``secrets.token_urlsafe(32)``, se hashea con SHA-256 y se
persiste con TTL (``PASSWORD_RESET_EXPIRE_MINUTES``, default 30). Al
usarse, se marca ``used_at = now()``; al pedir un nuevo reset para el
mismo ``user_id``, se invalidan los pendientes.

Modelo EFÍMERO: no hereda ``BaseMixin`` (no tiene soft delete ni
``updated_at``). El ciclo de vida es: crear → usar (mark_used) o expirar →
purgar (cleanup_expired, cuando exista en un change futuro).
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.database import Base


class PasswordResetToken(Base):
    """Token de un solo uso para reset de contraseña.

    Attributes:
        user_id: FK al ``User`` que solicitó el reset.
        token_hash: SHA-256 hex (64 chars) del token opaco. UNIQUE.
        expires_at: Timestamp de expiración absoluta.
        used_at: ``NULL`` mientras no se usó; timestamp al consumirse.
    """

    __tablename__ = "password_reset_token"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash = Column(String(128), nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    def is_expired(self, now: datetime | None = None) -> bool:
        """True si ``expires_at < now``."""
        if now is None:
            now = datetime.now(timezone.utc)
        return self.expires_at < now

    def is_used(self) -> bool:
        """True si ya fue consumido (``used_at IS NOT NULL``)."""
        return self.used_at is not None

    def __repr__(self) -> str:
        return (
            f"<PasswordResetToken id={self.id} user_id={self.user_id} "
            f"used={'yes' if self.used_at else 'no'} "
            f"expires_at={self.expires_at}>"
        )
