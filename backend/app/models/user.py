"""Modelo User — identidad de un usuario en el sistema multi-tenant.

Cada User pertenece a un ``tenant``. El ``email`` es único por tenant (un mismo
email puede existir en distintos tenants, pero no duplicado dentro del mismo).
El ``password_hash`` es Argon2id; el ``totp_secret`` (cuando está enrolado) se
persiste cifrado con Fernet para que un dump de la DB no exponga el secreto TOTP.

El nombre de la tabla es ``users`` y NO ``user`` porque ``user`` es palabra
reservada de PostgreSQL y producía corrupción de catálogo con quoted identifiers
en Postgres 18.

Soft delete: hereda ``BaseMixin.deleted_at``. Los usuarios "eliminados" siguen
existiendo para auditoría; las queries por defecto los excluyen via el scope
de :class:`~app.repositories.base.BaseRepository`.
"""

from sqlalchemy import Boolean, Column, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.encryption import EncryptedColumn
from app.models.base import BaseMixin


class User(Base, BaseMixin):
    """Usuario del sistema (identidad base de C-03).

    Attributes:
        email: Email del usuario (lookup key para login). Único por tenant.
        password_hash: Hash Argon2id del password.
        is_active: Si ``False``, el usuario no puede autenticarse.
        totp_secret: Secreto TOTP cifrado con Fernet (AES). ``None`` si 2FA
            no está enrolado.
        totp_enabled: Si ``True``, el gate 2FA se activa después de
            validar credenciales.
    """

    __tablename__ = "users"

    email = Column(String(255), nullable=False)
    password_hash = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    # Placeholder key — la real se inyecta en init_engine() desde settings.
    totp_secret = Column(
        EncryptedColumn(key="placeholder_replace_in_init_engine"),
        nullable=True,
    )
    totp_enabled = Column(Boolean, nullable=False, default=False)

    # Un email por tenant + índice de tenant_id (de BaseMixin, explícito
    # porque al definir __table_args__ pisamos el del mixin).
    __table_args__ = (
        Index("ix_users_tenant_id", "tenant_id"),
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
    )

    def __repr__(self) -> str:
        return (
            f"<User id={self.id} tenant_id={self.tenant_id} "
            f"email={self.email!r} is_active={self.is_active} "
            f"totp_enabled={self.totp_enabled}>"
        )
