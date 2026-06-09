## ADDED Requirements

### Requirement: Solicitud de recuperación por email

El sistema SHALL exponer `POST /api/auth/forgot` (sin autenticación) que recibe `{ email }`, busca el usuario por `(tenant_id, email)`, y si existe y está `is_active = true`, genera un `password_reset_token` opaco (256 bits, `secrets.token_urlsafe(32)`), guarda su hash SHA-256 con `expires_at = now() + PASSWORD_RESET_EXPIRE_MINUTES` (default 30) y `used_at = NULL`, y entrega el token al servicio de mail (interfaz `MailSender`; implementación por defecto `ConsoleMailSender` que loggea). Si el email no existe, SHALL responder `200 OK` con el mismo cuerpo genérico (no revela existencia). SHALL rate-limitar 5 requests / 60s por `(ip, email)`. SHALL registrar `PASSWORD_RESET_REQUEST` con `user_id` si el usuario existía.

#### Scenario: Solicitud exitosa

- **WHEN** un cliente envía `POST /api/auth/forgot` con un `email` existente y `is_active = true`
- **THEN** el sistema responde `200 OK` con `{ detail: "If the email is registered, a reset link has been sent" }`, crea una fila `password_reset_token` con TTL 30 min y emite un mail mock con el link. Registra `PASSWORD_RESET_REQUEST` con `user_id`

#### Scenario: Solicitud con email inexistente

- **WHEN** un cliente envía `POST /api/auth/forgot` con un `email` que no existe
- **THEN** el sistema responde `200 OK` con el mismo cuerpo genérico y NO crea ninguna fila `password_reset_token`. NO registra `PASSWORD_RESET_REQUEST`

#### Scenario: Solicitud con usuario inactivo

- **WHEN** un cliente envía `POST /api/auth/forgot` con un `email` existente pero `is_active = false`
- **THEN** el sistema responde `200 OK` con cuerpo genérico, NO crea token ni envía mail. La cuenta inactiva no se usa como vector de enumeración

#### Scenario: Múltiples solicitudes del mismo email

- **WHEN** un cliente solicita reset tres veces para el mismo `email` en pocos minutos
- **THEN** se crean tres filas `password_reset_token` activas. Solo la última es utilizable (ver reset behavior). Las anteriores siguen siendo válidas hasta su TTL; el reset SHALL invalidar TODAS las pendientes del mismo `user_id` para evitar ambigüedad

### Requirement: Reset de contraseña con token de un solo uso

El sistema SHALL exponer `POST /api/auth/reset` (sin autenticación) que recibe `{ token, new_password }`. El token es el string opaco entregado por `forgot`. El sistema SHALL hashear el token recibido con SHA-256, buscar la fila `password_reset_token` por hash, validar `expires_at > now()`, `used_at IS NULL`, y si OK, actualizar `user.password_hash` con el nuevo Argon2id, marcar el token como `used_at = now()` y marcar como `used_at` TODOS los demás tokens pendientes del mismo `user_id` (invalida la familia). El sistema SHALL responder `200 OK` con `{ detail: "Password updated" }` y registrar `PASSWORD_RESET_OK`. El sistema SHALL revocar TODOS los `refresh_token` activos del `user_id` (forzar re-login desde todos los devices).

#### Scenario: Reset exitoso

- **WHEN** un cliente envía `POST /api/auth/reset` con un `token` válido (no expirado, no usado) y `new_password` que cumple la política
- **THEN** el sistema responde `200 OK`, actualiza `password_hash`, marca el token como usado, invalida los demás tokens pendientes del `user_id`, revoca todos los `refresh_token` activos del usuario, y registra `PASSWORD_RESET_OK`

#### Scenario: Reset con token expirado

- **WHEN** un cliente envía `POST /api/auth/reset` con un `token` cuyo `expires_at < now()`
- **THEN** el sistema responde `400 Bad Request` con `{ detail: "Reset token expired" }` y NO modifica `password_hash`

#### Scenario: Reset con token ya usado

- **WHEN** un cliente envía `POST /api/auth/reset` con un `token` cuyo `used_at IS NOT NULL`
- **THEN** el sistema responde `400 Bad Request` con `{ detail: "Reset token already used" }` y NO modifica `password_hash`

#### Scenario: Reset con token desconocido

- **WHEN** un cliente envía `POST /api/auth/reset` con un `token` que no existe
- **THEN** el sistema responde `400 Bad Request` con `{ detail: "Invalid reset token" }`

#### Scenario: Reset invalida sesiones activas

- **WHEN** un usuario tenía 3 `refresh_token` activos y completa un reset exitoso
- **THEN** los 3 refresh tokens quedan con `revoked_at = now()`. El usuario debe volver a loguearse desde todos sus devices

### Requirement: Política mínima de contraseñas

El sistema SHALL exigir en `new_password` (vía `ResetRequest` y en cualquier endpoint que acepte password): mínimo 12 caracteres, al menos 1 mayúscula, 1 minúscula, 1 dígito. SHALL responder `422 Unprocessable Entity` con detalle de validación si no se cumple. La validación se hace con un validador Pydantic v2 reutilizable `StrongPassword`.

#### Scenario: Password débil rechazada

- **WHEN** un cliente envía `POST /api/auth/reset` con `new_password = "123"`
- **THEN** el sistema responde `422 Unprocessable Entity` con detalle listando las reglas que no se cumplen

#### Scenario: Password fuerte aceptada

- **WHEN** un cliente envía `POST /api/auth/reset` con `new_password = "MiPassword2026!"`
- **THEN** la validación Pydantic pasa y el endpoint procede con el reset
