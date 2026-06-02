"""Modelo Tenant — raíz del aislamiento multi-tenant.

Un ``Tenant`` representa una institución. Es la primera entidad del sistema:
antes de cualquier otro registro, existe el tenant. Todo modelo del dominio
hereda de :class:`~app.models.base.BaseMixin` que provee la columna
``tenant_id`` para el aislamiento row-level.

Reglas:
- ``id`` y ``tenant_id`` coinciden en el registro raíz (self-reference).
- El par ``(tenant_id, id)`` es único por definición.
- ``nombre`` es el identificador legible del tenant.
"""

from sqlalchemy import Column, String

from app.models.base import BaseMixin
from app.core.database import Base


class Tenant(Base, BaseMixin):
    """Representa una institución (tenant) en el sistema multi-tenant.

    Attributes:
        nombre: Nombre legible de la institución.
    """

    __tablename__ = "tenant"

    nombre = Column(String(255), nullable=False)
