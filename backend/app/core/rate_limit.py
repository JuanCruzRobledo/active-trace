"""Rate limiter — wrapper sobre slowapi (C-03).

Decisión D5 (design.md): ``slowapi`` in-memory (single-process). Cuando
el deploy pase a multi-replica (Easypanel), se cambia el backend a Redis
en un change dedicado — no es bloqueante para C-03.

**Limitación C-03**: el ``key_func`` es solo IP (``get_remote_address``).
La spec pide ``(ip, email)`` pero acceder al email requiere parsear el
body del request, que es async — no se puede hacer en el ``key_func`` sync
de slowapi. C-12 (worker) lo refina con async body parsing. Documentado
en el design como deuda técnica aceptada para MVP.

Uso en un router::

    from app.core.rate_limit import rate_limit_login
    from fastapi import APIRouter

    router = APIRouter()

    @router.post("/login")
    @rate_limit_login
    async def login(...): ...
"""

from __future__ import annotations

import functools
import logging
from collections.abc import Callable
from typing import Any

from fastapi import Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

_logger = logging.getLogger("rate_limit")


def get_client_ip(request: Request) -> str:
    """Key func para slowapi: IP del cliente.

    IMPORTANTE: el parámetro DEBE llamarse ``request`` (slowapi hace
    ``inspect.signature(key_func).parameters`` y busca la clave literal
    ``"request"`` para decidir si pasar el request al llamar).

    Args:
        request: Request de FastAPI.

    Returns:
        IP del cliente (string). Si no hay client.host, retorna ``"unknown"``
        (defensivo — en producción esto no debería pasar).
    """
    return request.client.host if request.client else "unknown"


# Singleton de Limiter. Reutilizado por todos los decoradores.
limiter = Limiter(
    key_func=get_client_ip,
    headers_enabled=True,  # agrega X-RateLimit-* y Retry-After a las responses
)


def _build_limit_decorator(
    limit_str: str,
    action: str,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Construye un decorador de rate limit con auditoría y logging.

    IMPORTANTE: preserva la firma de la función original con
    ``functools.wraps`` para que FastAPI pueda resolver las dependencias
    (``request: Request``, body, etc.) correctamente.

    Args:
        limit_str: Límite en formato slowapi (ej. ``"5/60 second"``).
        action: Nombre lógico del endpoint (para audit log).

    Returns:
        Decorador que envuelve el endpoint con rate limit.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        # Aplica el decorador de slowapi. La función resultante preserva
        # la firma de ``func`` (slowapi usa functools.wraps internamente).
        limited = limiter.limit(limit_str)(func)

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # El limit real lo aplica slowapi vía la excepción. Acá
            # agregamos logging cuando se dispara el límite.
            try:
                return await limited(*args, **kwargs)
            except RateLimitExceeded as exc:
                from app.core.audit import record  # noqa: PLC0415

                # ``request`` puede estar en args o kwargs dependiendo de
                # cómo FastAPI resolvió las dependencias. Inspeccionamos ambos.
                request: Request | None = kwargs.get("request")
                if request is None:
                    for arg in args:
                        if isinstance(arg, Request):
                            request = arg
                            break
                ip = (
                    get_client_ip(request)
                    if request is not None
                    else "unknown"
                )
                record(
                    "RATE_LIMIT_HIT",
                    {
                        "action": action,
                        "ip": ip,
                        "limit": limit_str,
                        "detail": str(exc),
                    },
                )
                _logger.warning(
                    "rate_limit.hit",
                    extra={
                        "extra": {
                            "rate_limit.action": action,
                            "rate_limit.ip": ip,
                            "rate_limit.limit": limit_str,
                        }
                    },
                )
                raise

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# Decoradores pre-configurados para los 4 endpoints sensibles
# ---------------------------------------------------------------------------


def rate_limit_login(func: Callable[..., Any]) -> Callable[..., Any]:
    """Rate limit para ``POST /api/auth/login``: 5/60s por IP."""
    return _build_limit_decorator("5/60 second", "login")(func)


def rate_limit_2fa_verify(func: Callable[..., Any]) -> Callable[..., Any]:
    """Rate limit para ``POST /api/auth/2fa/verify``: 5/60s por IP."""
    return _build_limit_decorator("5/60 second", "2fa_verify")(func)


def rate_limit_refresh(func: Callable[..., Any]) -> Callable[..., Any]:
    """Rate limit para ``POST /api/auth/refresh``: 5/60s por IP."""
    return _build_limit_decorator("5/60 second", "refresh")(func)


def rate_limit_forgot(func: Callable[..., Any]) -> Callable[..., Any]:
    """Rate limit para ``POST /api/auth/forgot``: 5/60s por IP."""
    return _build_limit_decorator("5/60 second", "forgot")(func)


def rate_limit_reset(func: Callable[..., Any]) -> Callable[..., Any]:
    """Rate limit para ``POST /api/auth/reset``: 5/60s por IP."""
    return _build_limit_decorator("5/60 second", "reset")(func)
