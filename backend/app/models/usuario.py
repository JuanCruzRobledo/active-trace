"""Modelo Usuario — entidad base del dominio con PII cifrada.

El Usuario es la identidad de negocio del sistema, distinto del modelo ``User``
del módulo de autenticación (C-03). Se relacionan 1:1 por ``auth_user_id``.

PII (email, dni, cuil, cbu, alias_cbu) se almacena cifrada con AES-256 en
reposo via ``EncryptedColumn`` (C-02). El resto de los campos son de negocio.

Soft delete: hereda ``BaseMixin.deleted_at``. El partial unique index sobre
``(tenant_id, email)`` filtra ``WHERE deleted_at IS NULL`` para permitir
re-uso del email tras baja lógica.
"""

from sqlalchemy import Column, ForeignKey, Index, String, text

from app.core.database import Base
from app.core.encryption import EncryptedColumn
from app.models.base import BaseMixin


class Usuario(Base, BaseMixin):
    __tablename__ = "usuario"

    auth_user_id = Column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    nombre = Column(String(100), nullable=False)
    apellidos = Column(String(200), nullable=False)

    # ── PII cifrada con AES-256 (EncryptedColumn) ──────────────────────
    email = Column(EncryptedColumn(key="placeholder_replace_in_init_engine"), nullable=False)
    dni = Column(EncryptedColumn(key="placeholder_replace_in_init_engine"), nullable=True)
    cuil = Column(EncryptedColumn(key="placeholder_replace_in_init_engine"), nullable=True)
    cbu = Column(EncryptedColumn(key="placeholder_replace_in_init_engine"), nullable=True)
    alias_cbu = Column(EncryptedColumn(key="placeholder_replace_in_init_engine"), nullable=True)

    # ── Datos de negocio ───────────────────────────────────────────────
    banco = Column(String(100), nullable=True)
    regional = Column(String(100), nullable=True)
    legajo = Column(String(50), nullable=True)
    legajo_profesional = Column(String(50), nullable=True)
    facturador = Column(String(200), nullable=True)
    estado = Column(String(20), nullable=False, default="Activo")

    __table_args__ = (
        Index("ix_usuario_tenant_id", "tenant_id"),
        Index(
            "uq_usuario_tenant_email_active",
            "tenant_id",
            "email",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Usuario id={self.id} tenant_id={self.tenant_id} "
            f"nombre={self.nombre!r} apellidos={self.apellidos!r} "
            f"estado={self.estado!r}>"
        )
