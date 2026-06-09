"""Modelo ficticio para tests de repositorio, mixin y aislamiento multi-tenant.

Este modelo NO es parte del dominio — existe exclusivamente para verificar
que :class:`~app.models.base.BaseMixin` y :class:`~app.repositories.base.BaseRepository`
funcionan correctamente sin depender de modelos de dominio reales.
"""

from sqlalchemy import Column, String

from app.models.base import BaseMixin
from app.core.database import Base
from app.core.encryption import EncryptedColumn


class DummyEntity(Base, BaseMixin):
    """Entidad dummy para tests de infraestructura.

    Attributes:
        label: Texto identificador para asserts en tests.
    """

    __tablename__ = "_test_dummy_entity"

    label = Column(String(100), nullable=False)


class DummySecretEntity(Base, BaseMixin):
    """Entidad dummy con columna cifrada para tests de encriptación.

    Attributes:
        name: Texto plano (público).
        secret_dni: DNI ficticio (PII) cifrado en reposo.
    """

    __tablename__ = "_test_dummy_secret"

    name = Column(String(100), nullable=False)
    secret_dni = Column(EncryptedColumn(key="A" * 32), nullable=True)
