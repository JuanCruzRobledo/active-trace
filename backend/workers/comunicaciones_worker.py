"""Worker asíncrono de comunicaciones — polling loop con FOR UPDATE SKIP LOCKED.

Procesa comunicaciones Pendiente en lotes, llamando al ComunicacionProvider
para cada envío y actualizando el estado a Enviado/Error.

Uso::

    python -m workers.comunicaciones_worker

Configuración vía entorno:
    ``COMUNICACIONES_POLL_INTERVAL``: segundos entre polls (default: 5).
    ``COMUNICACIONES_WORKER_BATCH_SIZE``: máx comunicaciones por lote (default: 50).
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
from datetime import datetime, timezone
from typing import NoReturn
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.database import close_engine, get_session_maker, init_engine
from app.models.comunicacion import Comunicacion, EstadoComunicacion
from app.models.tenant import Tenant
from workers.providers.comunicacion_provider import (
    ComunicacionProvider,
    StubComunicacionProvider,
)

logger = logging.getLogger("workers.comunicaciones")

# ── Configuración desde entorno ──────────────────────────────────────

POLL_INTERVAL = int(os.environ.get("COMUNICACIONES_POLL_INTERVAL", "5"))
BATCH_SIZE = int(os.environ.get("COMUNICACIONES_WORKER_BATCH_SIZE", "50"))


# ── Lógica de procesamiento (exportada para tests) ────────────────────


async def procesar_comunicacion(
    comunicacion: Comunicacion,
    provider: ComunicacionProvider,
) -> EstadoComunicacion:
    """Envía una comunicación vía provider y retorna el estado resultante.

    Args:
        comunicacion: Instancia de Comunicacion a enviar.
        provider: Provider de envío.

    Returns:
        EstadoComunicacion.Enviado si fue exitoso, EstadoComunicacion.Error si falló.
    """
    try:
        exito = await provider.enviar(
            destinatario=comunicacion.destinatario,
            asunto=comunicacion.asunto,
            cuerpo=comunicacion.cuerpo,
        )
    except Exception:
        logger.exception(
            "comunicacion.error",
            extra={"extra": {"comunicacion_id": str(comunicacion.id)}},
        )
        return EstadoComunicacion.Error

    return EstadoComunicacion.Enviado if exito else EstadoComunicacion.Error


async def procesar_lote(
    session: AsyncSession,
    provider: ComunicacionProvider,
    batch_size: int = BATCH_SIZE,
) -> int:
    """Obtiene comunicaciones Pendiente con FOR UPDATE SKIP LOCKED y las procesa.

    Cruzando todos los tenants. Si un tenant tiene configurado
    ``aprobacion_comunicaciones_requerida = False``, también procesa
    aquellas con ``necesita_aprobacion`` seteado.

    Args:
        session: Sesión de base de datos.
        provider: Provider de envío.
        batch_size: Máximo de comunicaciones a procesar.

    Returns:
        Cantidad de comunicaciones procesadas en este lote.
    """
    # Obtener config de tenants para saber quién requiere aprobación
    tenants = await session.scalars(
        select(Tenant).where(Tenant.deleted_at.is_(None))
    )
    tenant_config: dict[UUID, bool] = {}
    for t in tenants.all():
        cfg = t.config or {}
        tenant_config[t.id] = cfg.get("aprobacion_comunicaciones_requerida", True)

    # Construir query: Pendientes, no eliminadas
    # Si el tenant requiere aprobación, excluir necesita_aprobacion
    # Si no requiere, incluir también las que tienen necesita_aprobacion
    filters = [
        Comunicacion.estado == EstadoComunicacion.Pendiente,
        Comunicacion.deleted_at.is_(None),
    ]

    # No podemos hacer un filter condicional por tenant fácilmente en una query,
    # así que obtenemos un lote general y filtramos en memoria
    pendientes = await session.scalars(
        select(Comunicacion)
        .where(*filters)
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    )
    comunicaciones = list(pendientes.all())

    if not comunicaciones:
        return 0

    # Separar las que requieren aprobación según config del tenant
    a_procesar: list[Comunicacion] = []
    for c in comunicaciones:
        requiere = tenant_config.get(c.tenant_id, True)
        if requiere and c.necesita_aprobacion is not None:
            continue  # saltar: necesita aprobación no concedida
        a_procesar.append(c)

    if not a_procesar:
        await session.commit()
        return 0

    ahora = datetime.now(timezone.utc)
    for c in a_procesar:
        nuevo_estado = await procesar_comunicacion(c, provider)
        c.estado = nuevo_estado
        c.enviado_at = ahora

    await session.flush()
    await session.commit()

    logger.info(
        "comunicacion.lote_procesado",
        extra={
            "extra": {
                "procesadas": len(a_procesar),
                "saltadas_por_aprobacion": len(comunicaciones) - len(a_procesar),
            }
        },
    )

    return len(a_procesar)


# ── Loop principal ───────────────────────────────────────────────────


_shutdown_event = asyncio.Event()


def _handle_signal(signum: int, _frame: object) -> None:
    """Handler de señales — activa el evento de shutdown."""
    logger.info(
        "worker.shutdown",
        extra={
            "extra": {
                "signal": signal.Signals(signum).name,  # type: ignore[arg-type]
            }
        },
    )
    _shutdown_event.set()


async def main_loop(
    provider: ComunicacionProvider | None = None,
    poll_interval: int = POLL_INTERVAL,
) -> None:
    """Loop principal del worker.

    Args:
        provider: Provider de envío (default: StubComunicacionProvider).
        poll_interval: Segundos entre polls.
    """
    provider = provider or StubComunicacionProvider()
    settings = Settings()  # type: ignore[call-arg]

    init_engine(
        settings.DATABASE_URL,
        encryption_key=settings.ENCRYPTION_KEY,
    )

    logger.info(
        "worker.iniciado",
        extra={
            "extra": {
                "poll_interval": poll_interval,
                "batch_size": BATCH_SIZE,
            }
        },
    )

    try:
        while not _shutdown_event.is_set():
            maker = get_session_maker()
            async with maker() as session:
                try:
                    procesadas = await procesar_lote(session, provider, BATCH_SIZE)
                    if procesadas > 0:
                        logger.info(
                            "worker.ciclo",
                            extra={"extra": {"procesadas": procesadas}},
                        )
                except Exception:
                    logger.exception("worker.ciclo.error")
                    await session.rollback()

            try:
                await asyncio.wait_for(
                    _shutdown_event.wait(),
                    timeout=poll_interval,
                )
                break
            except asyncio.TimeoutError:
                continue
    finally:
        logger.info("worker.finalizando")
        await close_engine()
        logger.info("worker.finalizado")


# ── Entrypoint ───────────────────────────────────────────────────────


def main() -> None:
    """Entrypoint del worker — configura logging, señales y arranca el loop."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    asyncio.run(main_loop())


if __name__ == "__main__":
    main()
