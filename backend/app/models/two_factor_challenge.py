"""Modelo TwoFactorChallenge — token opaco temporal para gate 2FA.

Cuando un usuario con 2FA hace login, NO se emite par access+refresh. En
su lugar, se genera un ``TwoFactorChallenge`` con un token opaco (TTL 5
minutos, un solo uso). El cliente lo presenta junto con su código TOTP
en ``POST /2fa/verify``. Si el código es válido, se emite el par
access+refresh y se marca el challenge como usado.

Modelo EFÍMERO: no hereda ``BaseMixin`` (no tiene soft delete ni
``updated_at``). Mismo patrón que ``PasswordResetToken``.
"""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.database import Base


class TwoFactorChallenge(Base):
    """Challenge token temporal para el gate 2FA post-login.

    Attributes:
        user_id: FK al ``User`` que debe verificar el código TOTP.
        token_hash: SHA-256 hex (64 chars) del challenge opaco. UNIQUE.
        expires_at: Timestamp de expiración absoluta (TTL 5 min).
        used_at: ``NULL`` mientras no se usó; timestamp al consumirse.
    """

    __tablename__ = "two_factor_challenge"

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
        """True si ya fue consumido."""
        return self.used_at is not None

    def __repr__(self) -> str:
        return (
            f"<TwoFactorChallenge id={self.id} user_id={self.user_id} "
            f"used={'yes' if self.used_at else 'no'} "
            f"expires_at={self.expires_at}>"
        )
