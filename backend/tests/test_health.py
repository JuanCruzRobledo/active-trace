"""Tests para el endpoint GET /health.

Requiere PostgreSQL real para verificar el readiness de la base de datos.
"""

import pytest
from httpx import AsyncClient

from tests.conftest import db_available


class TestHealthEndpoint:
    """Scenario: La aplicación está viva."""

    async def test_health_returns_200_and_status_ok(
        self, client: AsyncClient
    ) -> None:
        """WHEN GET /health → responde 200 con JSON que incluye status."""
        # Act
        response = await client.get("/health")
        body = response.json()
        # Assert
        assert response.status_code == 200
        assert body["status"] == "ok"

    async def test_health_response_has_database_field(
        self, client: AsyncClient
    ) -> None:
        """WHEN GET /health → la respuesta incluye campo database."""
        # Act
        response = await client.get("/health")
        body = response.json()
        # Assert
        assert "database" in body


class TestDatabaseReadiness:
    """Scenario: Readiness de la base de datos."""

    @pytest.mark.skipif(
        not db_available(),
        reason="Requiere PostgreSQL: definir DATABASE_URL_TEST",
    )
    async def test_database_up_when_db_reachable(
        self, client: AsyncClient
    ) -> None:
        """WHEN DB reachable → database: up."""
        # Act
        response = await client.get("/health")
        body = response.json()
        # Assert
        assert body["database"] == "up"
