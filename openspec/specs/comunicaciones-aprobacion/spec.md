# comunicaciones-aprobacion Specification

## Purpose
TBD - created by archiving change c-12-comunicaciones-cola-worker. Update Purpose after archive.
## Requirements
### Requirement: Aprobación configurable por tenant (RN-17)
El sistema SHALL permitir configurar por tenant si los envíos masivos requieren aprobación humana. Cuando la aprobación está habilitada, las comunicaciones masivas (más de un destinatario) SHALL permanecer en estado `Pendiente` hasta que un usuario con permiso `comunicacion:aprobar` las apruebe o rechace.

#### Scenario: Envío masivo con aprobación requerida
- **WHEN** el tenant tiene `aprobacion_comunicaciones_requerida=true` y se encola un envío con múltiples destinatarios
- **THEN** las comunicaciones quedan en estado `Pendiente` a la espera de aprobación.

#### Scenario: Envío individual con aprobación requerida
- **WHEN** el tenant tiene `aprobacion_comunicaciones_requerida=true` y se encola un envío con UN solo destinatario
- **THEN** el worker procesa la comunicación sin esperar aprobación.

#### Scenario: Aprobación exitosa de lote
- **WHEN** un usuario con `comunicacion:aprobar` aprueba un lote pendiente
- **THEN** las comunicaciones del lote quedan listas para que el worker las procese.

#### Scenario: Rechazo de lote
- **WHEN** un usuario con `comunicacion:aprobar` rechaza un lote pendiente
- **THEN** todas las comunicaciones del lote pasan a estado `Cancelado`.

#### Scenario: Envío masivo sin aprobación requerida
- **WHEN** el tenant tiene `aprobacion_comunicaciones_requerida=false` y se encola un envío con múltiples destinatarios
- **THEN** las comunicaciones quedan en estado `Pendiente` listas para que el worker las procese directamente.

### Requirement: Roles aprobadores por permiso
El sistema SHALL otorgar la capacidad de aprobar comunicaciones exclusivamente a usuarios con el permiso `comunicacion:aprobar`. Según la matriz de capacidades, este permiso corresponde a COORDINADOR y ADMIN.

#### Scenario: Aprobador autorizado aprueba lote
- **WHEN** un COORDINADOR con permiso `comunicacion:aprobar` accede al endpoint de aprobación
- **THEN** el sistema permite la operación.

#### Scenario: Usuario sin permiso intenta aprobar
- **WHEN** un PROFESOR sin permiso `comunicacion:aprobar` intenta acceder al endpoint de aprobación
- **THEN** el sistema rechaza la operación con error 403.

### Requirement: Visibilidad de lotes pendientes de aprobación
El sistema SHALL permitir a los usuarios con `comunicacion:aprobar` listar los lotes pendientes de aprobación en el tenant.

#### Scenario: Listar lotes pendientes
- **WHEN** un COORDINADOR consulta los lotes pendientes de aprobación
- **THEN** el sistema devuelve todos los lotes del tenant con estado `Pendiente` que requieren aprobación.

### Requirement: Auditoría de aprobación
El sistema SHALL registrar en el audit log cada acción de aprobación o rechazo de un lote de comunicaciones.

#### Scenario: Audit log al aprobar lote
- **WHEN** un COORDINADOR aprueba un lote
- **THEN** el sistema registra un evento de auditoría `COMUNICACION_ENVIAR` con metadata del aprobador, lote_id, acción "aprobar" y cantidad de mensajes.

#### Scenario: Audit log al rechazar lote
- **WHEN** un COORDINADOR rechaza un lote
- **THEN** el sistema registra un evento de auditoría `COMUNICACION_ENVIAR` con metadata del aprobador, lote_id, acción "rechazar" y cantidad de mensajes.

