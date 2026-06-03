## Context

Actualmente la auditoría en activia-trace se implementa como un logger dedicado (`core/audit.py`) que emite eventos JSON a un handler de logging con código estandarizado y payload estructurado. Esto funciona para trazabilidad en logs, pero no permite:

- Consultar el historial desde la API (necesario para F9.1 panel de auditoría y F9.2 log completo).
- Garantizar inmutabilidad real (el logger puede rotarse, borrarse, o un actor con acceso a los archivos podría modificarlos).
- Atribuir acciones bajo impersonación de forma nativa (el logger actual no tiene noción de `impersonado_id`).
- Filtrar por tenant, actor, acción, materia o rango de fechas sin parsear logs.

El sistema ya tiene C-01 (infra), C-02 (tenancy + mixins + repos base), C-03 (auth) y C-04 (RBAC) completados. Contamos con el patrón `BaseRepository` con scoping de tenant, `BaseMixin`, `EncryptedColumn`, `PermissionService`, `require_permission`, y la estructura completa de capas.

**ADR-004** (pendiente en `docs/ARQUITECTURA.md` §10) define que la estrategia de impersonación se decide al implementar esta feature: token de sesión separado vs. claim adicional en el JWT. Cerramos esa decisión aquí.

## Goals / Non-Goals

**Goals:**
- Modelo `AuditLog` persistente en DB, append-only, con todos los campos de E-AUD.
- Migración del logger `core/audit.py` a `AuditService` que persiste en DB + opcionalmente conserva el logging JSON actual.
- Endpoints de impersonación: iniciar (`POST /api/auth/impersonate`) y detener (`POST /api/auth/impersonate/stop`).
- Claim `impersonated_by` en JWT para sesiones bajo impersonación, sin token separado (cierra ADR-004).
- Permiso `impersonacion:usar` agregado al catálogo (ya existe en `PERMISOS_CATALOGO` en `core/permissions.py`).
- `AuditLogRepository` con métodos: `register()` (insert), `list()` (filtrado), `count()` (para paginación). Sin UPDATE ni DELETE.
- Restricción append-only a nivel aplicación (repository no expone update/delete) y a nivel DB (trigger PL/pgSQL).
- Tests: append-only violado → error, atribución bajo impersonación, consultas filtradas.

**Non-Goals:**
- No se implementa el panel de auditoría (F9.1, F9.2) — eso es C-19.
- No se modifican los códigos de acción existentes (se migran tal cual desde `_VALID_CODES` en `core/audit.py`).
- No se implementa retención ni purgado de audit log (append-only sin límite por ahora).
- No se agrega rate limiting específico para endpoints de impersonación (se reusa el existente).

## Decisions

### D1 — Impersonación: claim en JWT (cierra ADR-004)

**Decisión**: La impersonación usa un claim opcional `impersonated_by` en el JWT, en lugar de un token de sesión separado.

- **Alternativa A** (token separado): crear un endpoint que emita un segundo JWT con la identidad impersonada + contexto. Más seguro porque el token de impersonación puede tener una vida corta fija.
- **Alternativa B** (claim en JWT, elegida): el token existente se emite con `sub` = usuario impersonado y un claim adicional `impersonated_by` = UUID del actor real. Más simple, evita gestionar dos tokens, y el access token ya tiene vida corta (15 min).

**Rationale**: La vida corta del access token (15 min) mitiga el riesgo de un claim adicional. Si se necesita renovar la impersonación, se hace via refresh que incluye el mismo claim. La trazabilidad es completa porque `AuditService` lee `impersonated_by` del token y lo registra en `AuditLog.impersonado_id`. Simpleza > complejidad innecesaria para el MVP.

### D2 — Append-only: dual enforcement

**Decisión**: Se aplica append-only en dos niveles:

1. **Aplicación**: `AuditLogRepository` solo expone `register()` (insert). No hereda ni implementa `update()`, `soft_delete()`, ni ningún método de modificación. El modelo `AuditLog` NO hereda `BaseMixin` (no tiene `updated_at` ni `deleted_at`).
2. **Base de datos**: Trigger PL/pgSQL `CHECK` o rule que rechaza cualquier UPDATE o DELETE sobre la tabla `audit_log`. Esto es defense-in-depth contra accesos directos a la DB.

**Rationale**: El diseño del repositorio es la primera línea de defensa. El trigger de DB es la segunda línea — si alguien conecta directamente a PostgreSQL y ejecuta un UPDATE, el trigger lo rechaza.

### D3 — AuditService como reemplazo del logger actual

**Decisión**: Se crea `AuditService` con método `register(accion, actor_id, tenant_id, detalle=None, filas_afectadas=None, materia_id=None, impersonado_id=None, ip=None, user_agent=None)` que:
1. Persiste el registro en `AuditLog` via `AuditLogRepository.register()`.
2. Opcionalmente conserva el log JSON actual (configurable por settings).

El logger `core/audit.py` actual se refactoriza para delegar en `AuditService` cuando está disponible (inyectado), manteniendo el logging JSON como fallback. Los call sites existentes (`audit.log(...)`) se mantienen funcionales.

### D4 — Catálogo de códigos como constantes + DB seed

**Decisión**: Los códigos de acción se mantienen como constantes en `core/audit.py` (ya existen como `_VALID_CODES`) y se siembran en la tabla `audit_log` como seed data en la migración. No se crea una tabla separada de catálogo de códigos — el campo `accion` es un `VARCHAR` libre. La validación se hace a nivel aplicación via whitelist (defense-in-depth).

**Rationale**: Crear una tabla `codigo_accion` sería over-engineering. El set de códigos es pequeño y estable. La whitelist en `AuditService.register()` rechaza códigos no reconocidos.

### D5 — Sin cascada de permisos `(propio)` en audit log

**Decisión**: El permiso `auditoria:ver` (ya existente en `PERMISOS_CATALOGO`) permite ver los registros del tenant. El scope `(propio)` del COORDINADOR se implementa a nivel de query en el repository: si el usuario NO tiene `auditoria:ver` global, se filtran solo los registros donde `actor_id` = usuario actual. Esto se define en C-19 (panel de auditoría), no en este change. En C-05 solo se crea el repositorio con capacidad de filtrar por `actor_id`.

## Risks / Trade-offs

| Riesgo | Mitigación |
|--------|------------|
| **R1 — Performance**: insertar un audit log por cada acción significativa puede sumar latency si la tabla crece mucho | El insert es lightweight (una fila, pocos campos, sin joins). Se monitorea en C-19. Si es necesario, se agrega inserción asíncrona (cola en memoria o worker) como mejora futura. |
| **R2 — Crecimiento de la tabla**: append-only sin purga = la tabla crece indefinidamente | Para MVP no hay límite. Cuando se implemente C-19 se evalúa si agregar retención configurable por tenant o particionado por fecha. |
| **R3 — Impersonación mal usada**: un ADMIN con `impersonacion:usar` podría operar sin dejar rastro claro | Cada inicio y fin de impersonación se registra en audit log con `IMPERSONACION_INICIAR` / `IMPERSONACION_FINALIZAR`. Toda acción bajo impersonación registra `impersonado_id`. |
| **R4 — Rotura de call sites existentes**: el refactor de `core/audit.py` podría romper código que usa `audit.log()` | Se mantiene compatibilidad hacia atrás: `audit.log()` delega en `AuditService` si está disponible, y sigue emitiendo JSON logger como fallback. |
