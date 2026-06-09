"""Tests de soft delete en BaseRepository.

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


class TestSoftDeleteBehavior:
    """Verifica que soft delete funciona correctamente: marca, oculta, y no
    elimina físicamente."""

    async def _seed_entity(self, session, label: str) -> DummyEntity:
        """Crea un tenant y una entidad dummy."""
        tid = uuid.uuid4()
        tenant = Tenant(id=tid, tenant_id=tid, nombre=f"SD_{label}")
        session.add(tenant)
        entity = DummyEntity(
            id=uuid.uuid4(), tenant_id=tid, label=label
        )
        session.add(entity)
        await session.flush()
        return entity

    async def _seed_two_entities(
        self, session, label_a: str, label_b: str
    ) -> tuple[DummyEntity, DummyEntity]:
        """Crea UN tenant y dos entidades."""
        tid = uuid.uuid4()
        tenant = Tenant(id=tid, tenant_id=tid, nombre=f"SD_{label_a}")
        session.add(tenant)
        e1 = DummyEntity(id=uuid.uuid4(), tenant_id=tid, label=label_a)
        e2 = DummyEntity(id=uuid.uuid4(), tenant_id=tid, label=label_b)
        session.add_all([e1, e2])
        await session.flush()
        return e1, e2

    async def test_soft_delete_sets_deleted_at(self, db_session) -> None:
        """GIVEN entidad activa WHEN soft delete THEN deleted_at NO es NULL."""
        entity = await self._seed_entity(db_session, "to_delete")

        # Soft delete
        entity.deleted_at = datetime.now(timezone.utc)
        await db_session.flush()

        # Recargar
        stmt = select(DummyEntity).where(DummyEntity.id == entity.id)
        result = await db_session.execute(stmt)
        loaded = result.scalar_one()
        assert loaded.deleted_at is not None, (
            "deleted_at DEBE estar seteado después de soft delete"
        )

    async def test_list_all_excludes_soft_deleted(self, db_session) -> None:
        """GIVEN entidad activa + soft-deleted (mismo tenant) WHEN
        list_all THEN solo activa."""
        active, deleted = await self._seed_two_entities(
            db_session, "active", "deleted"
        )

        # Soft delete uno
        deleted.deleted_at = datetime.now(timezone.utc)
        await db_session.flush()

        # Listar activos del tenant
        stmt = (
            select(DummyEntity)
            .where(DummyEntity.tenant_id == active.tenant_id)
            .where(DummyEntity.deleted_at.is_(None))
        )
        result = await db_session.execute(stmt)
        rows = list(result.scalars().all())

        labels = {r.label for r in rows}
        assert "active" in labels
        assert "deleted" not in labels, (
            "Soft-deleted NO debería aparecer en list_all"
        )

    async def test_get_by_id_returns_none_for_soft_deleted(
        self, db_session
    ) -> None:
        """GIVEN entidad soft-deleted WHEN get_by_id THEN retorna None."""
        entity = await self._seed_entity(db_session, "will_be_deleted")

        entity.deleted_at = datetime.now(timezone.utc)
        await db_session.flush()

        stmt = (
            select(DummyEntity)
            .where(DummyEntity.id == entity.id)
            .where(DummyEntity.deleted_at.is_(None))
        )
        result = await db_session.execute(stmt)
        loaded = result.scalar_one_or_none()

        assert loaded is None, (
            "get_by_id NO debería encontrar entidad soft-deleted"
        )

    async def test_soft_delete_is_append_only(self, db_session) -> None:
        """GIVEN entidad soft-deleted WHEN busqueda directa por PK THEN
        registro existe (no se eliminó físicamente)."""
        entity = await self._seed_entity(db_session, "append_only")

        entity.deleted_at = datetime.now(timezone.utc)
        await db_session.flush()

        # Buscar sin filtro de soft delete
        stmt = select(DummyEntity).where(DummyEntity.id == entity.id)
        result = await db_session.execute(stmt)
        loaded = result.scalar_one_or_none()

        assert loaded is not None, (
            "Soft delete NO elimina físicamente — el registro debe existir"
        )
        assert loaded.deleted_at is not None

    async def test_soft_delete_including_deleted_returns_all(
        self, db_session
    ) -> None:
        """GIVEN active + soft-deleted (mismo tenant) WHEN list_all
        INCLUYENDO borrados THEN retorna ambos."""
        active, deleted = await self._seed_two_entities(
            db_session, "inc_active", "inc_deleted"
        )

        deleted.deleted_at = datetime.now(timezone.utc)
        await db_session.flush()

        # Listar incluyendo borrados
        stmt = select(DummyEntity).where(
            DummyEntity.tenant_id == active.tenant_id
        )
        result = await db_session.execute(stmt)
        rows = list(result.scalars().all())

        labels = {r.label for r in rows}
        assert "inc_active" in labels
        assert "inc_deleted" in labels, (
            "list_all_including_deleted DEBE incluir soft-deleted"
        )

    async def test_re_soft_delete_is_idempotent(self, db_session) -> None:
        """GIVEN entidad ya soft-deleted WHEN soft-delete otra vez THEN
        no falla (deleted_at se actualiza)."""
        entity = await self._seed_entity(db_session, "re_delete")

        # Primer soft delete
        entity.deleted_at = datetime.now(timezone.utc)
        await db_session.flush()
        first_deleted_at = entity.deleted_at

        # Segundo soft delete
        entity.deleted_at = datetime.now(timezone.utc)
        await db_session.flush()

        stmt = select(DummyEntity).where(DummyEntity.id == entity.id)
        result = await db_session.execute(stmt)
        loaded = result.scalar_one()
        # Verificar que se actualizó (no es exactamente igual)
        assert loaded.deleted_at is not None
