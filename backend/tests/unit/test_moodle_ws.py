"""Tests del cliente Moodle Web Services (C-09 padron-ingesta).

Cubre:
- sync_padron exitoso
- Error de conexion con reintentos
- Error de autenticacion sin reintento
- Error permanente sin reintento
- Respuesta invalida
- Excepcion en respuesta de Moodle
- Timeout de red
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import httpx
import pytest

from app.integrations.moodle_ws import (
    MoodleWSClient,
    MoodleWSAuthError,
    MoodleWSConnectionError,
    MoodleWSError,
)


@pytest.fixture
def client() -> MoodleWSClient:
    return MoodleWSClient(
        base_url="https://moodle.example.com",
        token="valid-token-123",
        timeout=5.0,
        max_retries=2,
    )


@pytest.fixture
def materia_id() -> UUID:
    return uuid4()


@pytest.fixture
def cohorte_id() -> UUID:
    return uuid4()


class _AsyncContextMock:
    """Mock que actua como context manager async y delegado en un AsyncMock."""

    def __init__(self, get_mock: AsyncMock) -> None:
        self._get_mock = get_mock

    async def __aenter__(self) -> _AsyncContextMock:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        pass

    async def get(self, url: str, params: dict[str, str]) -> httpx.Response:
        return await self._get_mock(url, params)


class TestMoodleWSClient:
    """Suite de tests para MoodleWSClient."""

    async def _setup_mock(
        self, response: httpx.Response | None = None, side_effect: Exception | None = None
    ) -> _AsyncContextMock:
        """Crea un mock de httpx.AsyncClient con la respuesta o side_effect dados."""
        get_mock = AsyncMock()
        if side_effect:
            get_mock.side_effect = side_effect
        elif response is not None:
            get_mock.return_value = response
        return _AsyncContextMock(get_mock)

    async def test_sync_padron_exitoso(
        self, client: MoodleWSClient, materia_id: UUID, cohorte_id: UUID
    ):
        """Scenario: Sincronizacion on-demand exitosa retorna datos normalizados."""
        response = httpx.Response(
            status_code=200,
            json=[
                {"firstname": "Juan", "lastname": "Perez", "email": "juan@test.com"},
                {
                    "firstname": "Maria",
                    "lastname": "Garcia",
                    "email": "maria@test.com",
                },
            ],
        )
        ctx_mock = await self._setup_mock(response=response)

        with patch("httpx.AsyncClient", return_value=ctx_mock):
            participantes = await client.sync_padron(materia_id, cohorte_id)

        assert len(participantes) == 2
        assert participantes[0].nombre == "Juan"
        assert participantes[0].apellidos == "Perez"
        assert participantes[0].email == "juan@test.com"

    async def test_sync_padron_error_conexion_reintenta(
        self, client: MoodleWSClient, materia_id: UUID, cohorte_id: UUID
    ):
        """Scenario: Error 503 de Moodle reintenta hasta agotar intentos."""
        response = httpx.Response(status_code=503)
        ctx_mock = await self._setup_mock(response=response)

        with patch("httpx.AsyncClient", return_value=ctx_mock):
            with pytest.raises(MoodleWSConnectionError) as exc_info:
                await client.sync_padron(materia_id, cohorte_id)

        assert "Moodle" in str(exc_info.value)

    async def test_sync_padron_token_invalido_no_reintenta(
        self, client: MoodleWSClient, materia_id: UUID, cohorte_id: UUID
    ):
        """Scenario: Token invalido (401) NO reintenta."""
        response = httpx.Response(status_code=401)
        ctx_mock = await self._setup_mock(response=response)

        with patch("httpx.AsyncClient", return_value=ctx_mock):
            with pytest.raises(MoodleWSAuthError):
                await client.sync_padron(materia_id, cohorte_id)

    async def test_sync_padron_404_no_reintenta(
        self, client: MoodleWSClient, materia_id: UUID, cohorte_id: UUID
    ):
        """Scenario: Error permanente (404) NO reintenta."""
        response = httpx.Response(status_code=404)
        ctx_mock = await self._setup_mock(response=response)

        with patch("httpx.AsyncClient", return_value=ctx_mock):
            with pytest.raises(MoodleWSError):
                await client.sync_padron(materia_id, cohorte_id)

    async def test_sync_padron_respuesta_invalida(
        self, client: MoodleWSClient, materia_id: UUID, cohorte_id: UUID
    ):
        """Scenario: Moodle devuelve JSON invalido que no se puede parsear."""
        response = httpx.Response(status_code=200, text="not json")
        ctx_mock = await self._setup_mock(response=response)

        with patch("httpx.AsyncClient", return_value=ctx_mock):
            with pytest.raises(MoodleWSError):
                await client.sync_padron(materia_id, cohorte_id)

    async def test_sync_padron_exception_moodle(
        self, client: MoodleWSClient, materia_id: UUID, cohorte_id: UUID
    ):
        """Scenario: Moodle devuelve excepcion en el JSON."""
        response = httpx.Response(
            status_code=200,
            json={
                "exception": "invalid_parameter_exception",
                "errorcode": "invalidparameter",
                "message": "Invalid course id",
            },
        )
        ctx_mock = await self._setup_mock(response=response)

        with patch("httpx.AsyncClient", return_value=ctx_mock):
            with pytest.raises(MoodleWSError) as exc_info:
                await client.sync_padron(materia_id, cohorte_id)

        assert "Invalid course id" in str(exc_info.value)

    async def test_sync_timeout_error(
        self, client: MoodleWSClient, materia_id: UUID, cohorte_id: UUID
    ):
        """Scenario: Timeout de red lanza MoodleWSConnectionError."""
        ctx_mock = await self._setup_mock(
            side_effect=httpx.TimeoutException("Connection timed out")
        )

        with patch("httpx.AsyncClient", return_value=ctx_mock):
            with pytest.raises(MoodleWSConnectionError) as exc_info:
                await client.sync_padron(materia_id, cohorte_id)

        # Verifica que sea un error de conexion, no de autenticacion ni otro
        assert isinstance(exc_info.value, MoodleWSConnectionError)
        assert "3 attempts" in str(exc_info.value)
