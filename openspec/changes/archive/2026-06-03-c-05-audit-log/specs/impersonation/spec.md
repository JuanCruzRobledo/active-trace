# impersonation Specification

## Purpose
Define el sistema de impersonación (suplantación legítima) que permite a usuarios autorizados operar temporalmente en nombre de otro usuario para diagnóstico o asistencia, con trazabilidad completa de todas las acciones.

## ADDED Requirements

### Requirement: Permiso de impersonación

El sistema SHALL requerir el permiso `impersonacion:usar` para iniciar una sesión de impersonación. Este permiso SHALL estar asignado al rol ADMIN (y opcionalmente a otros roles según el catálogo del tenant).

#### Scenario: Usuario sin permiso no puede impersonar
- **WHEN** un usuario autenticado SIN permiso `impersonacion:usar` intenta acceder al endpoint de impersonación
- **THEN** el sistema responde `403 Forbidden`

#### Scenario: Usuario con permiso puede impersonar
- **WHEN** un usuario autenticado CON permiso `impersonacion:usar` llama al endpoint de impersonación
- **THEN** la operación continúa a la validación del target

### Requirement: Inicio de impersonación

El sistema SHALL exponer `POST /api/auth/impersonate` que recibe un `target_user_id` (UUID del usuario a impersonar) y, si el actor tiene permiso `impersonacion:usar`:
1. Verifica que el target exista y esté activo dentro del mismo tenant
2. Registra `IMPERSONACION_INICIAR` en el audit log con `actor_id` (quien impersona) y `impersonado_id` (target)
3. Emite un nuevo JWT access token con `sub = target_user_id` y claim adicional `impersonated_by = actor_id`
4. Retorna el nuevo token pair (access + refresh)

#### Scenario: Iniciar impersonación exitosa
- **WHEN** el actor (ADMIN) envía `POST /api/auth/impersonate` con `target_user_id` de un usuario activo en el mismo tenant
- **THEN** el sistema retorna un token pair con access token cuyo `sub` es el target y claim `impersonated_by` es el actor

#### Scenario: Target no existe retorna 404
- **WHEN** el actor envía `target_user_id` de un usuario inexistente
- **THEN** el sistema responde `404 Not Found`

#### Scenario: Target de otro tenant retorna 404
- **WHEN** el actor envía `target_user_id` de un usuario de otro tenant
- **THEN** el sistema responde `404 Not Found` (no revela existencia entre tenants)

#### Scenario: Target inactivo retorna 400
- **WHEN** el actor envía `target_user_id` de un usuario con `estado = Inactivo`
- **THEN** el sistema responde `400 Bad Request`

### Requirement: Sesión distinguible bajo impersonación

El sistema SHALL generar tokens de acceso bajo impersonación que sean claramente distinguibles de una sesión normal mediante el claim `impersonated_by` en el JWT.

#### Scenario: Token normal no tiene impersonated_by
- **WHEN** se emite un token por login normal
- **THEN** el JWT NO contiene el claim `impersonated_by`

#### Scenario: Token de impersonación tiene impersonated_by
- **WHEN** se emite un token por inicio de impersonación
- **THEN** el JWT contiene `impersonated_by` con el UUID del actor real

#### Scenario: Dependencia get_current_user distingue impersonación
- **WHEN** `get_current_user` decodifica un token con `impersonated_by`
- **THEN** el `UserContext` retornado incluye `impersonated_by_id` con el UUID del actor real

### Requirement: Todas las acciones bajo impersonación registran al actor real

El sistema SHALL garantizar que toda acción realizada bajo una sesión de impersonación quede atribuida al actor real (quien impersona), no al usuario impersonado. `AuditService.register()` SHALL recibir `impersonado_id` desde el `UserContext` actual.

#### Scenario: Auditoría registra actor real + impersonado
- **WHEN** un usuario impersonado realiza una acción significativa (ej: importar calificaciones)
- **THEN** el audit log registra `actor_id = actor_real` y `impersonado_id = usuario_impersonado`

#### Scenario: Auditoría sin impersonación tiene impersonado_id nulo
- **WHEN** un usuario normal (sin impersonación) realiza una acción
- **THEN** el audit log registra `actor_id = usuario_actual` y `impersonado_id = NULL`

### Requirement: Detención de impersonación

El sistema SHALL exponer `POST /api/auth/impersonate/stop` que:
1. Toma el token actual con `impersonated_by` y lo invalida
2. Registra `IMPERSONACION_FINALIZAR` en el audit log con `actor_id` y `impersonado_id`
3. Retorna al token normal del actor (el que tenía antes de impersonar)

#### Scenario: Detener impersonación exitosa
- **WHEN** un usuario bajo impersonación llama a `POST /api/auth/impersonate/stop`
- **THEN** el sistema invalida el token actual, registra `IMPERSONACION_FINALIZAR` y retorna un nuevo token pair para el actor real

#### Scenario: Usuario sin impersonación no puede detener
- **WHEN** un usuario sin sesión de impersonación activa llama a `POST /api/auth/impersonate/stop`
- **THEN** el sistema responde `400 Bad Request`

### Requirement: Refresh rotation bajo impersonación

El sistema SHALL mantener el claim `impersonated_by` durante la rotación de tokens mientras la impersonación esté activa.

#### Scenario: Refresh conserva impersonated_by
- **WHEN** un usuario bajo impersonación hace refresh del token
- **THEN** el nuevo access token conserva el claim `impersonated_by`
