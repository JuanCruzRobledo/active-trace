## Why

El backend de activia-trace cuenta con toda la API REST necesaria (auth JWT, RBAC, 2FA, recovery), pero no existe una interfaz de usuario que la consuma. Sin un frontend, el sistema no es operable para usuarios finales. Este change construye el **shell SPA** del frontend y el **flujo completo de autenticación**, habilitando el login, 2FA, recuperación de contraseña y el layout base con navegación adaptada a permisos.

## What Changes

- **Scaffolding completo** de React 18 + TypeScript + Vite + Tailwind + TanStack Query + React Hook Form + Zod + Axios
- **Cliente HTTP centralizado** con interceptor de tokens, refresh transparente y manejo de 401/403
- **Pantalla de login** con email + password, manejo de errores (credenciales inválidas, rate limit, usuario inactivo)
- **Pantalla de 2FA** (verificación TOTP post-login con challenge_token)
- **Pantalla de enrolamiento 2FA** (generación de secret + QR + confirmación con código)
- **Flujo de recuperación de contraseña** (solicitar reset + establecer nueva contraseña)
- **Guard de rutas** que verifica autenticación y permisos (redirección a login si no hay sesión)
- **Layout principal** con sidebar/menú dinámico según roles y permisos de la sesión
- **Logout** que revoca el refresh token y limpia el estado local
- **Ruta /me** para obtener perfil del usuario autenticado desde el backend

## Capabilities

### New Capabilities
- `frontend-shell`: Scaffolding del proyecto frontend (Vite + React + TS + Tailwind), estructura feature-based, cliente HTTP Axios centralizado con interceptor JWT y refresh transparente
- `frontend-auth-login`: Página de login con email/password, manejo de errores (401, 429, usuario inactivo), detección de 2FA requerido, almacenamiento de tokens
- `frontend-auth-2fa`: Página de verificación TOTP (código de 6 dígitos post-login) y enrolamiento 2FA con QR + confirmación
- `frontend-auth-recovery`: Flujo completo de recuperación de contraseña (solicitar email + reset con token)
- `frontend-auth-guard`: Route guard que verifica sesión activa, redirect a login, layout dinámico según permisos, logout

### Modified Capabilities
- (ninguna — es el primer change frontend)

## Impact

- **Nuevo directorio**: `frontend/` con estructura feature-based completa
- **Dependencias npm**: React 18, React Router v6, TanStack Query, React Hook Form + Zod, Axios, Tailwind CSS, Vite
- **API endpoints consumidos**: `POST /api/auth/login`, `POST /api/auth/2fa/verify`, `POST /api/auth/2fa/enroll`, `POST /api/auth/2fa/confirm`, `POST /api/auth/forgot`, `POST /api/auth/reset`, `POST /api/auth/refresh`, `POST /api/auth/logout`, `GET /api/auth/me`
- **Docker**: Se agrega servicio `frontend` al `docker-compose.yml` con Vite dev server + build multi-stage
- **Sin cambios en backend** — solo consumo de APIs existentes
