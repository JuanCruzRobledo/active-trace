"""Logging estructurado JSON.

Reemplaza el formatter del logger raíz por uno que emite una línea JSON por
evento con campos ``timestamp``, ``level`` y ``message``.  Nunca registra
secretos ni PII en claro.
"""

import json
import logging
import sys
from datetime import UTC, datetime


class JSONFormatter(logging.Formatter):
    """Formatea cada registro como una línea JSON.

    Campos base: ``timestamp`` (ISO-8601 UTC), ``level``, ``logger``,
    ``message``.  Los ``extra`` dict se incorporan como campos adicionales.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            payload.update(record.extra)
        return json.dumps(payload, default=str)


def configure_json_logging(level: str = "DEBUG") -> None:
    """Configura el logger raíz con formato JSON y salida a stdout.

    Args:
        level: Nivel de log mínimo (``DEBUG``, ``INFO``, ``WARNING``, etc.).
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.DEBUG))
    # Remueve handlers previos para evitar duplicados
    for h in root.handlers[:]:
        root.removeHandler(h)
    root.addHandler(handler)
