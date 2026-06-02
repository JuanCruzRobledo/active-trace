"""Tests de integración para BaseRepository contra PostgreSQL real.

Ejercita los 4 métodos públicos (``get_by_id``, ``list_all``, ``save``,
``soft_delete``) a través del repositorio — no con SQL directo — para
garantizar que el scope multi-tenant y soft delete funcionan en runtime.
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.models.tenant import Tenant
from app.repositories.base import BaseRepository
from tests.conftest import db_available
from tests.fixtures.models import DummyEntity

pytestmark = [
    pytest.mark.skipif(
        not db_available(),
        reason="Requiere PostgreSQL: definir DATABASE_URL_TEST en el entorno",
    ),
]


@pytest_asyncio.fixture
async def tenant(db_session) -> Tenant:
    """Crea un tenant raíz."""
    tid = uuid.uuid4()
    tenant = Tenant(id=tid, tenant_id=tid, nombre="RepoTest")
    db_session.add(tenant)
    await db_session.flush()
    return tenant


@pytest_asyncio.fixture
async def tenant_b(db_session) -> Tenant:
    """Segundo tenant para tests de aislamiento."""
    tid = uuid.uuid4()
    tenant = Tenant(id=tid, tenant_id=tid, nombre="RepoTestB")
    db_session.add(tenant)
    await db_session.flush()
    return tenant


def _make_repo(
    db_session, tenant: Tenant,
) -> BaseRepository[DummyEntity]:
    """Construye un repositorio para DummyEntity scoped al tenant."""
    return BaseRepository[DummyEntity](
        session=db_session,
        model=DummyEntity,
        tenant_id=tenant.id,
    )


class TestBaseRepositoryIntegration:
    """Ejercita BaseRepository contra PostgreSQL real."""

    # ── list_all ───────────────────────────────────────────────────────

    async def test_list_all_returns_entities_for_tenant(
        self, db_session, tenant: Tenant,
    ) -> None:
        """GIVEN repositorio con tenant WHEN list_all THEN retorna
        entidades del tenant."""
        repo = _make_repo(db_session, tenant)
        e1 = DummyEntity(id=uuid.uuid4(), tenant_id=tenant.id, label="L1")
        e2 = DummyEntity(id=uuid.uuid4(), tenant_id=tenant.id, label="L2")
        db_session.add_all([e1, e2])
        await db_session.flush()

        results = await repo.list_all()

        assert len(results) == 2
        labels = {r.label for r in results}
        assert "L1" in labels
        assert "L2" in labels

    async def test_list_all_excludes_other_tenant(
        self, db_session, tenant: Tenant, tenant_b: Tenant,
    ) -> None:
        """GIVEN T1 y T2 con entidades WHEN repo de T1.list_all THEN
        no incluye entidades de T2."""
        repo_t1 = _make_repo(db_session, tenant)
        DummyEntity(id=uuid.uuid4(), tenant_id=tenant_b.id, label="T2_only")
        db_session.add(DummyEntity(id=uuid.uuid4(), tenant_id=tenant.id, label="T1_only"))
        await db_session.flush()

        results = await repo_t1.list_all()
        labels = {r.label for r in results}
        assert "T1_only" in labels
        assert "T2_only" not in labels

    async def test_list_all_empty_when_no_entities(
        self, db_session, tenant: Tenant,
    ) -> None:
        """GIVEN repositorio en tenant sin entidades WHEN list_all THEN
        lista vacía."""
        repo = _make_repo(db_session, tenant)
        results = await repo.list_all()
        assert results == []

    # ── get_by_id ──────────────────────────────────────────────────────

    async def test_get_by_id_returns_entity(
        self, db_session, tenant: Tenant,
    ) -> None:
        """GIVEN entidad persistida WHEN get_by_id(id) THEN retorna la
        entidad."""
        repo = _make_repo(db_session, tenant)
        entity = DummyEntity(
            id=uuid.uuid4(), tenant_id=tenant.id, label="get_by_id_1"
        )
        db_session.add(entity)
        await db_session.flush()

        loaded = await repo.get_by_id(entity.id)
        assert loaded is not None
        assert loaded.label == "get_by_id_1"

    async def test_get_by_id_returns_none_for_nonexistent(
        self, db_session, tenant: Tenant,
    ) -> None:
        """GIVEN repositorio con tenant WHEN get_by_id(id_inexistente)
        THEN retorna None."""
        repo = _make_repo(db_session, tenant)
        loaded = await repo.get_by_id(uuid.uuid4())
        assert loaded is None

    async def test_get_by_id_respects_tenant_scope(
        self, db_session, tenant: Tenant, tenant_b: Tenant,
    ) -> None:
        """GIVEN entidad en T2 WHEN get_by_id(id, T1) THEN retorna
        None."""
        repo_t1 = _make_repo(db_session, tenant)
        t2_entity = DummyEntity(
            id=uuid.uuid4(), tenant_id=tenant_b.id, label="T2_secret"
        )
        db_session.add(t2_entity)
        await db_session.flush()

        loaded = await repo_t1.get_by_id(t2_entity.id)
        assert loaded is None, (
            "Repo de T1 NO debe encontrar entidad de T2 por ID"
        )

    # ── save ───────────────────────────────────────────────────────────

    async def test_save_persists_entity(
        self, db_session, tenant: Tenant,
    ) -> None:
        """GIVEN repositorio WHEN save(entidad) THEN entidad se persiste
        y puede recuperarse."""
        repo = _make_repo(db_session, tenant)
        entity = DummyEntity(
            id=uuid.uuid4(), tenant_id=tenant.id, label="saved"
        )

        saved = await repo.save(entity)

        assert saved.id == entity.id
        # Verificar que está en DB
        stmt = select(DummyEntity).where(DummyEntity.id == entity.id)
        result = await db_session.execute(stmt)
        loaded = result.scalar_one()
        assert loaded.label == "saved"

    async def test_save_updates_existing_entity(
        self, db_session, tenant: Tenant,
    ) -> None:
        """GIVEN entidad persistida WHEN save con cambios THEN cambios
        se persisten."""
        repo = _make_repo(db_session, tenant)
        entity = DummyEntity(
            id=uuid.uuid4(), tenant_id=tenant.id, label="original"
        )
        await repo.save(entity)

        # Modificar y guardar de nuevo
        entity.label = "updated"
        await repo.save(entity)

        stmt = select(DummyEntity).where(DummyEntity.id == entity.id)
        result = await db_session.execute(stmt)
        loaded = result.scalar_one()
        assert loaded.label == "updated"

    # ── soft_delete ────────────────────────────────────────────────────

    async def test_soft_delete_marks_deleted_at(
        self, db_session, tenant: Tenant,
    ) -> None:
        """GIVEN entidad activa WHEN soft_delete THEN deleted_at se
        setea."""
        repo = _make_repo(db_session, tenant)
        entity = DummyEntity(
            id=uuid.uuid4(), tenant_id=tenant.id, label="to_delete"
        )
        await repo.save(entity)

        await repo.soft_delete(entity)

        assert entity.deleted_at is not None

    async def test_soft_delete_excludes_from_list_all(
        self, db_session, tenant: Tenant,
    ) -> None:
        """GIVEN entidad soft-deleteada WHEN list_all THEN NO aparece."""
        repo = _make_repo(db_session, tenant)
        e1 = DummyEntity(id=uuid.uuid4(), tenant_id=tenant.id, label="keep")
        e2 = DummyEntity(
            id=uuid.uuid4(), tenant_id=tenant.id, label="remove"
        )
        await repo.save(e1)
        await repo.save(e2)

        await repo.soft_delete(e2)
        results = await repo.list_all()

        labels = {r.label for r in results}
        assert "keep" in labels
        assert "remove" not in labels

    async def test_soft_delete_excludes_from_get_by_id(
        self, db_session, tenant: Tenant,
    ) -> None:
        """GIVEN entidad soft-deleteada WHEN get_by_id THEN None."""
        repo = _make_repo(db_session, tenant)
        entity = DummyEntity(
            id=uuid.uuid4(), tenant_id=tenant.id, label="gone"
        )
        await repo.save(entity)

        await repo.soft_delete(entity)
        loaded = await repo.get_by_id(entity.id)

        assert loaded is None

    async def test_soft_delete_then_list_all_multi_tenant(
        self, db_session, tenant: Tenant, tenant_b: Tenant,
    ) -> None:
        """GIVEN entidad soft-deleteada en T1 WHEN repo de T2.list_all
        THEN T2 activas no se ven afectadas."""
        repo_t1 = _make_repo(db_session, tenant)
        repo_t2 = _make_repo(db_session, tenant_b)

        t1_active = DummyEntity(
            id=uuid.uuid4(), tenant_id=tenant.id, label="T1_active"
        )
        t1_deleted = DummyEntity(
            id=uuid.uuid4(), tenant_id=tenant.id, label="T1_deleted"
        )
        t2_active = DummyEntity(
            id=uuid.uuid4(), tenant_id=tenant_b.id, label="T2_active"
        )
        db_session.add_all([t1_active, t1_deleted, t2_active])
        await db_session.flush()

        # Soft-delete T1 entity via repo
        await repo_t1.soft_delete(t1_deleted)

        t1_results = await repo_t1.list_all()
        t1_labels = {r.label for r in t1_results}
        assert "T1_active" in t1_labels
        assert "T1_deleted" not in t1_labels
        assert len(t1_results) == 1

        t2_results = await repo_t2.list_all()
        t2_labels = {r.label for r in t2_results}
        assert "T2_active" in t2_labels
        assert len(t2_results) == 1
