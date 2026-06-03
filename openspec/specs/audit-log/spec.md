# audit-log Specification

## Purpose
TBD - created by archiving change c-05-audit-log. Update Purpose after archive.
## Requirements
### Requirement: Modelo AuditLog

El sistema SHALL exponer un modelo `AuditLog` en la tabla `audit_log` con los siguientes campos:
- `id`: UUID (PK)
- `tenant_id`: UUID (FK → Tenant, NOT NULL)
- `fecha_hora`: DateTime with timezone, default UTC now
- `actor_id`: UUID (FK → Usuario, NOT NULL) — quien realizó la acción
- `impersonado_id`: UUID (FK → Usuario, nullable) — usuario impersonado, nulo si no hay impersonación
- `materia_id`: UUID (FK → Materia, nullable)
- `accion`: VARCHAR(100) — código estandarizado (ej: `CALIFICACIONES_IMPORTAR`)
- `detalle`: JSONB — contexto adicional de la acción
- `filas_afectadas`: Integer — cantidad de registros involucrados (nullable)
- `ip`: VARCHAR(45) — dirección IP del cliente (nullable)
- `user_agent`: Text — agente de usuario (nullable)

NO SHALL tener `updated_at` ni `deleted_at`. NO SHALL heredar `BaseMixin`.

#### Scenario: Crear registro de auditoría
- **WHEN** se registra una acción con todos los campos obligatorios (`tenant_id`, `actor_id`, `accion`)
- **THEN** el registro se persiste con `id`, `fecha_hora` y los campos proporcionados

#### Scenario: Registro con impersonación
- **WHEN** se registra una acción bajo impersonación con `actor_id` y `impersonado_id`
- **THEN** el registro persiste ambos identificadores

#### Scenario: Registro con detalle JSON
- **WHEN** se registra una acción con `detalle` como objeto JSON
- **THEN** el detalle se almacena como JSONB y puede consultarse

#### Scenario: Registrar acción con materia opcional
- **WHEN** se registra una acción que no está asociada a ninguna materia
- **THEN** `materia_id` es NULL

### Requirement: Append-only enforcement

El sistema SHALL garantizar que ningún registro de auditoría pueda ser modificado ni eliminado, ni a nivel aplicación ni a nivel base de datos.

#### Scenario: Repositorio no expone update ni delete
- **WHEN** se intenta llamar a un método `update()` o `delete()` en `AuditLogRepository`
- **THEN** el repositorio NO tiene esos métodos (solo `register()`, `list()`, `count()`, `get_by_id()`)

#### Scenario: Trigger de DB rechaza UPDATE directo
- **WHEN** se ejecuta un `UPDATE audit_log SET ...` directamente en la base de datos
- **THEN** el trigger PL/pgSQL rechaza la operación con un error

#### Scenario: Trigger de DB rechaza DELETE directo
- **WHEN** se ejecuta un `DELETE FROM audit_log` directamente en la base de datos
- **THEN** el trigger PL/pgSQL rechaza la operación con un error

### Requirement: Validación de códigos de acción

El sistema SHALL validar que el código de acción (`accion`) pertenezca a una whitelist de códigos conocidos antes de persistir.

#### Scenario: Código válido es aceptado
- **WHEN** se registra una acción con `accion = "CALIFICACIONES_IMPORTAR"`
- **THEN** el registro se persiste sin error

#### Scenario: Código inválido es rechazado
- **WHEN** se registra una acción con `accion = "CODIGO_INEXISTENTE"`
- **THEN** el sistema lanza `ValueError` o `HTTPException(400)` y NO persiste el registro

### Requirement: Consultas filtradas

El sistema SHALL exponer métodos de consulta en `AuditLogRepository` que permitan filtrar por:
- `tenant_id` (siempre aplicado por el repositorio base)
- `actor_id` (opcional)
- `accion` (opcional)
- `materia_id` (opcional)
- Rango de fechas `fecha_hora_desde` / `fecha_hora_hasta` (opcional)
- Paginación `offset` / `limit`

#### Scenario: Listar todos los registros del tenant
- **WHEN** se llama a `list()` sin filtros
- **THEN** retorna todos los registros del tenant actual, ordenados por `fecha_hora DESC`, paginados

#### Scenario: Filtrar por actor
- **WHEN** se llama a `list(actor_id=...)` 
- **THEN** retorna solo los registros de ese actor

#### Scenario: Filtrar por acción y rango de fechas
- **WHEN** se llama a `list(accion="CALIFICACIONES_IMPORTAR", fecha_hora_desde=..., fecha_hora_hasta=...)`
- **THEN** retorna solo los registros con esa acción en ese rango

#### Scenario: Contar registros con filtros
- **WHEN** se llama a `count(accion="...")`
- **THEN** retorna el número total de registros que coinciden (sin paginación)

### Requirement: Códigos de acción estandarizados

El sistema SHALL incluir al menos los siguientes códigos de acción en la whitelist:
- `CALIFICACIONES_IMPORTAR`
- `PADRON_CARGAR`
- `COMUNICACION_ENVIAR`
- `ASIGNACION_MODIFICAR`
- `LIQUIDACION_CERRAR`
- `IMPERSONACION_INICIAR`
- `IMPERSONACION_FINALIZAR`

#### Scenario: Todos los códigos del seed son válidos
- **WHEN** se registra una acción con cualquiera de los códigos de la whitelist
- **THEN** el registro se persiste exitosamente

