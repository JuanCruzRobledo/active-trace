"""Tests de cifrado en reposo con EncryptedColumn + ORM.

Requiere PostgreSQL real (``DATABASE_URL_TEST`` en el entorno).
"""

import uuid

import pytest
from sqlalchemy import select

from app.models.tenant import Tenant
from tests.conftest import db_available
from tests.fixtures.models import DummySecretEntity

pytestmark = [
    pytest.mark.skipif(
        not db_available(),
        reason="Requiere PostgreSQL: definir DATABASE_URL_TEST en el entorno",
    ),
]


class TestEncryptionRoundTrip:
    """Verifica que EncryptedColumn cifra en reposo y descifra al leer."""

    async def test_encrypt_decrypt_round_trip(self, db_session) -> None:
        """GIVEN DummySecretEntity con DNI ficticio WHEN persistir y
        recargar THEN el valor descifrado es igual al original."""
        tid = uuid.uuid4()
        tenant = Tenant(id=tid, tenant_id=tid, nombre="EncTest")
        db_session.add(tenant)

        original_dni = "12345678"
        entity = DummySecretEntity(
            id=uuid.uuid4(),
            tenant_id=tid,
            name="Juan",
            secret_dni=original_dni,
        )
        db_session.add(entity)
        await db_session.flush()

        # Recargar desde DB
        await db_session.refresh(entity)
        assert entity.secret_dni == original_dni, (
            f"Esperaba '{original_dni}', obtuvo '{entity.secret_dni}'"
        )
        assert entity.name == "Juan"

    async def test_encrypted_value_differs_in_db(self, db_session) -> None:
        """GIVEN DummySecretEntity con DNI WHEN persistir THEN el valor
        en la columna NO es texto plano."""
        tid = uuid.uuid4()
        tenant = Tenant(id=tid, tenant_id=tid, nombre="EncCipher")
        db_session.add(tenant)

        original = "99999999"
        entity = DummySecretEntity(
            id=uuid.uuid4(),
            tenant_id=tid,
            name="Ana",
            secret_dni=original,
        )
        db_session.add(entity)
        await db_session.flush()

        # Leer RAW de la tabla
        from sqlalchemy import text

        raw_result = await db_session.execute(
            text(
                "SELECT secret_dni FROM _test_dummy_secret "
                "WHERE id = :eid"
            ),
            {"eid": entity.id},
        )
        raw_value = raw_result.scalar_one()

        assert raw_value != original, (
            "El valor en DB NO debe ser texto plano"
        )
        # Debe ser base64 URL-safe (Fernet output)
        assert isinstance(raw_value, str)
        assert len(raw_value) > 0

    async def test_multiple_encrypted_values(self, db_session) -> None:
        """GIVEN múltiples entidades con distintos DNI WHEN recargar THEN
        cada uno mantiene su valor."""
        tid = uuid.uuid4()
        tenant = Tenant(id=tid, tenant_id=tid, nombre="EncMulti")
        db_session.add(tenant)

        dnies = ["11111111", "22222222", "33333333"]
        entities: list[DummySecretEntity] = []
        for i, dni in enumerate(dnies):
            e = DummySecretEntity(
                id=uuid.uuid4(),
                tenant_id=tid,
                name=f"User_{dni}",
                secret_dni=dni,
            )
            db_session.add(e)
            entities.append(e)
        await db_session.flush()

        for i, e in enumerate(entities):
            await db_session.refresh(e)
            assert e.secret_dni == dnies[i], (
                f"Mismatch for {e.id}: {e.secret_dni} != {dnies[i]}"
            )

    async def test_null_encrypted_column(self, db_session) -> None:
        """GIVEN entidad con secret_dni=None WHEN persistir THEN
        recargar devuelve None."""
        tid = uuid.uuid4()
        tenant = Tenant(id=tid, tenant_id=tid, nombre="EncNull")
        db_session.add(tenant)

        entity = DummySecretEntity(
            id=uuid.uuid4(),
            tenant_id=tid,
            name="NullTest",
            secret_dni=None,
        )
        db_session.add(entity)
        await db_session.flush()

        await db_session.refresh(entity)

        assert entity.secret_dni is None, (
            "Columna cifrada NULL debe seguir siendo NULL"
        )

    async def test_encrypted_column_with_tenant_isolation(
        self, db_session
    ) -> None:
        """GIVEN dos tenants con DNI distintos WHEN recargar cada uno
        THEN cada tenant ve su propio DNI."""
        t1_id = uuid.uuid4()
        t2_id = uuid.uuid4()
        db_session.add(Tenant(id=t1_id, tenant_id=t1_id, nombre="EncT1"))
        db_session.add(Tenant(id=t2_id, tenant_id=t2_id, nombre="EncT2"))
        await db_session.flush()

        e1 = DummySecretEntity(
            id=uuid.uuid4(),
            tenant_id=t1_id,
            name="T1User",
            secret_dni="10000001",
        )
        e2 = DummySecretEntity(
            id=uuid.uuid4(),
            tenant_id=t2_id,
            name="T2User",
            secret_dni="20000002",
        )
        db_session.add_all([e1, e2])
        await db_session.flush()

        # Refresh y verificar cada uno
        await db_session.refresh(e1)
        await db_session.refresh(e2)
        assert e1.secret_dni == "10000001"
        assert e2.secret_dni == "20000002"
