"""Entrypoint mínimo del worker background.

Placeholder — la tecnología real de la cola (ARQ / Celery / asyncio propio)
se define en ADR-003, que se resuelve al construir el módulo de comunicaciones.
"""

import asyncio
import logging

logger = logging.getLogger(__name__)


async def main() -> None:
    """Loop no-op del worker.

    En C-01 solo arranca, loguea un mensaje y espera indefinidamente.
    Reemplazar con el subscriber de cola real en el change correspondiente.
    """
    logger.info("Worker iniciado (placeholder — sin lógica de cola)")
    # Bucle infinito para mantener el proceso vivo
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
