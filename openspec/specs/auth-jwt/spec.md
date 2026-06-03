# auth-jwt Specification

## Purpose
TBD - created by archiving change c-03-auth-jwt-2fa. Update Purpose after archive.
## Requirements
### Requirement: Login por email y contraseña

El sistema SHALL autenticar a un usuario contra el `tenant` correcto utilizando `email` + `password` (Argon2id). La verificación de credenciales se hace server-side consultando la fila `user` filtrada por `tenant_id` (resuelto del header `X-Tenant-Id` del request de bootstrap) y `email`. Si las credenciales son válidas y el usuario tiene `is_active = true` y `totp_enabled = false`, el sistema SHALL emitir un par de tokens (access + refresh). Si `totp_enabled = true`, SHALL emitir un `challenge_token` opaco en lugar de los tokens, con TTL de 5 minutos. Si las credenciales son inválidas o el usuario está inactivo, SHALL responder `401 Unauthorized` con un cuerpo genérico que NO revela si el email existe. Todos los intentos (exitosos y fallidos) SHALL quedar registrados con un `code` de auditoría (`LOGIN_OK` o `LOGIN_FAIL`).

#### Scenario: Login exitoso sin 2FA

- **WHEN** el cliente envía `POST /api/auth/login` con `{ email, password }` válidos para un usuario `is_active = true` y `totp_enabled = false`
- **THEN** el sistema responde `200 OK` con `{ access_token, refresh_token, token_type: "bearer", expires_in: 900 }` y registra `LOGIN_OK` con `user_id` y `tenant_id`

#### Scenario: Login con credenciales inválidas

- **WHEN** el cliente envía `POST /api/auth/login` con `email` existente y `password` incorrecto
- **THEN** el sistema responde `401 Unauthorized` con `{ detail: "Invalid credentials" }` y registra `LOGIN_FAIL` con el `email` y motivo `bad_password`. El response NO debe distinguir entre "email no existe" y "password incorrecto"

#### Scenario: Login con email inexistente

- **WHEN** el cliente envía `POST /api/auth/login` con `email` que no existe en el `tenant`
- **THEN** el sistema responde `401 Unauthorized` con el mismo cuerpo que credenciales inválidas, y registra `LOGIN_FAIL` con motivo `unknown_email`

#### Scenario: Login con usuario inactivo

- **WHEN** el cliente envía `POST /api/auth/login` con credenciales válidas de un usuario con `is_active = false`
- **THEN** el sistema responde `401 Unauthorized` y registra `LOGIN_FAIL` con motivo `inactive_user`. NO emite tokens

#### Scenario: Login con 2FA habilitado devuelve challenge

- **WHEN** el cliente envía `POST /api/auth/login` con credenciales válidas de un usuario con `totp_enabled = true`
- **THEN** el sistema responde `200 OK` con `{ "2fa_required": true, "challenge_token": "<opaque>" }` y registra `LOGIN_2FA_REQUIRED`. NO emite access ni refresh

### Requirement: Refresh token con rotación y detección de reuso

El sistema SHALL emitir un refresh token con TTL configurable (`REFRESH_TOKEN_EXPIRE_DAYS`, default 7) y HASHEARLO con SHA-256 antes de persistirlo. El `POST /api/auth/refresh` SHALL recibir un refresh token, localizar la fila por hash, validar que `expires_at > now()` y `revoked_at IS NULL`, emitir un par nuevo, marcar el refresh presentado como `revoked_at = now()` y apuntar `replaced_by_id` al nuevo. Si el refresh presentado está `revoked_at` no nulo (reuso), SHALL revocar TODA la familia de tokens del mismo `user_id` (poner `revoked_at` en todos los siblings que aún no lo tengan) y responder `401 Unauthorized`. El endpoint SHALL registrar `REFRESH_OK` o `REFRESH_REUSE_DETECTED`.

#### Scenario: Refresh exitoso

- **WHEN** el cliente envía `POST /api/auth/refresh` con un refresh token válido y no revocado
- **THEN** el sistema responde `200 OK` con un par nuevo, marca el refresh presentado como revocado y registra `REFRESH_OK`

#### Scenario: Refresh con token expirado

- **WHEN** el cliente envía `POST /api/auth/refresh` con un refresh token cuyo `expires_at < now()`
- **THEN** el sistema responde `401 Unauthorized` con `{ detail: "Refresh token expired" }` y NO emite tokens nuevos

#### Scenario: Refresh con reuso detecta familia comprometida

- **WHEN** el cliente envía `POST /api/auth/refresh` con un refresh token cuyo `revoked_at IS NOT NULL`
- **THEN** el sistema responde `401 Unauthorized`, marca como revocados TODOS los refresh tokens del mismo `user_id` que aún no lo estén, y registra `REFRESH_REUSE_DETECTED` con el `user_id` y la cantidad de tokens revocados

#### Scenario: Refresh con token desconocido

- **WHEN** el cliente envía `POST /api/auth/refresh` con un refresh token que no existe en DB
- **THEN** el sistema responde `401 Unauthorized` con `{ detail: "Invalid refresh token" }`

### Requirement: Logout revoca el refresh presentado

El sistema SHALL permitir `POST /api/auth/logout` (autenticado con access token) que recibe un refresh token en el body, lo busca por hash, y si pertenece al `user_id` del JWT y no está revocado, lo marca `revoked_at = now()`. SHALL responder `204 No Content`. SHALL registrar `LOGOUT` con `user_id`.

#### Scenario: Logout revoca un refresh válido

- **WHEN** el cliente autenticado envía `POST /api/auth/logout` con el refresh token actual
- **THEN** el sistema responde `204 No Content`, marca el refresh como revocado y registra `LOGOUT`

#### Scenario: Logout con refresh de otro usuario

- **WHEN** el cliente autenticado envía `POST /api/auth/logout` con un refresh que pertenece a otro `user_id`
- **THEN** el sistema responde `404 Not Found` (no expone existencia) y NO registra logout

#### Scenario: Logout con refresh ya revocado

- **WHEN** el cliente autenticado envía `POST /api/auth/logout` con un refresh ya revocado
- **THEN** el sistema responde `204 No Content` (idempotente) y NO registra un segundo `LOGOUT`

### Requirement: Identidad derivada EXCLUSIVAMENTE del JWT verificado

El sistema SHALL exponer una dependencia `get_current_user` que extrae `user_id`, `tenant_id` y `roles` ÚNICAMENTE del payload del access JWT verificado con `SECRET_KEY` y algoritmo `HS256`. Si el token está expirado, mal formado o la firma no valida, SHALL responder `401 Unauthorized` con `{ detail: "Invalid or expired token" }`. Ningún parámetro de query string, body ni header distinto a `Authorization: Bearer <token>` SHALL poder alterar la identidad resuelta.

#### Scenario: Acceso con token válido

- **WHEN** un cliente hace una request con `Authorization: Bearer <access_token>` firmado correctamente y no expirado
- **THEN** `get_current_user` retorna un `UserContext` con `user_id` y `tenant_id` que coinciden con el payload del JWT. El sistema NO consulta la DB para resolver identidad (la fila se consulta solo si un endpoint lo pide explícitamente para datos como `email` o `is_active`)

#### Scenario: Acceso sin token

- **WHEN** un cliente hace una request sin header `Authorization`
- **THEN** el sistema responde `401 Unauthorized` con `{ detail: "Not authenticated" }` sin distinguir "sin header" de "header malformado"

#### Scenario: Acceso con token expirado

- **WHEN** un cliente hace una request con un access token cuyo `exp < now()`
- **THEN** el sistema responde `401 Unauthorized` con `{ detail: "Token expired" }`

#### Scenario: Acceso con token de firma inválida

- **WHEN** un cliente hace una request con un token firmado con un `SECRET_KEY` distinto
- **THEN** el sistema responde `401 Unauthorized` y registra el evento como log de seguridad con `code = "TOKEN_SIGNATURE_INVALID"`

#### Scenario: Intento de suplantación por query string

- **WHEN** un cliente hace una request con `Authorization: Bearer <token_A>` Y `?user_id=<otro_uuid>` en la URL
- **THEN** `get_current_user` resuelve la identidad del token (usuario A); el `user_id` de la query es tratado como dato de entrada, no como identidad. Un endpoint que reciba `user_id` en su firma SHALL compararlo con el `user_id` del contexto y responder `403` si no coinciden

### Requirement: Rate limit en login y endpoints sensibles

El sistema SHALL aplicar un rate limit de 5 requests por 60 segundos por combinación `(ip_cliente, email_destino)` en los endpoints `POST /api/auth/login`, `POST /api/auth/2fa/verify`, `POST /api/auth/forgot` y `POST /api/auth/reset`. Al alcanzar el límite, SHALL responder `429 Too Many Requests` con `Retry-After: <segundos>` y registrar `RATE_LIMIT_HIT`.

#### Scenario: 5 intentos fallidos en 60s

- **WHEN** un cliente hace 5 requests fallidos a `/login` con el mismo `email` desde la misma IP en menos de 60 segundos
- **THEN** la sexta request responde `429 Too Many Requests` con header `Retry-After: <segundos_hasta_reset>` y registra `RATE_LIMIT_HIT` con `ip` y `email`

#### Scenario: IPs distintas no comparten contador

- **WHEN** un cliente hace 5 requests fallidos desde IP A, y un cliente desde IP B intenta con el mismo `email`
- **THEN** el cliente desde IP B recibe respuesta normal (no 429) porque su contador es independiente

#### Scenario: Reset del contador después de 60s

- **WHEN** un cliente alcanzó el rate limit y espera 60 segundos sin nuevas requests
- **THEN** la siguiente request es procesada normalmente (contador reseteado)

