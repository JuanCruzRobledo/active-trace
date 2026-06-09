"""Tests de integración para migraciones Alembic.

Verifica que las migraciones se aplican y revierten correctamente contra
PostgreSQL real (``alembic upgrade`` / ``alembic downgrade``).
"""

import os

import pytest

from tests.conftest import db_available

pytestmark = [
    pytest.mark.skipif(
        not db_available(),
        reason="Requiere PostgreSQL: definir DATABASE_URL_TEST en el entorno",
    ),
]


def _test_db_url() -> str:
    """Retorna la URL de test desde el entorno."""
    return (
        os.environ.get("DATABASE_URL_TEST")
        or os.environ.get("DATABASE_URL")
        or "postgresql+asyncpg://postgres:nikolan@localhost:5432/trace_test"
    )


class TestAlembicMigrations:
    """Verifica que las migraciones upgrade y downgrade funcionan."""

    @pytest.fixture(autouse=True)
    def _use_test_db(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Apunta Alembic a la base de test en vez de producción."""
        monkeypatch.setenv("DATABASE_URL", _test_db_url())

    async def _table_exists(self, table_name: str) -> bool:
        """Verifica si una tabla existe en la BD de test usando asyncpg."""
        import asyncpg  # noqa: PLC0415

        conn = await asyncpg.connect(
            user="postgres",
            password="nikolan",
            database="trace_test",
            host="localhost",
            port=5432,
        )
        try:
            row = await conn.fetchrow(
                "SELECT EXISTS (SELECT FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = $1)",
                table_name,
            )
            return row["exists"] if row else False
        finally:
            await conn.close()

    def test_upgrade_001_creates_tenant_table(self) -> None:
        """GIVEN base vacía WHEN alembic upgrade 001 THEN tabla tenant
        existe con las columnas esperadas."""
        import asyncpg  # noqa: PLC0415
        from alembic import command  # noqa: PLC0415
        from alembic.config import Config  # noqa: PLC0415

        cfg = Config("alembic.ini")
        cfg.set_main_option("sqlalchemy.url", _test_db_url())

        # Upgrade a 001
        command.upgrade(cfg, "001")

        # Verificar desde asyncpg
        import asyncio

        async def verify():
            conn = await asyncpg.connect(
                user="postgres",
                password="nikolan",
                database="trace_test",
                host="localhost",
                port=5432,
            )
            try:
                rows = await conn.fetch(
                    "SELECT column_name, data_type "
                    "FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = 'tenant'"
                )
                columns = {r["column_name"] for r in rows}
                expected = {
                    "id", "tenant_id", "created_at",
                    "updated_at", "deleted_at", "nombre",
                }
                assert expected.issubset(columns), (
                    f"Columnas esperadas: {expected}, "
                    f"presentes: {columns}"
                )
            finally:
                await conn.close()

        asyncio.run(verify())

        # Limpiar
        command.downgrade(cfg, "base")

    def test_downgrade_removes_tenant_table(self) -> None:
        """GIVEN migración 001 aplicada WHEN alembic downgrade base THEN
        tabla tenant NO existe."""
        from alembic import command  # noqa: PLC0415
        from alembic.config import Config  # noqa: PLC0415

        cfg = Config("alembic.ini")
        cfg.set_main_option("sqlalchemy.url", _test_db_url())

        # Upgrade
        command.upgrade(cfg, "001")
        # Downgrade
        command.downgrade(cfg, "base")

        import asyncio

        async def verify():
            exists = await self._table_exists("tenant")
            assert not exists, (
                "Tabla 'tenant' NO debería existir después del downgrade"
            )

        asyncio.run(verify())

    def test_upgrade_and_downgrade_full_cycle(self) -> None:
        """GIVEN ciclo completo upgrade→downgrade→upgrade WHEN verificar
        estado intermedio THEN cada paso es correcto."""
        from alembic import command  # noqa: PLC0415
        from alembic.config import Config  # noqa: PLC0415

        cfg = Config("alembic.ini")
        cfg.set_main_option("sqlalchemy.url", _test_db_url())

        import asyncio

        # 1. Upgrade → tabla existe
        command.upgrade(cfg, "001")
        assert asyncio.run(self._table_exists("tenant"))

        # 2. Downgrade → tabla no existe
        command.downgrade(cfg, "base")
        assert not asyncio.run(self._table_exists("tenant"))

        # 3. Re-upgrade → tabla existe de nuevo
        command.upgrade(cfg, "001")
        assert asyncio.run(self._table_exists("tenant"))

        # Cleanup final
        command.downgrade(cfg, "base")
