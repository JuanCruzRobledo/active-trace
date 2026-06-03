## 1. Modelo y Migración

- [x] 1.1 Crear el modelo `AuditLog` en `app/models/audit_log.py` (NO hereda `BaseMixin`, sin `updated_at` ni `deleted_at`, con campos: `id`, `tenant_id`, `fecha_hora`, `actor_id`, `impersonado_id`, `materia_id`, `accion`, `detalle`, `filas_afectadas`, `ip`, `user_agent`)
- [x] 1.2 Registrar `AuditLog` en `app/models/__init__.py`
- [x] 1.3 Crear migración Alembic `006_audit_log.py` con la tabla `audit_log` + seed de códigos de acción como comentario
- [x] 1.4 Crear script SQL `alembic/scripts/001_audit_log_trigger.sql` con el trigger PL/pgSQL que rechaza UPDATE/DELETE en `audit_log`
- [x] 1.5 Incluir la ejecución del trigger en la migración `006` (op.execute del SQL)

## 2. Repositorio Append-Only

- [x] 2.1 Crear `AuditLogRepository` en `app/repositories/audit_log_repository.py` con métodos:
  - `register(tenant_id, actor_id, accion, detalle=None, filas_afectadas=None, materia_id=None, impersonado_id=None, ip=None, user_agent=None)` → insert + flush
  - `get_by_id(id)` → retorna un registro por ID (scoped por tenant)
  - `list(*, actor_id=None, accion=None, materia_id=None, fecha_hora_desde=None, fecha_hora_hasta=None, offset=0, limit=50)` → retorna registros paginados ordenados por `fecha_hora DESC`
  - `count(*, actor_id=None, accion=None, materia_id=None, fecha_hora_desde=None, fecha_hora_hasta=None)` → retorna total de registros coincidentes
- [x] 2.2 NO heredar métodos de modificación (sin `update`, `soft_delete`). El repositorio solo extiende lo necesario de `BaseRepository` (scoping de tenant, get_by_id heredado si aplica)
- [x] 2.3 NO incluir `deleted_at` filter en el scoping de tenant para este modelo (no tiene soft delete)

## 3. Servicio de Auditoría

- [x] 3.1 Crear `AuditService` en `app/services/audit_service.py` con:
  - `__init__(self, audit_log_repo, settings)` — inyección de dependencias
  - `register(accion, actor_id, tenant_id, *, detalle=None, filas_afectadas=None, materia_id=None, impersonado_id=None, ip=None, user_agent=None)` → valida código contra whitelist + persiste vía repo
  - Whitelist de códigos (constantes + set de validación) reusando `_VALID_CODES` desde `core/audit.py`
- [x] 3.2 Refactorizar `core/audit.py` actual para que delegue en `AuditService` cuando esté disponible, manteniendo el logger JSON como fallback
- [x] 3.3 Asegurar que `AuditService.register()` sea invocado desde los call sites existentes (auth service, etc.)

## 4. Impersonación — Backend

- [x] 4.1 Agregar el permiso `impersonacion:usar` al catálogo en `core/permissions.py` si no existe (verificar `PERMISOS_CATALOGO`)
- [x] 4.2 Extender `UserContext` en `core/dependencies.py` para incluir `impersonated_by_id: str | None`
- [x] 4.3 Modificar `token_service.py` para soportar el claim opcional `impersonated_by` en el JWT:
  - `create_access_token()` acepta `impersonated_by: str | None = None` (via `extra_claims`)
  - `create_refresh_token()` acepta `impersonated_by: str | None = None`
- [x] 4.4 Crear router `app/api/v1/routers/impersonation.py` con endpoints:
  - `POST /api/auth/impersonate` → body `{"target_user_id": "uuid"}` → verifica permiso `impersonacion:usar`, verifica target activo y del mismo tenant, registra `IMPERSONACION_INICIAR`, emite nuevo token pair con claim `impersonated_by`
  - `POST /api/auth/impersonate/stop` → verifica que el token actual tenga `impersonated_by`, registra `IMPERSONACION_FINALIZAR`, invalida token actual, retorna token pair normal del actor
- [x] 4.5 Modificar `get_current_user` en `dependencies.py` para extraer el claim `impersonated_by` del JWT y pasarlo al `UserContext`
- [x] 4.6 Modificar `refresh()` en el router de auth para conservar `impersonated_by` durante refresh rotation
- [x] 4.7 Agregar los nuevos endpoints al `__init__.py` de routers

## 5. Tests Unitarios

- [x] 5.1 Test: `AuditLogRepository.register()` inserta un registro correctamente
- [x] 5.2 Test: `AuditLogRepository.register()` con todos los campos opcionales
- [x] 5.3 Test: `AuditLogRepository.list()` retorna registros paginados ordenados por fecha DESC
- [x] 5.4 Test: `AuditLogRepository.list()` filtra por `actor_id`
- [x] 5.5 Test: `AuditLogRepository.list()` filtra por `accion` + rango de fechas
- [x] 5.6 Test: `AuditLogRepository.count()` con y sin filtros
- [x] 5.7 Test: `AuditService.register()` con código válido persiste
- [x] 5.8 Test: `AuditService.register()` con código inválido lanza error y NO persiste
- [x] 5.9 Test: `AuditService.register()` con impersonación registra `actor_id` + `impersonado_id`
- [x] 5.10 Test: el repositorio NO tiene métodos `update()` ni `delete()` (assert de atributos)

## 6. Tests de Integración — Impersonación

- [x] 6.1 Test: iniciar impersonación con ADMIN con permiso → 200 + token con `impersonated_by`
- [x] 6.2 Test: iniciar impersonación sin permiso → 403
- [x] 6.3 Test: iniciar impersonación a usuario inexistente → 404
- [x] 6.4 Test: iniciar impersonación a usuario de otro tenant → 404
- [x] 6.5 Test: detener impersonación → 200 + registra `IMPERSONACION_FINALIZAR`
- [x] 6.6 Test: detener impersonación sin estar impersonando → 400
- [x] 6.7 Test: refresh conserva `impersonated_by`
- [x] 6.8 Test: acción bajo impersonación registra `actor_id` real en audit log
- [x] 6.9 Test: acción sin impersonación registra `impersonado_id = NULL`

## 7. Integración y Verificación

- [x] 7.1 Verificar que `core/audit.py` siga funcionando como fallback (tests existentes de auth pasan)
- [x] 7.2 Verificar que el trigger SQL se ejecuta correctamente en la migración
- [x] 7.3 Verificar que todos los tests existentes siguen pasando (safety net)
- [x] 7.4 Ejecutar `coverage run -m pytest` y verificar ≥80% líneas, ≥90% reglas de negocio
