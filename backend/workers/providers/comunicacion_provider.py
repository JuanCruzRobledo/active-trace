"""ComunicacionProvider — interfaz abstracta y stub para envío de comunicaciones.

En C-12 se implementa solo el stub que loggea el intento. En futuros changes
se agregan implementaciones reales (SMTP, N8N webhook, etc.).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

logger = logging.getLogger("workers.comunicaciones")


class ComunicacionProvider(ABC):
    """Interfaz abstracta para envío de comunicaciones.

    Cada implementación concreta debe sobrescribir :meth:`enviar`.
    """

    @abstractmethod
    async def enviar(
        self,
        destinatario: str,
        asunto: str,
        cuerpo: str,
    ) -> bool:
        """Envía una comunicación.

        Args:
            destinatario: Email del destinatario.
            asunto: Asunto del mensaje.
            cuerpo: Cuerpo del mensaje en texto plano o HTML.

        Returns:
            True si el envío fue exitoso, False en caso de error.
        """
        ...


class StubComunicacionProvider(ComunicacionProvider):
    """Provider de prueba que loggea el intento y retorna True.

    Usar en development y tests. En producción se reemplaza por una
    implementación real (ej. N8nComunicacionProvider).
    """

    async def enviar(
        self,
        destinatario: str,
        asunto: str,
        cuerpo: str,
    ) -> bool:
        """Loggea el intento de envío y retorna éxito.

        Args:
            destinatario: Email del destinatario.
            asunto: Asunto del mensaje.
            cuerpo: Cuerpo del mensaje.

        Returns:
            Siempre True (simula envío exitoso).
        """
        logger.info(
            "comunicacion.enviar",
            extra={
                "extra": {
                    "destinatario": destinatario,
                    "asunto": asunto,
                    "resultado": "ok",
                }
            },
        )
        return True
