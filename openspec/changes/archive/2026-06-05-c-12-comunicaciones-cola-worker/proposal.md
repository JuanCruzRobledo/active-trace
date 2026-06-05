## Why

Con el análisis de atrasados completado (C-11), el sistema necesita el canal de comunicación para convertir la detección de riesgo en acción. Sin este módulo, los docentes identifican alumnos atrasados pero no pueden contactarlos desde la plataforma. Este change implementa la cola de comunicaciones: preview obligatorio (RN-16), envío masivo asíncrono con estados trazables (RN-15), aprobación humana configurable por tenant (RN-17) y el worker que despacha los mensajes.

## What Changes

- **Nuevo modelo Comunicacion**: tabla `comunicaciones` con ciclo Pendiente→Enviando→Enviado/Error/Cancelado, destinatario cifrado (AES-256), lote_id para agrupar envíos masivos
- **Preview obligatorio**: endpoint de preview que muestra asunto + cuerpo renderizado antes de encolar (RN-16)
- **Envío masivo asíncrono**: endpoint que encola mensajes en estado Pendiente; worker desencola, envía y actualiza estado (RN-15)
- **Aprobación humana**: si el tenant lo requiere, los envíos masivos quedan Pendiente hasta que un usuario con `comunicacion:aprobar` los aprueba (RN-17)
- **Endpoints REST**: `/api/comunicaciones/*` con guard `comunicacion:enviar`
- **Worker asíncrono**: módulo `workers/comunicaciones_worker.py` que procesa la cola
- **Audit log**: acción `COMUNICACION_ENVIAR` en cada envío
- **Migración Alembic**: creación de la tabla `comunicaciones`

## Capabilities

### New Capabilities
- `comunicaciones-envio`: Envío masivo de comunicaciones con preview obligatorio, estados trazables (Pendiente→Enviando→Enviado/Error/Cancelado), destinatario cifrado y lote_id para agrupación.
- `comunicaciones-aprobacion`: Aprobación humana configurable por tenant para envíos masivos; rol con `comunicacion:aprobar` revisa y habilita o rechaza el lote antes del despacho.
- `comunicaciones-worker`: Worker asíncrono que desencola comunicaciones Pendientes, ejecuta el envío real y actualiza el estado a Enviado/Error/Cancelado según resultado.

### Modified Capabilities
<!-- No existing spec-level requirements change — the audit-log spec already defines `COMUNICACION_ENVIAR` as a valid action code. -->

## Impact

- **Nuevo modelo**: `backend/app/models/comunicacion.py` — entidad Comunicacion SQLAlchemy
- **Nuevo schema Pydantic**: `backend/app/schemas/comunicacion.py` — DTOs con `extra='forbid'`
- **Nuevo repository**: `backend/app/repositories/comunicacion_repository.py` — queries con scope de tenant
- **Nuevo service**: `backend/app/services/comunicacion_service.py` — lógica de preview, encolado, aprobación, cancelación
- **Nuevo router**: `backend/app/api/v1/routers/comunicaciones.py` — endpoints bajo `/api/comunicaciones/*`
- **Nuevo worker**: `backend/workers/comunicaciones_worker.py` — procesamiento asíncrono de la cola
- **Nueva migración**: migración Alembic para tabla `comunicaciones`
- **Permisos**: `comunicacion:enviar` (PROFESOR propio, COORDINADOR, ADMIN), `comunicacion:aprobar` (COORDINADOR, ADMIN)
- **Audit log**: código `COMUNICACION_ENVIAR`
- **Tests**: tests de integración con base real para cada escenario
