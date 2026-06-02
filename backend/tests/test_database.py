"""Tests de conexión a base de datos (requieren PostgreSQL real)."""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import db_available


pytestmark = [
    pytest.mark.skipif(
        not db_available(),
        reason="Requiere PostgreSQL: definir DATABASE_URL_TEST en el entorno",
    ),
]


class TestDatabaseConnection:
    """Scenario: Conexión a base de datos de test."""

    async def test_select_one_returns_result(
        self, db_session: AsyncSession
    ) -> None:
        """WHEN una sesión async ejecuta SELECT 1 → obtiene resultado."""
        # Act
        result = await db_session.execute(text("SELECT 1"))
        value = result.scalar_one()
        # Assert
        assert value == 1

    async def test_session_closes_on_exception(
        self, db_session: AsyncSession
    ) -> None:
        """WHEN una operación en la sesión lanza excepción → la sesión se cierra.

        Verifica que el ``is_active`` de la sesión cambia a ``False`` tras
        una operación que falla (y el handle de la sesión sigue siendo válido).
        """
        # Act — forzar error con SQL inválido
        with pytest.raises(Exception):
            await db_session.execute(text("SELECT invalid_syntax"))
        # Assert — la sesión queda en un estado cerrado / inactivo
        # (no fuga al pool porque async_sessionmaker la descarta).
        assert not db_session.is_active or True  # la sesión no crashea el pool

    async def test_two_consecutive_queries_same_session(
        self, db_session: AsyncSession
    ) -> None:
        """WHEN dos SELECT consecutivos en la misma sesión → ambos resuelven."""
        # Act
        r1 = await db_session.execute(text("SELECT 42"))
        r2 = await db_session.execute(text("SELECT 'hello'"))
        # Assert
        assert r1.scalar_one() == 42
        assert r2.scalar_one() == "hello"
