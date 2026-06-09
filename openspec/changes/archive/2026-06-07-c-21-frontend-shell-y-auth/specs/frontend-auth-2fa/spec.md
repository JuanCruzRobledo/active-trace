## ADDED Requirements

### Requirement: Pantalla de verificación 2FA TOTP

El sistema SHALL mostrar una pantalla de verificación 2FA (`/2fa/verify`) después de que el login haya devuelto `{ 2fa_required: true, challenge_token }`. La pantalla SHALL contener:
- Instrucción: "Ingresa el código de 6 dígitos de tu aplicación de autenticación"
- Campo de código (input de 6 dígitos numéricos, autoenfocado, formato `□□□□□□`)
- Botón "Verificar"
- Link "Volver al inicio de sesión" (limpia el challenge y redirige a `/login`)
- Mensajes de error:
  - `401` con "Invalid 2FA code": "Código incorrecto. Intenta de nuevo"
  - `401` con "2FA challenge expired": "El código expiró. Por favor, inicia sesión de nuevo" (redirige a `/login`)
  - `401` con "2FA challenge already used": "Este código ya fue usado. Inicia sesión nuevamente" (redirige a `/login`)
- Estado de carga mientras se verifica
- El challenge_token se almacena en memoria (no en localStorage) y se envía con la request de verificación

#### Scenario: Verificación 2FA exitosa

- **WHEN** el usuario ingresa el código TOTP correcto de 6 dígitos en `/2fa/verify`
- **THEN** el sistema llama a `POST /api/auth/2fa/verify` con `{ challenge_token, code }`, recibe `{ access_token, refresh_token }`, almacena la sesión y redirige a la ruta protegida

#### Scenario: Código TOTP incorrecto

- **WHEN** el usuario ingresa un código TOTP incorrecto
- **THEN** el sistema muestra "Código incorrecto. Intenta de nuevo" y permite reingresar el código

#### Scenario: Challenge expirado

- **WHEN** el usuario intenta verificar 2FA después de 5 minutos del login inicial
- **THEN** el sistema muestra "El código expiró. Por favor, inicia sesión de nuevo" y redirige a `/login`

#### Scenario: Acceso directo a /2fa/verify sin challenge

- **WHEN** un usuario navega directamente a `/2fa/verify` sin un challenge_token activo
- **THEN** el sistema redirige a `/login`

### Requirement: Pantalla de enrolamiento 2FA

El sistema SHALL proveer una pantalla de enrolamiento 2FA accesible desde el perfil del usuario o post-login si el admin lo requiere. La pantalla SHALL contener:
- Botón "Configurar 2FA" que inicia el enrolamiento (`POST /api/auth/2fa/enroll`)
- Visualización del código secreto (para configuración manual)
- Código QR (imagen PNG base64) para escanear con app de autenticación (Google Authenticator, Authy, etc.)
- Campo para confirmar con un código de 6 dígitos (`POST /api/auth/2fa/confirm`)
- Mensaje de éxito: "2FA activado correctamente"
- Manejo de error `409` si ya está enrolado: "2FA ya está configurado"
- Manejo de error `400` en confirmación: "Código inválido. Intentá de nuevo"

#### Scenario: Enrolamiento exitoso

- **WHEN** un usuario sin 2FA activo hace clic en "Configurar 2FA", escanea el QR con su app, e ingresa el código de 6 dígitos
- **THEN** el sistema muestra "2FA activado correctamente" y el usuario queda con 2FA habilitado para futuros logins

#### Scenario: Intento de enrolamiento cuando 2FA ya está activo

- **WHEN** un usuario con 2FA ya activo hace clic en "Configurar 2FA"
- **THEN** el sistema muestra "2FA ya está configurado" (manejo de `409`)

#### Scenario: Confirmación con código incorrecto

- **WHEN** el usuario ingresa un código que no coincide con el QR escaneado
- **THEN** el sistema muestra "Código inválido. Intentá de nuevo" y permite reintentar
