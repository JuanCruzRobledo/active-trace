"""Test integral que combina multi-tenant, soft delete y cifrado.

Requiere PostgreSQL real (``DATABASE_URL_TEST`` en el entorno).
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.models.tenant import Tenant
from tests.conftest import db_available
from tests.fixtures.models import DummyEntity, DummySecretEntity

pytestmark = [
    pytest.mark.skipif(
        not db_available(),
        reason="Requiere PostgreSQL: definir DATABASE_URL_TEST en el entorno",
    ),
]


class TestFullIntegrationC02:
    """Combina todos los features de C-02 en un flujo realista."""

    async def _seed_full_tenant(
        self, session, nombre: str
    ) -> tuple[uuid.UUID, list[DummyEntity], list[DummySecretEntity]]:
        """Crea un tenant completo con entidades dummy y secretas."""
        tid = uuid.uuid4()
        session.add(Tenant(id=tid, tenant_id=tid, nombre=nombre))

        entities = [
            DummyEntity(
                id=uuid.uuid4(), tenant_id=tid, label=f"{nombre}_e{i}"
            )
            for i in range(3)
        ]
        secret_entities = [
            DummySecretEntity(
                id=uuid.uuid4(),
                tenant_id=tid,
                name=f"{nombre}_user_{i}",
                secret_dni=f"{i:08d}",
            )
            for i in range(2)
        ]
        session.add_all(entities + secret_entities)
        await session.flush()
        return tid, entities, secret_entities

    async def test_scenario_import_then_query(self, db_session) -> None:
        """Flujo realista: importar datos de un tenant, consultar,
        soft-delete un registro, verificar aislamiento.

        Simula el caso de uso de un coordinador que importa datos
        de Moodle para una comisión y luego consulta.
        """
        # ── Arrange: dos tenants con datos ──────────────────────────────
        tid_a, e_a, s_a = await self._seed_full_tenant(
            db_session, "ComA"
        )
        tid_b, e_b, s_b = await self._seed_full_tenant(
            db_session, "ComB"
        )

        # ── Act: soft-delete la última entidad de ComA ──────────────────
        target = e_a[-1]
        target.deleted_at = datetime.now(timezone.utc)
        await db_session.flush()

        # ── Assert 1: aislamiento multi-tenant ───────────────────────────
        for tid, expected_count, name in [
            (tid_a, 2, "ComA"),
            (tid_b, 3, "ComB"),
        ]:
            stmt = (
                select(DummyEntity)
                .where(DummyEntity.tenant_id == tid)
                .where(DummyEntity.deleted_at.is_(None))
            )
            result = await db_session.execute(stmt)
            rows = list(result.scalars().all())
            assert len(rows) == expected_count, (
                f"{name}: esperaba {expected_count} activas, "
                f"tiene {len(rows)}"
            )

        # ── Assert 2: soft delete (la borrada no aparece) ────────────────
        stmt_check = (
            select(DummyEntity)
            .where(DummyEntity.id == target.id)
            .where(DummyEntity.deleted_at.is_(None))
        )
        assert (
            await db_session.execute(stmt_check)
        ).scalar_one_or_none() is None, (
            "Entidad soft-deleted no debe aparecer en query activos"
        )

        # ── Assert 3: cifrado funciona ───────────────────────────────────
        for sec in s_a:
            stmt_sec = select(DummySecretEntity).where(
                DummySecretEntity.id == sec.id
            )
            loaded = (
                await db_session.execute(stmt_sec)
            ).scalar_one()
            assert loaded.secret_dni == sec.secret_dni, (
                f"Cifrado: {loaded.secret_dni} != {sec.secret_dni}"
            )
            assert loaded.name.startswith("ComA_"), (
                f"Nombre plano incorrecto: {loaded.name}"
            )

        # ── Assert 4: cross-tenant NO ve datos del otro ─────────────────
        stmt_cross = (
            select(DummyEntity)
            .where(DummyEntity.tenant_id == tid_a)
            .where(DummyEntity.deleted_at.is_(None))
        )
        cross_result = await db_session.execute(stmt_cross)
        cross_labels = {
            r.label for r in cross_result.scalars().all()
        }
        assert all("ComA_" in lbl for lbl in cross_labels), (
            "ComA NO debe ver labels de ComB"
        )
