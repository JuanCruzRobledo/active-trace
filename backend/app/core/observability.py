"""Inicialización de OpenTelemetry para activia-trace.

Activable por entorno.  Si no hay endpoint OTLP configurado la aplicación
arranca igual (no se acopla a un backend de telemetría en el cimiento).
"""

import logging

logger = logging.getLogger(__name__)


def init_opentelemetry(
    service_name: str = "activia-trace",
    otlp_endpoint: str | None = None,
) -> None:
    """Inicializa la instrumentación OpenTelemetry para FastAPI.

    Si no se provee ``otlp_endpoint``, la inicialización es no-operativa:
    la app sigue funcionando sin telemetría exportada.

    Args:
        service_name: Nombre del servicio para el resource.
        otlp_endpoint: URL del collector OTLP (opcional).
    """
    if not otlp_endpoint:
        logger.info(
            "OTel sin exporter — la telemetría se registra pero no se exporta"
        )
        return

    try:
        from opentelemetry import trace  # noqa: PLC0415
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (  # noqa: PLC0415, F811
            OTLPSpanExporter,
        )
        from opentelemetry.instrumentation.fastapi import (  # noqa: PLC0415, F401
            FastAPIInstrumentor,
        )
        from opentelemetry.sdk.resources import (  # noqa: PLC0415
            Resource,
        )
        from opentelemetry.sdk.trace import TracerProvider  # noqa: PLC0415
        from opentelemetry.sdk.trace.export import (  # noqa: PLC0415
            BatchSpanProcessor,
        )

        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)
        processor = BatchSpanProcessor(
            OTLPSpanExporter(endpoint=otlp_endpoint)
        )
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)

        logger.info("OTel inicializado con endpoint %s", otlp_endpoint)
    except ImportError as exc:
        logger.warning(
            "OTel no disponible (%s) — saltando instrumentación",
            exc,
        )
