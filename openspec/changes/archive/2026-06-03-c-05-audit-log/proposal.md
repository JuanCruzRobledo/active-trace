## Why

El sistema actual registra auditoría únicamente a un logger JSON (`core/audit.py`), sin persistencia en base de datos. Esto impide:
- Consultar el historial de acciones desde la aplicación (necesario para F9.1, F9.2).
- Garantizar inmutabilidad real (append-only a nivel DB, no solo a nivel logger).
- Atribuir correctamente acciones bajo impersonación (quién hizo realmente la acción vs. en nombre de quién).
- Tener un registro centralizado que pueda ser filtrado por tenant, actor, acción, materia y rango de fechas.

El nombre del producto es *trace* — todo audita. Necesitamos migrar del logger volátil a un modelo persistente append-only que sea la fuente de verdad de toda acción significativa.

## What Changes

- **Nuevo modelo `AuditLog`** (E-AUD) con campos: `id`, `tenant_id`, `fecha_hora`, `actor_id`, `impersonado_id`, `materia_id`, `accion`, `detalle` (JSON), `filas_afectadas`, `ip`, `user_agent`.
- **Restricción append-only**: sin UPDATE ni DELETE a nivel aplicación y a nivel base de datos (trigger o constraint).
- **Helper/decorator de auditoría** para registrar acciones con códigos estandarizados (ej: `CALIFICACIONES_IMPORTAR`, `PADRON_CARGAR`).
- **Servicio `AuditService`** como reemplazo del logger actual: los call sites existentes (`audit.log()`) migran a `AuditService.register()`.
- **Impersonación**: endpoint `POST /api/auth/impersonate` (permiso `impersonacion:usar`), sesión distinguible en JWT (claim `impersonated_by`), todas las acciones bajo impersonación registran al actor real.
- **Migración Alembic 006**: creación de tabla `audit_log`.
- **Repo `AuditLogRepository`** con métodos append-only y consultas con filtros (tenant, actor, acción, rango de fechas).
- **Tests**: append-only validado, atribución bajo impersonación, registro con código + filas afectadas, consultas con filtros.

## Capabilities

### New Capabilities
- `audit-log`: Persistencia append-only de acciones significativas con consultas filtrables y códigos estandarizados.
- `impersonation`: Suplantación legítima con sesión distinguible, permiso dedicado y trazabilidad completa.

### Modified Capabilities
<!-- No existing specs change — esto es nuevo. Audit previo era un logger sin spec. -->

## Impact

- **Backend**: nuevo modelo `AuditLog`, repositorio `AuditLogRepository`, servicio `AuditService`, helper en `core/audit.py` se refactoriza para usar la DB.
- **API**: nuevo endpoint `POST /api/auth/impersonate`, extendido `POST /api/auth/impersonate/stop`.
- **Auth**: JWT modificado para soportar claim `impersonated_by` (opcional).
- **Permisos**: se agrega `impersonacion:usar` al catálogo de permisos.
- **Migraciones**: nueva migración `006_audit_log.py`.
- **Tests**: nuevos tests unitarios e integration para audit log e impersonación.
