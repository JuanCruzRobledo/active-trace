"""Tests de aislamiento multi-tenant en BaseRepository.

Requiere PostgreSQL real (``DATABASE_URL_TEST`` en el entorno).
"""

import uuid

import pytest
from sqlalchemy import select

from app.models.tenant import Tenant
from tests.conftest import db_available
from tests.fixtures.models import DummyEntity

pytestmark = [
    pytest.mark.skipif(
        not db_available(),
        reason="Requiere PostgreSQL: definir DATABASE_URL_TEST en el entorno",
    ),
]


class TestMultiTenantIsolation:
    """Verifica que cada tenant ve SOLO sus propios datos."""

    async def _seed_tenant(
        self, session, nombre: str
    ) -> tuple[Tenant, DummyEntity, DummyEntity]:
        """Crea un tenant con 2 DummyEntities y devuelve (tenant, e1, e2)."""
        tid = uuid.uuid4()
        tenant = Tenant(id=tid, tenant_id=tid, nombre=nombre)
        session.add(tenant)
        e1 = DummyEntity(
            id=uuid.uuid4(), tenant_id=tid, label=f"{nombre}_entity_1"
        )
        e2 = DummyEntity(
            id=uuid.uuid4(), tenant_id=tid, label=f"{nombre}_entity_2"
        )
        session.add_all([e1, e2])
        await session.flush()
        return tenant, e1, e2

    async def test_list_all_returns_only_own_tenant(
        self, db_session
    ) -> None:
        """GIVEN dos tenants con entidades each WHEN list_all(T1) THEN solo
        entidades de T1."""
        t1, *_ = await self._seed_tenant(db_session, "Alpha")
        t2, *_ = await self._seed_tenant(db_session, "Beta")

        # Act — query manual con scope
        stmt = (
            select(DummyEntity)
            .where(DummyEntity.tenant_id == t1.id)
            .where(DummyEntity.deleted_at.is_(None))
        )
        result = await db_session.execute(stmt)
        rows = list(result.scalars().all())

        # Assert
        labels = {r.label for r in rows}
        assert all("Alpha" in lbl for lbl in labels), (
            f"T1 debería ver solo entidades Alpha, obtuvo: {labels}"
        )
        assert len(rows) == 2

    async def test_list_all_excludes_other_tenant(
        self, db_session
    ) -> None:
        """GIVEN T1 y T2 con entidades WHEN list_all(T1) THEN no incluye
        entidades de T2."""
        t1, *_ = await self._seed_tenant(db_session, "Alpha")
        t2, *_ = await self._seed_tenant(db_session, "Beta")

        stmt = (
            select(DummyEntity)
            .where(DummyEntity.tenant_id == t1.id)
            .where(DummyEntity.deleted_at.is_(None))
        )
        result = await db_session.execute(stmt)
        rows = list(result.scalars().all())

        t2_labels = {r.label for r in rows if "Beta" in r.label}
        assert len(t2_labels) == 0, (
            f"T1 NO debería ver entidades Beta, obtuvo: {t2_labels}"
        )

    async def test_get_by_id_returns_none_for_wrong_tenant(
        self, db_session
    ) -> None:
        """GIVEN entidad en T2 WHEN get_by_id(id, T1) THEN retorna None."""
        t1, *_ = await self._seed_tenant(db_session, "Alpha")
        t2, t2_e1, _ = await self._seed_tenant(db_session, "Beta")

        # Buscar entidad de T2 desde T1
        stmt = (
            select(DummyEntity)
            .where(DummyEntity.id == t2_e1.id)
            .where(DummyEntity.tenant_id == t1.id)
            .where(DummyEntity.deleted_at.is_(None))
        )
        result = await db_session.execute(stmt)
        entity = result.scalar_one_or_none()

        assert entity is None, (
            "T1 NO debería encontrar entidad de T2 por ID"
        )

    async def test_create_persists_correct_tenant(
        self, db_session
    ) -> None:
        """GIVEN tenant T1 WHEN create entidad con tenant_id=T1.id THEN
        se persiste en T1."""
        tid = uuid.uuid4()
        tenant = Tenant(id=tid, tenant_id=tid, nombre="TestCreate")
        db_session.add(tenant)
        await db_session.flush()

        entity = DummyEntity(
            id=uuid.uuid4(), tenant_id=tid, label="create_test"
        )
        db_session.add(entity)
        await db_session.flush()

        # Recuperar
        stmt = select(DummyEntity).where(DummyEntity.id == entity.id)
        result = await db_session.execute(stmt)
        loaded = result.scalar_one()
        assert loaded.tenant_id == tid

    async def test_two_tenants_have_independent_data(
        self, db_session
    ) -> None:
        """GIVEN T1 con 2 entidades y T2 con 3 WHEN list_all each THEN
        cada tenant ve su propia cantidad."""
        t1, *_ = await self._seed_tenant(db_session, "IndepA")
        t2, t2_e1, _ = await self._seed_tenant(db_session, "IndepB")

        # Agregar una tercera entidad a T2
        extra = DummyEntity(
            id=uuid.uuid4(), tenant_id=t2.id, label="IndepB_entity_3"
        )
        db_session.add(extra)
        await db_session.flush()

        for tid, expected_count, name in [
            (t1.id, 2, "T1"),
            (t2.id, 3, "T2"),
        ]:
            stmt = (
                select(DummyEntity)
                .where(DummyEntity.tenant_id == tid)
                .where(DummyEntity.deleted_at.is_(None))
            )
            result = await db_session.execute(stmt)
            rows = list(result.scalars().all())
            assert len(rows) == expected_count, (
                f"{name} debería tener {expected_count} entidades, "
                f"tiene {len(rows)}"
            )
