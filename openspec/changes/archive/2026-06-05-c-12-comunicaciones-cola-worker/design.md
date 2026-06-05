## Context

C-12 implementa el módulo de comunicaciones del sistema. Con C-11 los docentes ya detectan alumnos atrasados; ahora pueden contactarlos. Es el primer change que introduce un worker asíncrono en la arquitectura. Los cambios anteriores (C-01 a C-11) establecieron la base: FastAPI + SQLAlchemy 2.0 async, PostgreSQL, multi-tenancy con tenant_id, RBAC fino, AES-256 para datos cifrados, y audit log con códigos estandarizados.

El sistema actual no tiene cola de mensajes externa (RabbitMQ, Redis). ADR-003 (worker de mails: implementación propia vs. N8N) está pendiente de resolución. Para evitar bloquear este change, el worker se implementa con un loop asyncio simple que consulta la base de datos.

El modelo Comunicacion ya está definido en la KB (04_modelo_de_datos.md, E21): destinatario cifrado, lote_id, estados Pendiente→Enviando→Enviado/Error/Cancelado.

## Goals / Non-Goals

**Goals:**
- Migración Alembic para la tabla `comunicaciones` con columna `destinatario` cifrada (AES-256)
- Endpoint `POST /api/comunicaciones/preview` — renderiza asunto + cuerpo sin encolar
- Endpoint `POST /api/comunicaciones/enviar` — encola mensajes en estado Pendiente (con preview_token obligatorio, RN-16)
- Endpoint `GET /api/comunicaciones/{lote_id}` — consulta estado de un lote de envío
- Endpoint `PUT /api/comunicaciones/{lote_id}/aprobar` — aprueba/rechaza un lote (si tenant requiere aprobación)
- Worker en `workers/comunicaciones_worker.py` que consulta Pendientes, envía y actualiza estado
- Guard `comunicacion:enviar` en todos los endpoints de envío
- Guard `comunicacion:aprobar` en endpoints de aprobación
- Audit log `COMUNICACION_ENVIAR` por cada lote procesado
- Scope multi-tenant: todo query filtra por tenant_id
- Aprobación configurable por tenant (flag booleano + lista de roles aprobadores)

**Non-Goals:**
- No se implementa un sistema de colas externo (RabbitMQ, Redis) — el worker consulta la DB directamente (sujeto a ADR-003)
- No se implementa envío real de emails (SMTP) en este change — el worker hace stub logging hasta integrar el provider
- No se implementa F3.4 (mensajería interna / bandeja del docente) ni F3.5 (tablón de avisos)
- No se implementa frontend de comunicaciones (es Fase 5, C-21+)
- No se implementan plantillas de comunicación con variables de sustitución (se deja para iteración futura)
- No se implementa reintento automático de fallidos en este change

## Decisions

### D1: Worker sobre DB poll vs cola externa
**Decisión**: Worker asíncrono con polling periódico a la tabla `comunicaciones` en lugar de integrar una cola externa (RabbitMQ/Redis).
**Rationale**: ADR-003 está pendiente. Una cola externa agregaría complejidad operativa y una dependencia de infraestructura que retrasaría la entrega del módulo. El polling sobre la tabla existente es simple, testeable y no introduce nuevas dependencias. Cuando ADR-003 se resuelva, el worker puede migrarse a usar la cola sin cambiar el modelo de datos.
**Alternativa descartada**: Redis RQ o Celery — requieren Redis, no hay ADR cerrado que lo justifique.

### D2: Preview como paso obligatorio con token de verificación
**Decisión**: El endpoint `POST /comunicaciones/preview` genera un `preview_token` (hash del contenido), y `POST /comunicaciones/enviar` exige ese token para confirmar que el usuario vio la preview actual.
**Rationale**: Sigue el mismo patrón que la preview de importación de calificaciones (C-09). Asegura que el contenido no cambió entre preview y envío. Si el contenido cambió, el token no coincide y el sistema rechaza el envío.
**Alternativa descartada**: Guardar la preview en sesión — introduce estado server-side que complica el escalado horizontal.

### D3: Destinatario cifrado con AES-256 en reposo
**Decisión**: La columna `destinatario` (email del alumno) se cifra con AES-256 usando el módulo de cifrado existente del proyecto.
**Rationale**: El email es PII y está marcado como `[cifrado]` en la KB (E04, E21). Todos los demás datos PII del proyecto (CBU, DNI) usan AES-256. Consistencia.
**Implementación**: El repository descifra transparentemente al leer; el service recibe el email en texto plano desde el frontend y el repository lo cifra al persistir.

### D4: Aprobación como flag booleano por tenant
**Decisión**: Cada tenant tiene un flag `aprobacion_comunicaciones_requerida` (bool) y una lista de roles que pueden aprobar. Si el flag es true, los envíos masivos (más de 1 destinatario) quedan en Pendiente hasta que un usuario con `comunicacion:aprobar` los apruebe. Si es false, el worker procesa directamente.
**Rationale**: RN-17 dice "alcance masivo" pero no define el umbral. El design asume >1 destinatario como "masivo". La configuración por tenant permite que cada institución decida su política.
**Alternativa descartada**: Configuración global fija — cada tenant puede tener necesidades distintas.

## API Design

```
POST /api/comunicaciones/preview
  Request:  {asunto, cuerpo, destinatarios: [{tipo, valor}]}
  Response: {preview_token, preview_html, cantidad_destinatarios}
  Guard: comunicacion:enviar

POST /api/comunicaciones/enviar
  Request:  {preview_token, asunto, cuerpo, materia_id, destinatarios: [{tipo, valor}]}
  Response: {lote_id, estado_agregado, total_mensajes}
  Guard: comunicacion:enviar
  Regla: preview_token debe coincidir con hash(asunto + cuerpo + destinatarios)

POST /api/comunicaciones/enviar-individual
  Request:  {preview_token, asunto, cuerpo, materia_id, entrada_padron_id}
  Response: {comunicacion_id, estado}
  Guard: comunicacion:enviar (PROFESOR: solo alumnos de sus comisiones)

GET /api/comunicaciones/{lote_id}
  Response: {lote_id, estado, total, enviados, fallidos, cancelados, pendientes}
  Guard: comunicacion:enviar

PUT /api/comunicaciones/{lote_id}/aprobar
  Request:  {accion: aprobar | rechazar}
  Response: {lote_id, estado}
  Guard: comunicacion:aprobar

GET /api/comunicaciones/mis-envios?pagina=&tamano=
  Response: {items: [{lote_id, materia, fecha, total, estado}], total, pagina}
  Guard: comunicacion:enviar

POST /api/comunicaciones/{comunicacion_id}/cancelar
  Response: {comunicacion_id, estado: Cancelado}
  Guard: comunicacion:enviar (solo comunicaciones del propio usuario en estado Pendiente)
```

## Risks / Trade-offs

- **[Worker sin cola externa]**: El polling sobre la tabla `comunicaciones` puede generar contención si hay muchos tenants encolando simultáneamente. **Mitigación**: el worker consulta con `FOR UPDATE SKIP LOCKED` y un intervalo configurable (default 5s).
- **[Aprobación bloqueante]**: Si el tenant requiere aprobación y no hay aprobadores disponibles, los mensajes quedan pendientes indefinidamente. **Mitigación**: el endpoint GET /comunicaciones/{lote_id} expone el estado; el sistema notifica a los roles aprobadores.
- **[Cifrado de destinatario]**: El cifrado AES-256 impide hacer búsquedas directas por email cifrado. **Mitigación**: las búsquedas se hacen por lote_id o por filtros no cifrados (fecha, materia, estado). No se necesita buscar por destinatario exacto.
- **[Dependencia SMTP futura]**: El worker actualmente es un stub que loggea. **Mitigación**: la interfaz `ComunicacionProvider` se define desde el inicio; se inyecta una implementación concreta (SMTP, SendGrid, etc.) sin cambiar el worker.
