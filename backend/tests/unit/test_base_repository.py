"""Tests for BaseRepository[T] generic — tenant scope enforcement and CRUD."""

import inspect
from uuid import uuid4

from sqlalchemy import select


class TestBaseRepositoryStructure:
    """BaseRepository SHOULD be generic over model type and accept tenant_id."""

    def test_repository_accepts_tenant_id(self):
        """BaseRepository SHOULD require tenant_id at construction."""
        from app.repositories.base import BaseRepository  # noqa: PLC0415
        from tests.fixtures.models import DummyEntity  # noqa: PLC0415

        repo = BaseRepository(session=None, model=DummyEntity, tenant_id=uuid4())
        assert repo.tenant_id is not None

    def test_repository_stores_model(self):
        """BaseRepository SHOULD store the model class."""
        from app.repositories.base import BaseRepository  # noqa: PLC0415
        from tests.fixtures.models import DummyEntity  # noqa: PLC0415

        repo = BaseRepository(session=None, model=DummyEntity, tenant_id=uuid4())
        assert repo.model is DummyEntity

    def test_repository_stores_session(self):
        """BaseRepository SHOULD store the session reference."""
        from app.repositories.base import BaseRepository  # noqa: PLC0415
        from tests.fixtures.models import DummyEntity  # noqa: PLC0415

        repo = BaseRepository(session=None, model=DummyEntity, tenant_id=uuid4())
        assert repo.session is None  # None is valid for structural tests

    def test_repository_get_by_id_signature(self):
        """get_by_id SHOULD accept a UUID and return Optional[model]."""
        from app.repositories.base import BaseRepository  # noqa: PLC0415
        from tests.fixtures.models import DummyEntity  # noqa: PLC0415

        repo = BaseRepository(session=None, model=DummyEntity, tenant_id=uuid4())
        sig = inspect.signature(repo.get_by_id)
        assert "id" in sig.parameters

    def test_repository_list_all_signature(self):
        """list_all SHOULD return a list of model instances."""
        from app.repositories.base import BaseRepository  # noqa: PLC0415
        from tests.fixtures.models import DummyEntity  # noqa: PLC0415

        repo = BaseRepository(session=None, model=DummyEntity, tenant_id=uuid4())
        assert hasattr(repo, "list_all")
        assert callable(repo.list_all)

    def test_repository_has_soft_delete_method(self):
        """soft_delete SHOULD be an async method."""
        from app.repositories.base import BaseRepository  # noqa: PLC0415
        from tests.fixtures.models import DummyEntity  # noqa: PLC0415

        repo = BaseRepository(session=None, model=DummyEntity, tenant_id=uuid4())
        assert hasattr(repo, "soft_delete")
        assert callable(repo.soft_delete)

    def test_repository_has_save_method(self):
        """save SHOULD be an async method."""
        from app.repositories.base import BaseRepository  # noqa: PLC0415
        from tests.fixtures.models import DummyEntity  # noqa: PLC0415

        repo = BaseRepository(session=None, model=DummyEntity, tenant_id=uuid4())
        assert hasattr(repo, "save")
        assert callable(repo.save)


class TestBaseRepositoryScope:
    """Tenant scope MUST be enforced in all queries."""

    def test_get_by_id_filters_tenant(self):
        """get_by_id SHOULD include tenant_id in the WHERE clause."""
        from app.repositories.base import BaseRepository  # noqa: PLC0415
        from tests.fixtures.models import DummyEntity  # noqa: PLC0415

        tid = uuid4()
        repo = BaseRepository(session=None, model=DummyEntity, tenant_id=tid)
        stmt = repo._scope_query(select(DummyEntity))
        sql_str = str(stmt)
        assert "tenant_id" in sql_str

    def test_list_all_includes_tenant_scope(self):
        """list_all SHOULD generate a query scoped to tenant."""
        from app.repositories.base import BaseRepository  # noqa: PLC0415
        from tests.fixtures.models import DummyEntity  # noqa: PLC0415

        tid = uuid4()
        repo = BaseRepository(session=None, model=DummyEntity, tenant_id=tid)
        stmt = repo._scope_query(repo._list_query())
        sql_str = str(stmt)
        assert "tenant_id" in sql_str

    def test_different_tenants_have_different_scope(self):
        """Two repos with different tenant_ids SHOULD produce different scopes."""
        from app.repositories.base import BaseRepository  # noqa: PLC0415
        from tests.fixtures.models import DummyEntity  # noqa: PLC0415

        tid_a, tid_b = uuid4(), uuid4()
        repo_a = BaseRepository(session=None, model=DummyEntity, tenant_id=tid_a)
        repo_b = BaseRepository(session=None, model=DummyEntity, tenant_id=tid_b)

        stmt_a = repo_a._scope_query(select(DummyEntity))
        stmt_b = repo_b._scope_query(select(DummyEntity))

        compiled_a = stmt_a.compile(compile_kwargs={"literal_binds": True})
        compiled_b = stmt_b.compile(compile_kwargs={"literal_binds": True})
        assert str(compiled_a) != str(compiled_b)

    def test_soft_delete_is_part_of_default_scope(self):
        """_scope_query SHOULD include deleted_at IS NULL by default."""
        from app.repositories.base import BaseRepository  # noqa: PLC0415
        from tests.fixtures.models import DummyEntity  # noqa: PLC0415

        repo = BaseRepository(session=None, model=DummyEntity, tenant_id=uuid4())
        stmt = repo._scope_query(select(DummyEntity))
        sql_str = str(stmt).lower()
        assert "deleted_at" in sql_str
