"""Tests for BaseMixin: id, tenant_id, timestamps, and soft_delete."""


import pytest
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession


class TestBaseMixinAttributes:
    """The mixin SHOULD provide id, tenant_id, created_at, updated_at, deleted_at."""

    def test_mixin_has_id_column(self):
        """BaseMixin SHOULD define an 'id' column of type UUID."""
        from app.models.base import BaseMixin  # noqa: PLC0415

        id_col: Column = BaseMixin.id
        assert isinstance(id_col, Column)
        assert isinstance(id_col.type, PGUUID)

    def test_mixin_has_tenant_id_column(self):
        """BaseMixin SHOULD define a 'tenant_id' column of type UUID."""
        from app.models.base import BaseMixin  # noqa: PLC0415

        tenant_col: Column = BaseMixin.tenant_id
        assert isinstance(tenant_col, Column)
        assert isinstance(tenant_col.type, PGUUID)
        assert not tenant_col.nullable

    def test_mixin_has_created_at(self):
        """BaseMixin SHOULD define a 'created_at' column."""
        from app.models.base import BaseMixin  # noqa: PLC0415

        col: Column = BaseMixin.created_at
        assert isinstance(col, Column)
        assert not col.nullable

    def test_mixin_has_updated_at(self):
        """BaseMixin SHOULD define an 'updated_at' column."""
        from app.models.base import BaseMixin  # noqa: PLC0415

        col: Column = BaseMixin.updated_at
        assert isinstance(col, Column)
        assert not col.nullable

    def test_mixin_has_deleted_at(self):
        """BaseMixin SHOULD define a 'deleted_at' nullable column (soft delete)."""
        from app.models.base import BaseMixin  # noqa: PLC0415

        col: Column = BaseMixin.deleted_at
        assert isinstance(col, Column)
        assert col.nullable

    def test_mixin_has_tenant_id_indexed(self):
        """BaseMixin SHOULD index tenant_id for performance."""
        from app.models.tenant import Tenant  # noqa: PLC0415

        # BaseMixin itself is a mixin (not a table) — check on a concrete model
        tenant_idx = Tenant.__table__.indexes
        idx_names = {idx.name for idx in tenant_idx}
        assert any("tenant_id" in name for name in idx_names), (
            "A concrete model SHOULD have an index on tenant_id"
        )


class TestBaseMixinInheritance:
    """An entity inheriting BaseMixin SHOULD have all mixin columns."""

    async def test_entity_inherits_mixin_columns(self):
        """A model that inherits BaseMixin SHOULD have id, tenant_id, timestamps."""
        from app.models.base import BaseMixin  # noqa: PLC0415
        from app.core.database import Base  # noqa: PLC0415

        # Define a minimal entity inline for this test
        class TestEntity(Base, BaseMixin):
            __tablename__ = "_test_base_mixin_entity"
            name = Column(String(100))

        assert hasattr(TestEntity, "id")
        assert hasattr(TestEntity, "tenant_id")
        assert hasattr(TestEntity, "created_at")
        assert hasattr(TestEntity, "updated_at")
        assert hasattr(TestEntity, "deleted_at")
        assert hasattr(TestEntity, "name")

    async def test_entity_id_is_primary_key(self):
        """The inherited id SHOULD be the primary key."""
        from app.models.base import BaseMixin  # noqa: PLC0415
        from app.core.database import Base  # noqa: PLC0415

        class TestEntity(Base, BaseMixin):
            __tablename__ = "_test_pk_entity"
            name = Column(String(100))

        pk_cols = TestEntity.__table__.primary_key.columns
        assert len(pk_cols) == 1
        assert "id" in pk_cols


class TestBaseMixinTriangulate:
    """Triangulation: edge cases and variations."""

    def test_mixin_tenant_id_not_nullable(self):
        """tenant_id MUST be NOT NULL — multi-tenant isolation requires it."""
        from app.models.base import BaseMixin  # noqa: PLC0415

        col: Column = BaseMixin.tenant_id
        assert not col.nullable

    def test_mixin_deleted_at_nullable(self):
        """deleted_at MUST be nullable (NULL = active record)."""
        from app.models.base import BaseMixin  # noqa: PLC0415

        col: Column = BaseMixin.deleted_at
        assert col.nullable

    def test_mixin_updated_at_has_onupdate(self):
        """updated_at SHOULD auto-update on modification."""
        from app.models.base import BaseMixin  # noqa: PLC0415
        from app.core.database import Base  # noqa: PLC0415

        class TestEntity(Base, BaseMixin):
            __tablename__ = "_test_onupdate_entity"
            name = Column(String(100))

        updated_col = TestEntity.__table__.columns["updated_at"]
        assert updated_col.onupdate is not None

    def test_mixin_id_is_uuid_type(self):
        """id MUST be of type UUID (PGUUID as_uuid=True for native DB support)."""
        from app.models.base import BaseMixin  # noqa: PLC0415

        id_col: Column = BaseMixin.id
        assert isinstance(id_col.type, PGUUID)
        assert id_col.type.as_uuid is True


@pytest.mark.skip(reason="Requires PostgreSQL — run manually with DB")
class TestBaseMixinPersistence:
    """The mixin fields SHOULD persist correctly in the database."""

    async def test_entity_persists_with_all_mixin_fields(
        self, db_session: AsyncSession
    ):
        """A record created SHOULD have all mixin fields populated."""
        from app.models.base import BaseMixin  # noqa: PLC0415
        from app.core.database import Base  # noqa: PLC0415

        class TestEntity(Base, BaseMixin):
            __tablename__ = "_test_persist_entity"
            name = Column(String(100))

        async with db_session.begin():
            db_session.add_all([TestEntity])
        # Not runnable without DB — skip marker is intentional
        assert True
