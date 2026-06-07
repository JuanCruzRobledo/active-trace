## 1. Scaffolding del Proyecto Frontend

- [x] 1.1 Inicializar proyecto Vite + React 18 + TypeScript en `frontend/`
- [x] 1.2 Configurar TypeScript (`tsconfig.json`, `tsconfig.node.json`)
- [x] 1.3 Instalar dependencias: React Router v6, TanStack Query, React Hook Form + Zod, Axios, Tailwind CSS, PostCSS
- [x] 1.4 Configurar Tailwind CSS (`tailwind.config.js`, `postcss.config.js`, `index.css` con directives)
- [x] 1.5 Configurar Vite proxy para `/api/*` → backend en desarrollo (`vite.config.ts`)
- [x] 1.6 Crear estructura de directorios feature-based: `frontend/src/features/{auth,shared}/`, `frontend/src/shared/`
- [x] 1.7 Crear `.env.example` con `VITE_API_URL`
- [x] 1.8 Verificar que `npm run dev` y `npm run build` funcionan

## 2. Shared: Cliente HTTP Centralizado

- [x] 2.1 Crear `shared/services/api.ts` con instancia Axios configurada (baseURL, timeout, headers)
- [x] 2.2 Implementar interceptor de request que agrega `Authorization: Bearer` desde el contexto de auth
- [x] 2.3 Implementar interceptor de response con refresh transparente (detecta 401, ejecuta refresh, cola de requests en vuelo)
- [x] 2.4 Implementar helper `createAuthApi()` que wrappea la API con el token actual
- [x] 2.5 Crear `shared/services/authService.ts` con funciones: `login`, `refresh`, `logout`, `getMe`, `verify2FA`, `enroll2FA`, `confirm2FA`, `forgotPassword`, `resetPassword`

## 3. Shared: Auth Context y Providers

- [x] 3.1 Crear `shared/hooks/useAuth.ts` con AuthContext (user, tokens, login, logout, isAuthenticated, isLoading, permissions)
- [x] 3.2 Implementar AuthProvider que restaura sesión desde refresh token en localStorage al cargar
- [x] 3.3 Implementar almacenamiento de access token en memoria y refresh token en localStorage
- [x] 3.4 Implementar función `login` que llama al backend y almacena la sesión
- [x] 3.5 Implementar función `logout` que revoca en backend y limpia sesión local
- [x] 3.6 Implementar función `getPermissions` que consulta `GET /api/auth/me` para permisos del usuario

## 4. Feature: Frontend Auth Login

- [x] 4.1 Crear `features/auth/pages/LoginPage.tsx` con formulario email + password
- [x] 4.2 Implementar validación Zod para email (formato) y password (no vacío)
- [x] 4.3 Implementar manejo de error 401: mostrar "Credenciales inválidas"
- [x] 4.4 Implementar manejo de error 429: mostrar "Demasiados intentos" con cuenta regresiva desde `Retry-After`
- [x] 4.5 Implementar detección de 2FA (`2fa_required: true` → guardar challenge_token y redirigir a `/2fa/verify`)
- [x] 4.6 Implementar redirect a ruta original después de login exitoso (`?redirect=`)
- [x] 4.7 Implementar estado de carga (botón deshabilitado + spinner)
- [x] 4.8 Agregar link "¿Olvidaste tu contraseña?" → `/forgot`

## 5. Feature: Frontend Auth 2FA

- [x] 5.1 Crear `features/auth/pages/Verify2FAPage.tsx` con formulario de código TOTP de 6 dígitos
- [x] 5.2 Implementar verificación 2FA con challenge_token + code contra `POST /api/auth/2fa/verify`
- [x] 5.3 Implementar manejo de errores: código incorrecto, challenge expirado, challenge ya usado
- [x] 5.4 Implementar redirect a login si no hay challenge_token en sesión
- [x] 5.5 Crear `features/auth/pages/Enroll2FAPage.tsx` con botón de enrolamiento
- [x] 5.6 Implementar visualización de QR PNG base64 y código secreto
- [x] 5.7 Implementar confirmación de enrolamiento con código de 6 dígitos
- [x] 5.8 Manejar error 409 "2FA already enrolled"

## 6. Feature: Frontend Auth Recovery

- [x] 6.1 Crear `features/auth/pages/ForgotPasswordPage.tsx` con formulario de email
- [x] 6.2 Implementar envío de solicitud a `POST /api/auth/forgot`
- [x] 6.3 Mostrar mensaje genérico de éxito (no revelar existencia del email)
- [x] 6.4 Manejar rate limit 429
- [x] 6.5 Crear `features/auth/pages/ResetPasswordPage.tsx` con campos de nueva contraseña + confirmación
- [x] 6.6 Extraer token de query string `?token=`
- [x] 6.7 Implementar validación en frontend: mínimo 12 caracteres, 1 mayúscula, 1 minúscula, 1 dígito, ambas coinciden
- [x] 6.8 Implementar envío a `POST /api/auth/reset`
- [x] 6.9 Manejar errores: token expirado, token ya usado, token inválido
- [x] 6.10 Mostrar "Contraseña actualizada correctamente" + link a login

## 7. Feature: Auth Guard y Routing

- [x] 7.1 Crear `features/auth/components/ProtectedRoute.tsx` que verifica sesión y redirige a `/login?redirect=`
- [x] 7.2 Crear `features/auth/components/RequirePermission.tsx` que verifica permiso `modulo:accion` y muestra 403 si no lo tiene
- [x] 7.3 Configurar React Router en `App.tsx` con rutas públicas (login, 2fa, recovery) y protegidas (layout)
- [x] 7.4 Implementar lazy loading de páginas con `React.lazy` + `Suspense`
- [x] 7.5 Implementar página 404 para rutas no encontradas
- [x] 7.6 Crear layout protegido principal con sidebar dinámico (`features/auth/components/AppLayout.tsx`)
- [x] 7.7 Implementar generación de menú lateral según permisos del usuario
- [x] 7.8 Agregar indicador de usuario logueado (nombre, email, rol) y botón de logout en la cabecera
- [x] 7.9 Implementar spinner de carga mientras se restaura sesión al recargar página

## 8. Shared: Componentes UI Base

- [x] 8.1 Crear `shared/components/LoadingSpinner.tsx` (spinner reutilizable con tamaño configurable)
- [x] 8.2 Crear `shared/components/ErrorMessage.tsx` (mensaje de error reutilizable con icono y acción opcional)
- [x] 8.3 Crear `shared/components/FormField.tsx` (wrapper de campo con label, error, hint)
- [x] 8.4 Crear `shared/components/Button.tsx` (botón reutilizable con variantes y estado de carga)
- [x] 8.5 Crear `shared/components/Input.tsx` (input reutilizable con estilos Tailwind consistentes)

## 9. Contenedor Docker

- [x] 9.1 Crear `frontend/Dockerfile` multi-stage (build con node:20-alpine, serve con nginx:alpine)
- [x] 9.2 Configurar nginx para SPA routing (fallback a `index.html`)
- [x] 9.3 Agregar servicio `frontend` a `docker-compose.yml` con build context, puerto y `VITE_API_URL`
- [x] 9.4 Verificar build de Docker y funcionamiento del contenedor

## 10. Integración y Verificación Final

- [x] 10.1 Verificar que el build de producción (`npm run build`) compila sin errores
- [x] 10.2 Verificar flujo completo de login (sin 2FA)
- [x] 10.3 Verificar flujo completo de login + 2FA verify
- [x] 10.4 Verificar flujo completo de enrolamiento 2FA
- [x] 10.5 Verificar flujo completo de recovery (forgot + reset)
- [x] 10.6 Verificar que refresh transparente funciona (esperar expiración de token)
- [x] 10.7 Verificar que ruta protegida redirige a login sin sesión
- [x] 10.8 Verificar que sidebar se adapta a permisos del usuario
- [x] 10.9 Verificar logout revoca sesión y redirige a login
- [x] 10.10 Verificar página 404 para rutas inexistentes
