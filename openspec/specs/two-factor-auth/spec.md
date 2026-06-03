# two-factor-auth Specification

## Purpose
TBD - created by archiving change c-03-auth-jwt-2fa. Update Purpose after archive.
## Requirements
### Requirement: Enrolamiento de TOTP

El sistema SHALL exponer `POST /api/auth/2fa/enroll` (autenticado con access token) que genera un secret TOTP (160 bits, base32) usando `pyotp.random_base32()`, lo cifra con `EncryptionService` (Fernet, llave de `ENCRYPTION_KEY`) y lo guarda en `user.totp_secret`, devuelve `{ secret, otpauth_uri, qr_png_base64 }` (URI en formato estándar `otpauth://totp/<TOTP_ISSUER>:<email>?secret=<...>&issuer=<...>`; PNG generado con `qrcode`), y registra `TOTP_ENROLL_STARTED`. El usuario debe confirmar el secret con un código válido en `POST /api/auth/2fa/confirm` antes de que `totp_enabled` pase a `true`.

#### Scenario: Enrolamiento de un usuario sin 2FA

- **WHEN** un cliente autenticado con `is_active = true` y `totp_enabled = false` envía `POST /api/auth/2fa/enroll`
- **THEN** el sistema responde `200 OK` con `{ secret, otpauth_uri, qr_png_base64 }`, persiste el secret cifrado, y registra `TOTP_ENROLL_STARTED`. `totp_enabled` sigue en `false`

#### Scenario: Enrolamiento cuando 2FA ya está activo

- **WHEN** un cliente autenticado con `totp_enabled = true` envía `POST /api/auth/2fa/enroll`
- **THEN** el sistema responde `409 Conflict` con `{ detail: "2FA is already enrolled" }` y NO regenera el secret

### Requirement: Confirmación del secret TOTP

El sistema SHALL exponer `POST /api/auth/2fa/confirm` (autenticado) que recibe `{ code }` (6 dígitos), descifra el secret guardado, valida el código con `pyotp.TOTP(secret).verify(code, valid_window=1)`, y si es válido, pone `user.totp_enabled = true` y registra `TOTP_ENROLL_CONFIRMED`. Si el código no es válido, SHALL responder `400 Bad Request` y mantener `totp_enabled = false`.

#### Scenario: Confirmación exitosa

- **WHEN** un cliente autenticado con un secret TOTP pendiente envía `POST /api/auth/2fa/confirm` con el código TOTP actual de 6 dígitos
- **THEN** el sistema responde `200 OK`, pone `totp_enabled = true` y registra `TOTP_ENROLL_CONFIRMED`

#### Scenario: Confirmación con código incorrecto

- **WHEN** un cliente envía un código que no coincide con el TOTP del secret
- **THEN** el sistema responde `400 Bad Request` con `{ detail: "Invalid TOTP code" }` y `totp_enabled` permanece en `false`

#### Scenario: Confirmación con secret inexistente

- **WHEN** un cliente sin `totp_secret` guardado envía `POST /api/auth/2fa/confirm`
- **THEN** el sistema responde `400 Bad Request` con `{ detail: "No 2FA enrollment in progress" }`

### Requirement: Verificación post-login cuando 2FA está habilitado

El sistema SHALL exponer `POST /api/auth/2fa/verify` (sin autenticación previa) que recibe `{ challenge_token, code }`. El `challenge_token` es el string opaco devuelto por `login` cuando `totp_enabled = true`. El sistema SHALL hashear el challenge, buscar la fila `two_factor_challenge` por hash, validar `expires_at > now()` y `used_at IS NULL`, descifrar el `totp_secret` del `user_id` asociado, validar el código TOTP, y si OK, emitir par access+refresh, marcar el challenge como usado y registrar `LOGIN_2FA_OK`. Si el código es inválido, SHALL responder `401 Unauthorized` y registrar `LOGIN_2FA_FAIL`. Si el challenge está expirado/usado, SHALL responder `401 Unauthorized` con detalle específico.

#### Scenario: Verificación 2FA exitosa

- **WHEN** un cliente envía `POST /api/auth/2fa/verify` con `challenge_token` válido y `code` TOTP correcto
- **THEN** el sistema responde `200 OK` con `{ access_token, refresh_token, token_type: "bearer", expires_in: 900 }`, marca el challenge como usado, y registra `LOGIN_2FA_OK`

#### Scenario: Verificación 2FA con código incorrecto

- **WHEN** un cliente envía `POST /api/auth/2fa/verify` con `challenge_token` válido y `code` TOTP incorrecto
- **THEN** el sistema responde `401 Unauthorized` con `{ detail: "Invalid 2FA code" }` y registra `LOGIN_2FA_FAIL`. El challenge sigue siendo válido hasta su TTL o el próximo intento válido

#### Scenario: Verificación 2FA con challenge expirado

- **WHEN** un cliente envía `POST /api/auth/2fa/verify` con un `challenge_token` cuyo `expires_at < now()`
- **THEN** el sistema responde `401 Unauthorized` con `{ detail: "2FA challenge expired" }`. El usuario debe volver a `/login`

#### Scenario: Verificación 2FA con challenge ya usado

- **WHEN** un cliente envía `POST /api/auth/2fa/verify` con un `challenge_token` cuyo `used_at IS NOT NULL`
- **THEN** el sistema responde `401 Unauthorized` con `{ detail: "2FA challenge already used" }`

### Requirement: Aislamiento de tenant en todo flujo 2FA

El sistema SHALL resolver el `tenant_id` del usuario (de la fila `user` asociada al challenge_token o al JWT) y SHALL filtrar todas las consultas de `user`, `two_factor_challenge` y `totp_secret` por ese `tenant_id`. Ningún challenge ni secret es accesible cross-tenant.

#### Scenario: Challenge de otro tenant rechazado

- **WHEN** un cliente envía un `challenge_token` creado en tenant A pero el header `X-Tenant-Id` apunta a tenant B
- **THEN** el sistema responde `401 Unauthorized` con `{ detail: "Invalid 2FA challenge" }` y registra el intento como log de seguridad

