"""Tests combinados de soft delete y aislamiento multi-tenant.

Requiere PostgreSQL real (``DATABASE_URL_TEST`` en el entorno).
"""

import uuid
from datetime import datetime, timezone

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


class TestSoftDeleteMultiTenant:
    """Verifica que soft delete y multi-tenant interactúan correctamente."""

    async def _seed_tenant_with_entities(
        self, session, nombre: str, count: int = 2
    ) -> tuple[Tenant, list[DummyEntity]]:
        """Crea un tenant con N entidades."""
        tid = uuid.uuid4()
        tenant = Tenant(id=tid, tenant_id=tid, nombre=nombre)
        session.add(tenant)
        entities = []
        for i in range(count):
            e = DummyEntity(
                id=uuid.uuid4(),
                tenant_id=tid,
                label=f"{nombre}_e{i}",
            )
            session.add(e)
            entities.append(e)
        await session.flush()
        return tenant, entities

    async def test_delete_in_one_tenant_does_not_affect_other(
        self, db_session
    ) -> None:
        """GIVEN T1 y T2 con entidades WHEN soft-delete en T1 THEN T2
        no ve cambios."""
        t1, [t1_a, t1_b] = await self._seed_tenant_with_entities(
            db_session, "OnlyT1", 2
        )
        t2, [t2_a, t2_b] = await self._seed_tenant_with_entities(
            db_session, "OnlyT2", 2
        )

        # Soft-delete T1's first entity
        t1_b.deleted_at = datetime.now(timezone.utc)
        await db_session.flush()

        # T1 solo ve la activa
        stmt_t1 = (
            select(DummyEntity)
            .where(DummyEntity.tenant_id == t1.id)
            .where(DummyEntity.deleted_at.is_(None))
        )
        result_t1 = await db_session.execute(stmt_t1)
        t1_rows = list(result_t1.scalars().all())
        t1_labels = {r.label for r in t1_rows}
        assert len(t1_rows) == 1
        assert "OnlyT1_e0" in t1_labels
        assert "OnlyT1_e1" not in t1_labels

        # T2 sigue viendo sus 2 activas
        stmt_t2 = (
            select(DummyEntity)
            .where(DummyEntity.tenant_id == t2.id)
            .where(DummyEntity.deleted_at.is_(None))
        )
        result_t2 = await db_session.execute(stmt_t2)
        t2_rows = list(result_t2.scalars().all())
        assert len(t2_rows) == 2

    async def test_soft_deleted_cross_tenant_get_by_id(
        self, db_session
    ) -> None:
        """GIVEN entidad-deleted en T1 WHEN get_by_id en T2 con su ID
        THEN no se ve (doble restricción: tenant + soft delete)."""
        t1, [e1, _] = await self._seed_tenant_with_entities(
            db_session, "CrossDel", 2
        )
        t2, _ = await self._seed_tenant_with_entities(
            db_session, "CrossDel2", 1
        )

        # Soft-delete T1 entity
        e1.deleted_at = datetime.now(timezone.utc)
        await db_session.flush()

        # Buscar con T2 scope + deleted filter
        stmt = (
            select(DummyEntity)
            .where(DummyEntity.id == e1.id)
            .where(DummyEntity.tenant_id == t2.id)
            .where(DummyEntity.deleted_at.is_(None))
        )
        result = await db_session.execute(stmt)
        loaded = result.scalar_one_or_none()
        assert loaded is None, (
            "No debería ver entidad de otro tenant aunque esté activa"
        )

    async def test_tenant_active_count_after_mixed_deletes(
        self, db_session
    ) -> None:
        """GIVEN T1(3) + T2(3) WHEN soft-delete 1 de T1 + 2 de T2 THEN
        cada tenant tiene los activos correctos."""
        t1, t1_entities = await self._seed_tenant_with_entities(
            db_session, "Mixed_A", 3
        )
        t2, t2_entities = await self._seed_tenant_with_entities(
            db_session, "Mixed_B", 3
        )

        # Soft-delete 1 de T1, 2 de T2
        t1_entities[0].deleted_at = datetime.now(timezone.utc)
        t2_entities[0].deleted_at = datetime.now(timezone.utc)
        t2_entities[1].deleted_at = datetime.now(timezone.utc)
        await db_session.flush()

        for tid, expected, name in [
            (t1.id, 2, "T1"),
            (t2.id, 1, "T2"),
        ]:
            stmt = (
                select(DummyEntity)
                .where(DummyEntity.tenant_id == tid)
                .where(DummyEntity.deleted_at.is_(None))
            )
            result = await db_session.execute(stmt)
            rows = list(result.scalars().all())
            assert len(rows) == expected, (
                f"{name} debería tener {expected} activas, "
                f"tiene {len(rows)}"
            )
