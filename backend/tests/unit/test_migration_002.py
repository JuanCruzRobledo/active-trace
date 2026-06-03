"""Tests de integración para la migración Alembic 002.

Verifica que la migración 002 crea las 4 tablas nuevas (users, refresh_token,
password_reset_token, two_factor_challenge) con todos los índices, FKs y
constraints esperados, y que el ciclo upgrade → downgrade → upgrade es limpio.

Requiere PostgreSQL real (``DATABASE_URL_TEST`` en el entorno o fallback
a ``postgres:nikolan@localhost:5432/trace_test``).

Nota: la tabla de usuarios se llama ``users`` (no ``user``) porque
``user`` es palabra reservada de PostgreSQL. El modelo de SQLAlchemy
se mapea a ``User`` (clase) → tabla ``users``.
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


async def _table_exists(db: str, table_name: str) -> bool:
    """Verifica si una tabla existe en la BD de test usando asyncpg."""
    import asyncpg

    conn = await asyncpg.connect(
        user="postgres",
        password="nikolan",
        database=db,
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


async def _get_columns(db: str, table_name: str) -> set[str]:
    """Retorna el set de columnas de una tabla."""
    import asyncpg

    conn = await asyncpg.connect(
        user="postgres",
        password="nikolan",
        database=db,
        host="localhost",
        port=5432,
    )
    try:
        rows = await conn.fetch(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = $1",
            table_name,
        )
        return {r["column_name"] for r in rows}
    finally:
        await conn.close()


def _clean_test_db():
    """Limpia las tablas de test (por si quedaron de runs previos).

    Incluye todas las tablas conocidas hasta la migración 004.
    El orden importa: primero las que tienen FKs entrantes, después las
    referenciadas, y por último alembic_version.
    """
    import asyncio
    import asyncpg

    async def drop():
        conn = await asyncpg.connect(
            user="postgres",
            password="nikolan",
            database="trace_test",
            host="localhost",
            port=5432,
        )
        for table in [
            "user_rol",              # 004
            "rol_permiso",           # 003
            "rol",                   # 003
            "permiso",               # 003
            "two_factor_challenge",  # 002
            "password_reset_token",  # 002
            "refresh_token",         # 002
            "users",                 # 002
            "tenant",                # 001
            "alembic_version",       # alembic
        ]:
            await conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
        await conn.close()

    asyncio.run(drop())


class TestMigration002Upgrade:
    """Verifica que la migración 002 aplica limpia y crea las 4 tablas."""

    @pytest.fixture(autouse=True)
    def _use_test_db(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Apunta Alembic a la base de test y limpia estado previo."""
        monkeypatch.setenv("DATABASE_URL", _test_db_url())
        _clean_test_db()

    def _alembic_cfg(self):
        from alembic.config import Config

        cfg = Config("alembic.ini")
        cfg.set_main_option("sqlalchemy.url", _test_db_url())
        return cfg

    def test_upgrade_head_creates_all_4_new_tables(self) -> None:
        """GIVEN 001 ya aplicada WHEN upgrade head THEN las 4 tablas auth
        existen con las columnas esperadas."""
        import asyncio
        from alembic import command

        cfg = self._alembic_cfg()
        command.upgrade(cfg, "head")

        async def verify():
            for table, expected_cols in [
                (
                    "users",
                    {
                        "id",
                        "tenant_id",
                        "email",
                        "password_hash",
                        "is_active",
                        "totp_secret",
                        "totp_enabled",
                        "created_at",
                        "updated_at",
                        "deleted_at",
                    },
                ),
                (
                    "refresh_token",
                    {
                        "id",
                        "tenant_id",
                        "user_id",
                        "token_hash",
                        "expires_at",
                        "revoked_at",
                        "replaced_by_id",
                        "user_agent",
                        "created_ip",
                        "created_at",
                        "updated_at",
                        "deleted_at",
                    },
                ),
                (
                    "password_reset_token",
                    {
                        "id",
                        "tenant_id",
                        "user_id",
                        "token_hash",
                        "expires_at",
                        "used_at",
                        "created_at",
                    },
                ),
                (
                    "two_factor_challenge",
                    {
                        "id",
                        "tenant_id",
                        "user_id",
                        "token_hash",
                        "expires_at",
                        "used_at",
                        "created_at",
                    },
                ),
            ]:
                assert await _table_exists("trace_test", table), (
                    f"Tabla {table} no existe después de upgrade head"
                )
                cols = await _get_columns("trace_test", table)
                missing = expected_cols - cols
                assert not missing, (
                    f"Tabla {table} falta columnas: {missing}. Presentes: {cols}"
                )

        asyncio.run(verify())

        # Cleanup
        command.downgrade(cfg, "base")

    def test_users_table_has_unique_tenant_email(self) -> None:
        """GIVEN tabla users WHEN verificar constraints THEN existe
        UNIQUE (tenant_id, email)."""
        import asyncio
        from alembic import command

        cfg = self._alembic_cfg()
        command.upgrade(cfg, "head")

        async def verify():
            import asyncpg

            conn = await asyncpg.connect(
                user="postgres",
                password="nikolan",
                database="trace_test",
                host="localhost",
                port=5432,
            )
            try:
                row = await conn.fetchrow(
                    "SELECT conname FROM pg_constraint "
                    "WHERE conrelid = 'users'::regclass "
                    "AND contype = 'u' AND conname = 'uq_users_tenant_email'"
                )
                assert row is not None, (
                    "Falta UNIQUE constraint uq_users_tenant_email en tabla users"
                )
            finally:
                await conn.close()

        asyncio.run(verify())
        command.downgrade(cfg, "base")

    def test_token_hash_columns_have_unique_constraint(self) -> None:
        """GIVEN tablas de tokens WHEN verificar THEN token_hash es UNIQUE
        en cada una (refresh_token, password_reset_token, two_factor_challenge)."""
        import asyncio
        from alembic import command

        cfg = self._alembic_cfg()
        command.upgrade(cfg, "head")

        async def verify():
            import asyncpg

            conn = await asyncpg.connect(
                user="postgres",
                password="nikolan",
                database="trace_test",
                host="localhost",
                port=5432,
            )
            try:
                for table, expected_constraint in [
                    ("refresh_token", "uq_refresh_token_token_hash"),
                    (
                        "password_reset_token",
                        "uq_password_reset_token_token_hash",
                    ),
                    (
                        "two_factor_challenge",
                        "uq_two_factor_challenge_token_hash",
                    ),
                ]:
                    row = await conn.fetchrow(
                        "SELECT conname FROM pg_constraint "
                        "WHERE conrelid = $1::regclass "
                        "AND contype = 'u' AND conname = $2",
                        table,
                        expected_constraint,
                    )
                    assert row is not None, (
                        f"Falta UNIQUE {expected_constraint} en {table}"
                    )
            finally:
                await conn.close()

        asyncio.run(verify())
        command.downgrade(cfg, "base")

    def test_tenant_id_indexes_created(self) -> None:
        """GIVEN las 4 tablas WHEN verificar THEN cada una tiene índice
        ix_<table>_tenant_id."""
        import asyncio
        from alembic import command

        cfg = self._alembic_cfg()
        command.upgrade(cfg, "head")

        async def verify():
            import asyncpg

            conn = await asyncpg.connect(
                user="postgres",
                password="nikolan",
                database="trace_test",
                host="localhost",
                port=5432,
            )
            try:
                for table, expected_idx in [
                    ("users", "ix_users_tenant_id"),
                    ("refresh_token", "ix_refresh_token_tenant_id"),
                    (
                        "password_reset_token",
                        "ix_password_reset_token_tenant_id",
                    ),
                    (
                        "two_factor_challenge",
                        "ix_two_factor_challenge_tenant_id",
                    ),
                ]:
                    row = await conn.fetchrow(
                        "SELECT indexname FROM pg_indexes "
                        "WHERE schemaname = 'public' AND tablename = $1 "
                        "AND indexname = $2",
                        table,
                        expected_idx,
                    )
                    assert row is not None, (
                        f"Falta índice {expected_idx} en tabla {table}"
                    )
            finally:
                await conn.close()

        asyncio.run(verify())
        command.downgrade(cfg, "base")

    def test_ephemeral_tables_have_no_deleted_at(self) -> None:
        """GIVEN password_reset_token y two_factor_challenge WHEN verificar
        columnas THEN NO tienen deleted_at (son efímeras)."""
        import asyncio
        from alembic import command

        cfg = self._alembic_cfg()
        command.upgrade(cfg, "head")

        async def verify():
            for table in ["password_reset_token", "two_factor_challenge"]:
                cols = await _get_columns("trace_test", table)
                assert "deleted_at" not in cols, (
                    f"Tabla efímera {table} NO debería tener deleted_at. "
                    f"Columnas presentes: {cols}"
                )

        asyncio.run(verify())
        command.downgrade(cfg, "base")

    def test_users_and_user_tables_have_deleted_at(self) -> None:
        """GIVEN users y refresh_token WHEN verificar THEN tienen deleted_at
        (soft delete, BaseMixin)."""
        import asyncio
        from alembic import command

        cfg = self._alembic_cfg()
        command.upgrade(cfg, "head")

        async def verify():
            for table in ["users", "refresh_token"]:
                cols = await _get_columns("trace_test", table)
                assert "deleted_at" in cols, (
                    f"Tabla {table} DEBE tener deleted_at (soft delete)"
                )

        asyncio.run(verify())
        command.downgrade(cfg, "base")


class TestMigration002RoundTrip:
    """Verifica el ciclo upgrade → downgrade → upgrade."""

    @pytest.fixture(autouse=True)
    def _use_test_db(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DATABASE_URL", _test_db_url())
        _clean_test_db()

    def _alembic_cfg(self):
        from alembic.config import Config

        cfg = Config("alembic.ini")
        cfg.set_main_option("sqlalchemy.url", _test_db_url())
        return cfg

    def test_downgrade_to_001_removes_4_auth_tables(self) -> None:
        """GIVEN upgrade head WHEN downgrade 001 THEN las 4 tablas auth se
        eliminan, pero tenant permanece."""
        import asyncio
        from alembic import command

        cfg = self._alembic_cfg()
        command.upgrade(cfg, "head")
        command.downgrade(cfg, "001")

        async def verify():
            # tenant permanece
            assert await _table_exists("trace_test", "tenant")
            # Las 4 auth se eliminaron
            for table in [
                "users",
                "refresh_token",
                "password_reset_token",
                "two_factor_challenge",
            ]:
                assert not await _table_exists("trace_test", table), (
                    f"Tabla {table} no debería existir tras downgrade 001"
                )

        asyncio.run(verify())

        # Cleanup
        command.downgrade(cfg, "base")

    def test_full_round_trip_upgrade_downgrade_upgrade(self) -> None:
        """GIVEN ciclo upgrade→downgrade→upgrade completo WHEN verificar
        THEN cada paso deja el schema correcto."""
        import asyncio
        from alembic import command

        cfg = self._alembic_cfg()

        # 1. Upgrade head → 4 tablas auth presentes
        command.upgrade(cfg, "head")

        async def step1():
            for table in [
                "users",
                "refresh_token",
                "password_reset_token",
                "two_factor_challenge",
            ]:
                assert await _table_exists("trace_test", table)

        asyncio.run(step1())

        # 2. Downgrade base → todo limpio
        command.downgrade(cfg, "base")

        async def step2():
            for table in [
                "users",
                "refresh_token",
                "password_reset_token",
                "two_factor_challenge",
                "tenant",
            ]:
                assert not await _table_exists("trace_test", table), (
                    f"Tabla {table} no debería existir tras downgrade base"
                )

        asyncio.run(step2())

        # 3. Re-upgrade head → todo de vuelta
        command.upgrade(cfg, "head")

        async def step3():
            for table in [
                "users",
                "refresh_token",
                "password_reset_token",
                "two_factor_challenge",
                "tenant",
            ]:
                assert await _table_exists("trace_test", table), (
                    f"Tabla {table} debería existir tras re-upgrade"
                )

        asyncio.run(step3())

        # Cleanup final
        command.downgrade(cfg, "base")
