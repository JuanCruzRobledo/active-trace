"""Tests for the Tenant model — foundation of multi-tenant isolation."""

from uuid import uuid4


class TestTenantModelAttrs:
    """Tenant model SHOULD inherit from BaseMixin and have name field."""

    def test_tenant_inherits_base_mixin(self):
        """Tenant SHOULD inherit BaseMixin (id, tenant_id, timestamps, soft_delete)."""
        from app.models.tenant import Tenant  # noqa: PLC0415
        from app.models.base import BaseMixin  # noqa: PLC0415

        assert issubclass(Tenant, BaseMixin)

    def test_tenant_has_name_column(self):
        """Tenant SHOULD have a 'name' column."""
        from app.models.tenant import Tenant  # noqa: PLC0415
        from sqlalchemy import String  # noqa: PLC0415

        name_col = Tenant.__table__.columns["nombre"]
        assert isinstance(name_col.type, String)

    def test_tenant_has_tablename(self):
        """Tenant SHOULD have __tablename__ = 'tenant'."""
        from app.models.tenant import Tenant  # noqa: PLC0415

        assert Tenant.__tablename__ == "tenant"

    def test_tenant_has_tenant_id_self_reference(self):
        """Tenant's tenant_id SHOULD reference its own id (root tenant pattern)."""
        from app.models.tenant import Tenant  # noqa: PLC0415

        # Multi-tenant: Tenant is the root entity; its tenant_id = its own id
        tenant_id_col = Tenant.__table__.columns["tenant_id"]
        assert tenant_id_col is not None
        assert not tenant_id_col.nullable

    def test_tenant_creates_tenant_id_index(self):
        """Tenant SHOULD have an index on tenant_id (from BaseMixin)."""
        from app.models.tenant import Tenant  # noqa: PLC0415

        indexes = Tenant.__table__.indexes
        index_names = {idx.name for idx in indexes}
        assert any("tenant_id" in name for name in index_names)

    def test_tenant_name_is_not_nullable(self):
        """Tenant name SHOULD be NOT NULL."""
        from app.models.tenant import Tenant  # noqa: PLC0415

        name_col = Tenant.__table__.columns["nombre"]
        assert not name_col.nullable

    def test_tenant_name_max_length(self):
        """Tenant name SHOULD have a max length."""
        from app.models.tenant import Tenant  # noqa: PLC0415
        from sqlalchemy import String  # noqa: PLC0415

        name_col = Tenant.__table__.columns["nombre"]
        assert isinstance(name_col.type, String)
        assert name_col.type.length is not None


class TestTenantInstantiation:
    """Tenant SHOULD be instantiable and hold data."""

    def test_tenant_instantiation(self):
        """A Tenant instance SHOULD hold id, tenant_id, name."""
        from app.models.tenant import Tenant  # noqa: PLC0415

        tenant_id = uuid4()
        tenant = Tenant(
            id=tenant_id,
            tenant_id=tenant_id,  # Self-reference: root tenant
            nombre="Test Institution",
        )
        assert tenant.id == tenant_id
        assert tenant.tenant_id == tenant_id
        assert tenant.nombre == "Test Institution"
        # created_at / updated_at son column-level defaults (se setean al INSERT)
        assert tenant.deleted_at is None  # Active by default

    def test_tenant_default_active(self):
        """A new Tenant SHOULD be active (deleted_at is None)."""
        from app.models.tenant import Tenant  # noqa: PLC0415

        tid = uuid4()
        tenant = Tenant(id=tid, tenant_id=tid, nombre="Auto")
        assert tenant.deleted_at is None
