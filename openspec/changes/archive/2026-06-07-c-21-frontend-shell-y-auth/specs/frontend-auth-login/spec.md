## ADDED Requirements

### Requirement: Pantalla de login con email y contraseña

El sistema SHALL mostrar una pantalla de login (`/login`) con:
- Campo de email (input type="email", validación de formato)
- Campo de contraseña (input type="password")
- Botón "Iniciar sesión"
- Link "¿Olvidaste tu contraseña?" → `/forgot`
- Mensajes de error para:
  - `401`: "Credenciales inválidas" (genérico, sin revelar si el email existe)
  - `429`: "Demasiados intentos. Intenta de nuevo en X segundos" con el header `Retry-After`
  - Error de red: "Error de conexión. Verifica tu conexión a internet"
- Estado de carga mientras se procesa el login (botón deshabilitado + spinner)
- Redirect a la ruta que el usuario intentaba acceder (o a `/` si venía directo)
- En producción, el formulario NO debe autocompletar credenciales en campos de terceros (usar `autoComplete="off"`)

#### Scenario: Login exitoso sin 2FA

- **WHEN** el usuario ingresa email y contraseña válidos para una cuenta sin 2FA y hace clic en "Iniciar sesión"
- **THEN** el sistema llama a `POST /api/auth/login`, recibe `{ access_token, refresh_token }`, almacena la sesión y redirige a la ruta protegida correspondiente

#### Scenario: Login con 2FA redirige a verificación

- **WHEN** el usuario ingresa email y contraseña válidos para una cuenta con 2FA habilitado
- **THEN** el sistema recibe `{ 2fa_required: true, challenge_token }`, guarda el challenge token, y redirige a `/2fa/verify` para completar la autenticación

#### Scenario: Login con credenciales inválidas

- **WHEN** el usuario ingresa email o contraseña incorrectos
- **THEN** el sistema muestra el mensaje "Credenciales inválidas" sin distinguir si el email existe o no

#### Scenario: Rate limit alcanzado

- **WHEN** el usuario excede el límite de intentos de login (5 intentos en 60s)
- **THEN** el sistema recibe `429`, muestra "Demasiados intentos. Intenta de nuevo en X segundos" donde X es el valor del header `Retry-After`, y deshabilita el botón por esa duración

#### Scenario: Error de red en login

- **WHEN** el usuario intenta loguearse pero no hay conexión al servidor
- **THEN** el sistema muestra "Error de conexión. Verifica tu conexión a internet" sin cambiar de ruta

### Requirement: Almacenamiento de sesión

El sistema SHALL almacenar la sesión del usuario autenticado de la siguiente forma:
- Access token: en memoria (variable React state en `AuthContext`)
- Refresh token: en `localStorage` bajo la clave `trace_refresh_token`
- User info (id, email, nombre, roles, permisos, tenant_id): en `AuthContext` (estado global React)
- Al cerrar sesión o detectar refresh inválido: limpiar `localStorage` y resetear `AuthContext`

#### Scenario: Sesión persiste al refrescar página

- **WHEN** un usuario autenticado refresca la página
- **THEN** el sistema lee el refresh token de `localStorage`, ejecuta `POST /api/auth/refresh` para obtener un nuevo access token, obtiene `GET /api/auth/me` para cargar datos del usuario, y restaura la sesión sin redirigir a login

#### Scenario: Sesión NO persiste si refresh falla

- **WHEN** un usuario con refresh token expirado refresca la página
- **THEN** el sistema falla al refrescar, limpia `localStorage`, y redirige a `/login`

### Requirement: Logout revoca sesión

El sistema SHALL proveer un botón de "Cerrar sesión" que:
- Ejecuta `POST /api/auth/logout` con el refresh token en el body
- Limpia los tokens de memoria y localStorage
- Redirige a `/login`
- Si el logout HTTP falla (error de red), igual limpia la sesión local (el refresh token expirará por TTL)

#### Scenario: Logout exitoso

- **WHEN** el usuario hace clic en "Cerrar sesión"
- **THEN** el sistema ejecuta `POST /api/auth/logout` (204), limpia la sesión local y redirige a `/login`

#### Scenario: Logout con error de red

- **WHEN** el usuario hace clic en "Cerrar sesión" pero el servidor no responde
- **THEN** el sistema igual limpia la sesión local y redirige a `/login` (best-effort revocation)
