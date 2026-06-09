"""Moodle Web Services client — sync de usuarios/actividades.

Cliente dedicado para comunicacion con Moodle via Web Services.
Configuracion por tenant (URL + token). Implementa reintentos con
backoff exponencial para errores transitorios.

Uso::

    client = MoodleWSClient(base_url="https://moodle.example.com", token="abc123")
    participantes = await client.sync_padron(materia_id, cohorte_id)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import httpx

_logger = logging.getLogger(__name__)


class MoodleWSError(Exception):
    """Error base de Moodle WS, mapeable a HTTP 502."""

    def __init__(
        self,
        message: str,
        status_code: int = 502,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class MoodleWSAuthError(MoodleWSError):
    """Error de autenticacion contra Moodle (token invalido)."""

    def __init__(self, message: str = "Moodle WS authentication failed") -> None:
        super().__init__(message, status_code=502)


class MoodleWSConnectionError(MoodleWSError):
    """Error de conexion contra Moodle (timeout, DNS, etc.)."""

    def __init__(self, message: str = "Moodle WS connection failed") -> None:
        super().__init__(message, status_code=502)


@dataclass
class ParticipanteMoodle:
    """Participante normalizado desde Moodle WS."""

    nombre: str
    apellidos: str
    email: str
    comision: str | None = None
    regional: str | None = None


class MoodleWSClient:
    """Cliente para Moodle Web Services.

    Args:
        base_url: URL base de la instancia Moodle (ej: https://moodle.example.com).
        token: Token de servicio Web de Moodle.
        timeout: Timeout en segundos para requests (default: 30).
        max_retries: Maximo de reintentos para errores transitorios (default: 3).
    """

    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._timeout = timeout
        self._max_retries = max_retries

    async def sync_padron(
        self, materia_id: UUID, cohorte_id: UUID
    ) -> list[ParticipanteMoodle]:
        """Sincroniza participantes desde Moodle WS.

        Args:
            materia_id: UUID de la materia (se mapea al course id en Moodle).
            cohorte_id: UUID de la cohorte.

        Returns:
            Lista de participantes normalizados.

        Raises:
            MoodleWSError: Si la sincronizacion falla.
        """
        # Construir el identificador del curso segun mapping del tenant
        # Por ahora, usamos el materia_id como identificador; en produccion
        # se puede personalizar el mapeo por tenant
        course_id = str(materia_id)

        params = {
            "wstoken": self._token,
            "wsfunction": "core_enrol_get_enrolled_users",
            "courseid": course_id,
            "moodlewsrestformat": "json",
        }

        url = f"{self._base_url}/webservice/rest/server.php"

        for attempt in range(self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.get(url, params=params)
            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                _logger.warning(
                    "moodle_ws.connection_error",
                    extra={
                        "extra": {
                            "moodle.url": url,
                            "moodle.attempt": attempt + 1,
                            "moodle.error": str(exc),
                        }
                    },
                )
                if attempt < self._max_retries:
                    wait = 2**attempt  # backoff exponencial: 1s, 2s, 4s
                    await asyncio.sleep(wait)
                    continue
                raise MoodleWSConnectionError(
                    f"Moodle not reachable after {self._max_retries + 1} attempts"
                ) from exc

            if response.status_code == 401:
                raise MoodleWSAuthError("Invalid Moodle WS token")

            if response.status_code in (502, 503, 504):
                _logger.warning(
                    "moodle_ws.server_error",
                    extra={
                        "extra": {
                            "moodle.url": url,
                            "moodle.status": response.status_code,
                            "moodle.attempt": attempt + 1,
                        }
                    },
                )
                if attempt < self._max_retries:
                    wait = 2**attempt
                    await asyncio.sleep(wait)
                    continue
                raise MoodleWSConnectionError(
                    f"Moodle returned {response.status_code} "
                    f"after {self._max_retries + 1} attempts"
                )

            if response.status_code != 200:
                raise MoodleWSError(
                    f"Moodle returned unexpected status {response.status_code}",
                    details={"status_code": response.status_code, "body": response.text[:500]},
                )

            # Parsear respuesta
            try:
                data = response.json()
            except Exception as exc:
                raise MoodleWSError(
                    "Invalid JSON response from Moodle",
                    details={"response_preview": response.text[:500]},
                ) from exc

            # Moodle puede devolver error en el JSON (excepcion del WS)
            if isinstance(data, dict) and "exception" in data:
                raise MoodleWSError(
                    f"Moodle WS exception: {data.get('message', 'Unknown')}",
                    details={"moodle_exception": data.get("exception"), "errorcode": data.get("errorcode")},
                )

            # Normalizar participantes
            participantes: list[ParticipanteMoodle] = []
            for user in data if isinstance(data, list) else []:
                participantes.append(
                    ParticipanteMoodle(
                        nombre=user.get("firstname", ""),
                        apellidos=user.get("lastname", ""),
                        email=user.get("email", ""),
                        comision=None,  # Moodle no expone comision directamente
                        regional=None,
                    )
                )

            _logger.info(
                "moodle_ws.sync_ok",
                extra={
                    "extra": {
                        "moodle.participantes": len(participantes),
                        "moodle.materia_id": str(materia_id),
                    }
                },
            )
            return participantes

        # Si llegamos aca, todos los reintentos fallaron
        raise MoodleWSConnectionError(
            f"Moodle sync failed after {self._max_retries + 1} attempts"
        )
